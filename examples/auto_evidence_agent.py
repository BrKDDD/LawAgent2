"""
自动取证上链代理 - 监听微信/钉钉消息，检测敏感关键词并自动上链取证

功能：
1. 监听微信/钉钉消息
2. 检测"加班"、"工资"等关键词
3. 自动将消息内容上链存储为证据
"""

import asyncio
import json
import os
import time
import hmac
import hashlib
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import aiohttp
from urllib.parse import quote

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools.base import BaseTool
from spoon_ai.tools import ToolManager
from spoon_ai.tools.turnkey_tools import SignMessageTool, BroadcastTransactionTool
from spoon_ai.chat import ChatBot
from pydantic import Field

logger = logging.getLogger(__name__)

class WeChatWorkMonitorTool(BaseTool):
    """企业微信消息监听工具 - 使用企业微信官方API"""

    name: str = "monitor_wechat_work"
    description: str = "监听企业微信消息，检测敏感关键词"
    parameters: dict = {
        "type": "object",
        "properties": {
            "corp_id": {
                "type": "string",
                "description": "企业微信CorpID"
            },
            "corp_secret": {
                "type": "string",
                "description": "企业微信应用Secret"
            },
            "agent_id": {
                "type": "string",
                "description": "企业微信应用AgentID"
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要检测的关键词，如 ['加班', '工资', '薪资']"
            },
            "duration": {
                "type": "integer",
                "description": "监听时长（秒），默认300秒",
                "default": 300
            }
        },
        "required": ["corp_id", "corp_secret", "agent_id", "keywords"]
    }

    async def execute(self, corp_id: str, corp_secret: str, agent_id: str, keywords: List[str], duration: int = 300) -> str:
        """监听企业微信消息"""
        try:
            # 获取access_token
            token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
            async with aiohttp.ClientSession() as session:
                async with session.get(token_url) as resp:
                    token_data = await resp.json()
                    if token_data.get("errcode") != 0:
                        return f"获取企业微信token失败: {token_data.get('errmsg')}"

                    access_token = token_data["access_token"]

            # 注意：企业微信消息监听需要配置回调URL，这里只是获取消息的示例
            # 实际实现需要服务器接收微信推送的消息

            # 模拟获取最近消息（实际应该从回调接收）
            messages_url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/get_chatdata?access_token={access_token}"

            # 这里返回配置说明，因为实际的消息监听需要服务器端点
            return json.dumps({
                "status": "config_required",
                "message": "企业微信消息监听需要配置回调URL",
                "setup_steps": [
                    "1. 在企业微信管理后台配置应用回调URL",
                    "2. 实现消息接收端点处理微信推送",
                    "3. 设置消息加密解密",
                    f"4. 监听关键词: {keywords}"
                ],
                "corp_id": corp_id,
                "agent_id": agent_id
            }, ensure_ascii=False)

        except Exception as e:
            return f"企业微信监听失败: {str(e)}"

class DingTalkMonitorTool(BaseTool):
    """钉钉消息监听工具 - 使用钉钉机器人API"""

    name: str = "monitor_dingtalk"
    description: str = "监听钉钉群消息，检测敏感关键词"
    parameters: dict = {
        "type": "object",
        "properties": {
            "webhook_url": {
                "type": "string",
                "description": "钉钉机器人Webhook URL"
            },
            "secret": {
                "type": "string",
                "description": "钉钉机器人Secret（可选，用于签名验证）"
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要检测的关键词，如 ['加班', '工资', '薪资']"
            },
            "duration": {
                "type": "integer",
                "description": "监听时长（秒），默认300秒",
                "default": 300
            }
        },
        "required": ["webhook_url", "keywords"]
    }

    def _sign_request(self, secret: str, timestamp: str) -> str:
        """生成钉钉签名"""
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    async def execute(self, webhook_url: str, secret: Optional[str], keywords: List[str], duration: int = 300) -> str:
        """监听钉钉消息 - 通过机器人Webhook"""
        try:
            # 钉钉机器人主要用于发送消息，不是接收消息
            # 这里演示如何设置机器人来监听（实际需要配合群设置）

            # 测试webhook连接
            timestamp = str(int(time.time() * 1000))
            sign = self._sign_request(secret, timestamp) if secret else None

            test_url = webhook_url
            if sign:
                test_url += f"&timestamp={timestamp}&sign={quote(sign)}"

            test_message = {
                "msgtype": "text",
                "text": {
                    "content": f"🤖 消息监听已启动\n检测关键词: {', '.join(keywords)}\n监听时长: {duration}秒"
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(test_url, json=test_message) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("errcode") == 0:
                            return json.dumps({
                                "status": "webhook_tested",
                                "message": "钉钉机器人连接成功",
                                "keywords": keywords,
                                "duration": duration,
                                "note": "钉钉机器人主要用于发送消息，要接收群消息需要配置自定义机器人并设置相应权限"
                            }, ensure_ascii=False)
                        else:
                            return f"钉钉机器人测试失败: {result.get('errmsg')}"
                    else:
                        return f"钉钉Webhook请求失败: HTTP {resp.status}"

        except Exception as e:
            return f"钉钉监听失败: {str(e)}"

class WeChatWebMonitorTool(BaseTool):
    """微信网页版消息监听工具"""

    name: str = "monitor_wechat_web"
    description: str = "监听微信网页版消息，检测敏感关键词"
    parameters: dict = {
        "type": "object",
        "properties": {
            "platforms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要监听的平台，固定为 ['wechat_web']"
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要检测的关键词，如 ['加班', '工资', '薪资']"
            },
            "duration": {
                "type": "integer",
                "description": "监听时长（秒），默认300秒",
                "default": 300
            }
        },
        "required": ["keywords"]
    }

    async def execute(self, platforms: List[str], keywords: List[str], duration: int = 300) -> str:
        """微信网页版消息监听 - 需要手动扫码登录"""
        try:
            # 微信网页版API比较复杂，需要处理登录、保持会话等
            # 这里提供实现指导

            return json.dumps({
                "status": "manual_setup_required",
                "message": "微信网页版监听需要手动扫码登录",
                "implementation_guide": [
                    "1. 使用itchat库实现微信网页版自动化",
                    "2. 安装: pip install itchat",
                    "3. 实现消息监听函数",
                    "4. 处理登录和消息转发",
                    "5. 注意微信风控和账号安全"
                ],
                "sample_code": """
import itchat

@itchat.msg_register(itchat.content.TEXT)
def text_reply(msg):
    # 处理文本消息
    if any(kw in msg['Text'] for kw in keywords):
        # 检测到敏感关键词，触发取证流程
        handle_sensitive_message(msg)

itchat.auto_login(hotReload=True)
itchat.run()
                """,
                "keywords": keywords,
                "duration": duration,
                "security_note": "微信网页版监听可能违反微信使用协议，请确保合规使用"
            }, ensure_ascii=False)

        except Exception as e:
            return f"微信网页版监听失败: {str(e)}"

    async def execute(self, platforms: List[str], keywords: List[str], duration: int = 30) -> str:
        """模拟监听消息"""
        logger.info(f"开始监听平台: {platforms}, 关键词: {keywords}, 时长: {duration}秒")

        # 模拟消息数据（实际实现中需要接入微信/钉钉API）
        mock_messages = [
            {
                "platform": "wechat",
                "sender": "老板",
                "content": "小王，今天需要加班到晚上8点",
                "timestamp": datetime.now().isoformat(),
                "group": "工作群"
            },
            {
                "platform": "dingtalk",
                "sender": "HR",
                "content": "本月工资已发放，请查收",
                "timestamp": datetime.now().isoformat(),
                "group": "公司通知"
            },
            {
                "platform": "wechat",
                "sender": "同事",
                "content": "今天天气真好",
                "timestamp": datetime.now().isoformat(),
                "group": "闲聊群"
            }
        ]

        detected_messages = []

        # 检测关键词
        for msg in mock_messages:
            content_lower = msg["content"].lower()
            matched_keywords = [kw for kw in keywords if kw.lower() in content_lower]

            if matched_keywords:
                msg["matched_keywords"] = matched_keywords
                detected_messages.append(msg)
                logger.info(f"检测到敏感消息: {msg}")

        # 模拟监听延时
        await asyncio.sleep(min(duration, 5))  # 实际实现中会持续监听

        if detected_messages:
            return json.dumps({
                "status": "success",
                "detected_count": len(detected_messages),
                "messages": detected_messages
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "status": "no_matches",
                "message": f"监听期间未检测到关键词: {keywords}"
            }, ensure_ascii=False)

class EvidenceStorageTool(BaseTool):
    """证据上链存储工具"""

    name: str = "store_evidence_onchain"
    description: str = "将消息证据存储到区块链上"
    parameters: dict = {
        "type": "object",
        "properties": {
            "evidence_data": {
                "type": "object",
                "description": "要上链的证据数据"
            },
            "sign_with": {
                "type": "string",
                "description": "用于签名的钱包地址或私钥ID"
            }
        },
        "required": ["evidence_data", "sign_with"]
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 延迟初始化工具，避免在类定义时初始化
        self._sign_tool = None
        self._broadcast_tool = None

    @property
    def sign_tool(self):
        if self._sign_tool is None:
            self._sign_tool = SignMessageTool()
        return self._sign_tool

    @property
    def broadcast_tool(self):
        if self._broadcast_tool is None:
            self._broadcast_tool = BroadcastTransactionTool()
        return self._broadcast_tool

    async def execute(self, evidence_data: Dict[str, Any], sign_with: str) -> str:
        """
        将证据“真正上链”的最简方案：发送一笔 0 金额自转账交易，把 evidence_hash 写入 tx.data。

        优点：不需要部署合约；只要 RPC 可用、钱包有 gas，即可稳定落链。
        """

        # 尽量加载 .env（不强依赖）
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(override=False)
        except Exception:
            pass

        # 1) 创建证据哈希（使用 SHA-256，确保跨平台一致性）
        evidence_json = json.dumps(evidence_data, sort_keys=True, ensure_ascii=False)
        evidence_hash = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()

        # 2) 组装上链 payload：前缀 + 32 字节 hash
        prefix = b"SPOON_EVIDENCE_V1|"
        payload = prefix + bytes.fromhex(evidence_hash)
        data_hex = "0x" + payload.hex()

        # 3) 获取 RPC（兼容项目里常见的变量名）
        rpc_url = (
            os.getenv("WEB3_RPC_URL")
            or os.getenv("RPC_URL")
            or os.getenv("NEOX_RPC_URL")
        )
        if not rpc_url:
            return json.dumps(
                {
                    "status": "error",
                    "error": "missing_rpc_url",
                    "message": "缺少 RPC 配置：请设置 WEB3_RPC_URL（或兼容使用 RPC_URL / NEOX_RPC_URL）",
                },
                ensure_ascii=True,
                indent=2,
            )

        # 4) 获取签名私钥（支持明文 PRIVATE_KEY，或 ENC:v2 走 SecretVault 解密）
        private_key = os.getenv("PRIVATE_KEY")
        try:
            from spoon_ai.security import decrypted_secrets  # 延迟导入，避免示例环境缺依赖

            with decrypted_secrets(["PRIVATE_KEY"], prompt=True) as vault:
                if vault.exists("PRIVATE_KEY"):
                    with vault.get_decoded("PRIVATE_KEY") as pk:
                        if pk:
                            private_key = pk
        except Exception:
            # 解密体系不可用时，继续使用环境变量里的明文 PRIVATE_KEY
            pass

        if not private_key:
            return json.dumps(
                {
                    "status": "error",
                    "error": "missing_private_key",
                    "message": "缺少 PRIVATE_KEY：无法对交易签名并广播上链",
                },
                ensure_ascii=True,
                indent=2,
            )

        # 5) 连接链并广播交易（legacy tx：最少坑，EIP-1559 链也能接受）
        try:
            from web3 import Web3
            from web3.middleware import ExtraDataToPOAMiddleware
            from eth_account import Account
            from eth_account.messages import encode_defunct

            w3 = Web3(Web3.HTTPProvider(rpc_url))
            try:
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except Exception:
                # 不是 PoA 链也没关系
                pass

            if not w3.is_connected():
                return json.dumps(
                    {
                        "status": "error",
                        "error": "rpc_unreachable",
                        "message": f"无法连接 RPC：{rpc_url}",
                        "rpc_url": rpc_url,
                    },
                    ensure_ascii=True,
                    indent=2,
                )

            account = Account.from_key(private_key)
            from_addr = account.address

            nonce = w3.eth.get_transaction_count(from_addr)
            chain_id = int(w3.eth.chain_id)
            gas_price = w3.eth.gas_price

            # 估算 gas（失败则给一个保守兜底）
            try:
                gas = w3.eth.estimate_gas(
                    {"from": from_addr, "to": from_addr, "value": 0, "data": data_hex}
                )
                gas = int(gas * 2)  # 留余量，降低失败概率
            except Exception:
                gas = 80000

            tx = {
                "chainId": chain_id,
                "nonce": nonce,
                "to": from_addr,      # 自转账
                "value": 0,
                "data": data_hex,     # 把证据 hash 写进 calldata
                "gas": gas,
                "gasPrice": gas_price,
            }

            signed_tx = account.sign_transaction(tx)
            tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash = tx_hash_bytes.hex()

            # 可选：等待回执（短超时；超时也不影响“已广播”事实）
            receipt_status = None
            try:
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=30)
                receipt_status = int(getattr(receipt, "status", receipt.get("status", 0)))  # type: ignore[attr-defined]
            except Exception:
                receipt_status = None

            # 同一把私钥对“证据哈希声明”做一次签名，便于做主体证明（非必须）
            msg = f"Evidence Hash: {evidence_hash}\nTimestamp: {datetime.now().isoformat()}"
            sig = account.sign_message(encode_defunct(text=msg)).signature.hex()

            # Explorer 链接（优先用 SCAN_URL）
            scan_url = os.getenv("SCAN_URL")
            explorer = None
            if scan_url:
                explorer = scan_url.rstrip("/") + "/tx/" + tx_hash

            result = {
                "status": "success",
                "mode": "calldata_anchor_tx",
                "chain_id": chain_id,
                "rpc_url": rpc_url,
                "from": from_addr,
                "tx_hash": tx_hash,
                "receipt_status": receipt_status,  # None 表示未等待到/超时
                "evidence_hash": evidence_hash,
                "data_hex": data_hex,
                "signature": sig,
                "timestamp": datetime.now().isoformat(),
                "evidence_data": evidence_data,
                "explorer": explorer,
            }

            logger.info(f"证据已上链(真实交易): {tx_hash}")
            # 为了在 Windows 默认控制台编码下更稳（避免 emoji / 非 GBK 字符导致打印异常）
            # 这里使用 ensure_ascii=True，把非 ASCII 字符转义成 \\uXXXX。
            return json.dumps(result, ensure_ascii=True, indent=2)

        except ImportError as e:
            return json.dumps(
                {
                    "status": "error",
                    "error": "missing_dependencies",
                    "message": f"缺少依赖，无法上链：{e}",
                    "hint": "请安装: pip install web3 eth-account",
                },
                ensure_ascii=True,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {
                    "status": "error",
                    "error": "onchain_failed",
                    "message": f"上链失败: {str(e)}",
                },
                ensure_ascii=True,
                indent=2,
            )

class RealMessageMonitorAgent(ToolCallAgent):
    """真实消息监听取证代理"""

    name: str = "real_message_monitor_agent"
    description: str = "真实监听微信/钉钉消息，检测敏感关键词并上链取证"

    system_prompt: str = """
    你是一个真实的消息监听取证代理，负责：
    1. 使用各种方法监听微信/钉钉消息
    2. 检测"加班"、"工资"等敏感关键词
    3. 自动将相关消息作为证据上链存储

    工作流程：
    1. 根据用户指定的平台选择合适的监听工具
    2. 配置监听参数和关键词
    3. 如果检测到敏感关键词，使用store_evidence_onchain工具上链
    4. 返回处理结果和上链交易信息

    注意：确保所有操作符合法律法规和平台使用协议。
    """

    next_step_prompt: str = "根据用户需求选择合适的监听方案并执行"

    def __init__(self, **kwargs):
        # 设置默认的llm如果没有提供
        if 'llm' not in kwargs:
            kwargs['llm'] = ChatBot()

        # 初始化所有可用的监听工具
        tools = [
            WeChatWorkMonitorTool(),
            DingTalkMonitorTool(),
            WeChatWebMonitorTool(),
            EvidenceStorageTool()
        ]
        kwargs['available_tools'] = ToolManager(tools)
        super().__init__(**kwargs)

async def main():
    """演示真实消息监听取证功能"""

    print("🚀 真实消息监听取证代理演示")
    print("=" * 60)

    # 配置参数
    keywords = ["加班", "工资", "薪资", "加班费", "奖金", "辞职", "离职"]
    sign_with = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"  # 示例钱包地址

    print(f"🔍 检测关键词: {keywords}")
    print(f"🔐 签名钱包: {sign_with}")
    print()

    # 演示1: 企业微信监听设置
    print("1️⃣ 企业微信监听设置演示...")
    wechat_tool = WeChatWorkMonitorTool()
    # 注意：这里需要真实的corp_id, corp_secret, agent_id
    wechat_result = await wechat_tool.execute(
        corp_id="your_corp_id",
        corp_secret="your_corp_secret",
        agent_id="your_agent_id",
        keywords=keywords,
        duration=300
    )
    print("企业微信配置结果:")
    print(wechat_result)
    print()

    # 演示2: 钉钉机器人监听设置
    print("2️⃣ 钉钉机器人监听设置演示...")
    dingtalk_tool = DingTalkMonitorTool()
    # 注意：这里需要真实的webhook_url和secret
    dingtalk_result = await dingtalk_tool.execute(
        webhook_url="https://oapi.dingtalk.com/robot/send?access_token=your_access_token",
        secret="your_secret",  # 可选
        keywords=keywords,
        duration=300
    )
    print("钉钉机器人配置结果:")
    print(dingtalk_result)
    print()

    # 演示3: 微信网页版监听说明
    print("3️⃣ 微信网页版监听说明...")
    wechat_web_tool = WeChatWebMonitorTool()
    wechat_web_result = await wechat_web_tool.execute(platforms=["wechat_web"], keywords=keywords, duration=300)
    print("微信网页版实现指导:")
    print(wechat_web_result)
    print()

    # 演示4: 证据上链功能
    print("4️⃣ 证据上链功能演示...")
    sample_evidence = {
        "platform": "wechat",
        "message": {
            "sender": "老板",
            "content": "小王，这个月加班费已经发放到工资里了",
            "timestamp": datetime.now().isoformat(),
            "group": "工作群"
        },
        "detection_info": {
            "keywords": keywords,
            "matched_keywords": ["加班费", "工资"],
            "detection_time": datetime.now().isoformat()
        }
    }

    storage_tool = EvidenceStorageTool()
    storage_result = await storage_tool.execute(sample_evidence, sign_with)
    print("证据上链结果:")
    print(storage_result)
    print()

    print("✅ 演示完成")
    print()
    print("📝 实现要点:")
    print("1. 企业微信: 需要企业账号和开发者权限，配置回调URL")
    print("2. 钉钉: 使用机器人Webhook，需要群主添加机器人")
    print("3. 微信网页版: 需要itchat库，处理登录和消息监听")
    print("4. 区块链: 配置Turnkey API密钥和钱包")
    print("5. 安全: 确保所有操作符合法律法规")

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 运行演示
    asyncio.run(main())