"""
SpoonOS 法律公正助手 - 主程序
支持法律检索、回答与区块链存证。
"""
import asyncio
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from dotenv import load_dotenv

# 1. 最先加载 .env，确保后续代码能读取环境变量
load_dotenv()
app = Flask(__name__)
CORS(app) # 解决跨域问题

# 2. 显式获取配置（必须在创建 LLM 之前）
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
model_name = os.getenv("MODEL_NAME", "deepseek-chat")

if not api_key:
    raise ValueError(
        "请在 .env 中配置 OPENAI_API_KEY。当前未读取到有效的 API Key。"
    )

# 3. 显式初始化 DeepSeek LLM，使用 OpenAILike 避免模型名校验
from llama_index.llms.openai_like import OpenAILike

llm = OpenAILike(
    api_key=api_key,
    api_base=api_base,
    model=model_name,
    is_chat_model=True,
)

# 4. 配置全局 Settings
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

Settings.llm = llm
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")

# 5. 引入技能（需在 Settings 配置之后）
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.workflow import Context

from skills.legal_skill import search_laws
from skills.notary_skill import notarize_on_chain

# 6. 系统提示词：SpoonOS 法律公正助手
SYSTEM_PROMPT = """你是 SpoonOS 法律公正助手。

工作流程要求：
1. 先使用 search_laws 工具检索相关法律条文，再基于检索结果回答用户问题。
2. 回答用户的法律相关问题。
3. 如果用户明确要求对某段内容进行存证，则调用 notarize_on_chain 工具完成区块链存证。
"""

# 7. 构建 ReActAgent，显式传入 llm
agent = ReActAgent(
    tools=[search_laws, notarize_on_chain],
    llm=llm,
    system_prompt=SYSTEM_PROMPT,
    verbose=True,
)

# 8. 创建上下文与记忆
ctx = Context(agent)
memory = ChatMemoryBuffer.from_defaults(llm=llm)


# --- 3. API 路由 ---
# --- 修改后的 API 路由 ---
@app.route('/api/chat', methods=['POST'])
async def chat():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({"error": "No message"}), 400

    try:
        # 使用 agent.run 获取执行句柄
        handler = agent.run(user_input, memory=memory, ctx=ctx)
        
        # 这种方式会自动处理 ReAct 的思考过程，最终结果会直接包含在响应对象中
        response = await handler 
        
        # response 对象通常包含最终的 content，过滤掉中间的推理步骤
        return jsonify({"response": str(response)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# 原有的上传逻辑可保留在这里...
@app.route('/api/upload-evidence', methods=['POST'])
def upload_evidence():
    # ... 你之前的 Flask 存证逻辑 ...
    return jsonify({"success": True, "tx_hash": "0x...", "evidence_hash": "..."})

if __name__ == "__main__":
    app.run(port=5000, debug=True)