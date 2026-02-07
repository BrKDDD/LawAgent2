"""
SpoonOS 法律公正助手 + 区块链证据存证 后端
"""
import os
import json
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ================== 1. 环境变量 & Flask ==================
load_dotenv()

app = Flask(__name__)
CORS(app)

# ================== 2. 区块链证据上传工具（spoon_ai） ==================
upload_tool = None

def init_upload_agent():
    global upload_tool
    try:
        from examples.user_evidence_upload_agent import UserEvidenceUploadTool
        upload_tool = UserEvidenceUploadTool()
        print("✅ 证据上传工具初始化成功")
        return True
    except Exception as e:
        print(f"❌ 证据上传工具初始化失败: {e}")
        return False


@app.route('/api/upload-evidence', methods=['POST'])
def upload_evidence():
    """上传证据并上链"""
    try:
        if upload_tool is None:
            return jsonify({'error': '证据上传工具未初始化'}), 500

        # 获取上传的文件
        if 'evidence_file' not in request.files:
            return jsonify({'error': '没有提供文件'}), 400

        file = request.files['evidence_file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 获取表单数据
        evidence_type = request.form.get('evidence_type', 'document')
        # 前端历史值兼容：text -> document
        if evidence_type == 'text':
            evidence_type = 'document'
        evidence_source = request.form.get('evidence_source', 'user_upload')
        user_address = request.form.get('user_address', '')
        description = request.form.get('description', '')

        # 读取文件内容
        file_content = file.read()
        if isinstance(file_content, bytes):
            try:
                file_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # 如果不是文本文件，转换为 base64
                import base64
                file_content = base64.b64encode(file_content).decode('utf-8')
                evidence_type = 'binary'

        # 运行工具（异步）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # sign_with 参数目前仅用于接口兼容；真实上链使用 .env 的 PRIVATE_KEY
            sign_with = user_address or "local"
            result = loop.run_until_complete(
                upload_tool.execute(
                    evidence_content=file_content,
                    evidence_type=evidence_type,
                    source=evidence_source,
                    sign_with=sign_with,
                    description=description,
                    uploader_address=user_address,
                    file_name=file.filename,
                    metadata={
                        "content_encoding": "utf-8" if evidence_type != "binary" else "base64",
                    },
                )
            )
        finally:
            loop.close()

        # 解析结果
        if isinstance(result, str):
            # 尝试解析 JSON 结果
            try:
                parsed_result = json.loads(result)
                # 兼容前端：统一输出 success/tx_hash/evidence_hash 等字段
                status = parsed_result.get("status")
                success = status == "success"

                onchain = parsed_result.get("onchain")
                onchain_dict = onchain if isinstance(onchain, dict) else {}

                response_body = {
                    "success": bool(success),
                    "status": status,
                    "message": parsed_result.get("message") or ("OK" if success else "FAILED"),
                    "error": parsed_result.get("error"),
                    # 扁平化常用字段，便于前端展示
                    "tx_hash": onchain_dict.get("tx_hash"),
                    "evidence_hash": onchain_dict.get("evidence_hash"),
                    "signature": onchain_dict.get("signature"),
                    "timestamp": onchain_dict.get("timestamp"),
                    "explorer_url": onchain_dict.get("explorer"),
                    # 保留完整细节
                    "result": parsed_result,
                    "onchain": onchain,
                }
                return jsonify(response_body)
            except json.JSONDecodeError:
                return jsonify({
                    'success': False,
                    'error': 'invalid_json',
                    'message': result,
                    'raw_response': result,
                })
        else:
            return jsonify({
                'success': False,
                'error': 'invalid_result_type',
                'result': str(result)
            })

    except Exception as e:
        print(f"上传失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "upload_tool_ready": upload_tool is not None
    })


# ================== 3. LLM / Agent（法律助手） ==================
from llama_index.llms.openai_like import OpenAILike
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Context

from skills.legal_skill import search_laws
from skills.notary_skill import notarize_on_chain

api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
model_name = os.getenv("MODEL_NAME", "deepseek-chat")

llm = OpenAILike(
    api_key=api_key,
    api_base=api_base,
    model=model_name,
    is_chat_model=True,
)

Settings.llm = llm
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")

SYSTEM_PROMPT = """
你是 SpoonOS 法律公正助手。

流程：
1. 使用 search_laws 检索法律条文
2. 基于结果回答
3. 若用户要求存证，调用 notarize_on_chain
"""

agent = ReActAgent(
    tools=[search_laws, notarize_on_chain],
    llm=llm,
    system_prompt=SYSTEM_PROMPT,
    verbose=True,
)

ctx = Context(agent)
memory = ChatMemoryBuffer.from_defaults(llm=llm)


@app.route('/api/chat', methods=['POST'])
async def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"error": "message 不能为空"}), 400

    try:
        handler = agent.run(user_input, memory=memory, ctx=ctx)
        response = await handler
        return jsonify({"response": str(response)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================== 4. 启动入口 ==================
if __name__ == "__main__":
    init_upload_agent()
    print("🚀 SpoonOS 法律公正助手后端启动中...")
    app.run(host="0.0.0.0", port=5000, debug=True)
