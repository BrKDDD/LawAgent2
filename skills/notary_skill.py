"""
区块链存证技能：计算文本哈希，真实上链存证到 Sepolia 测试网。
"""
import hashlib
import os

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from llama_index.core.tools import FunctionTool

# 加载环境变量
load_dotenv()


def notarize_document(text: str) -> str:
    """
    对文本进行存证：计算 SHA256 哈希，发送真实交易上链。
    
    逻辑：向自己转账 0 ETH，将文件 Hash 写入 data (Input Data) 字段。
    """
    # 0. 强制重新加载环境变量（确保读取最新的 .env）
    load_dotenv(verbose=True, override=True)
    
    # 1. 计算文本的 SHA256 哈希
    doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    # 2. 组装上链 payload：前缀 + 32 字节 hash
    prefix = b"NOTARY_V1|"
    payload = prefix + bytes.fromhex(doc_hash)
    data_hex = "0x" + payload.hex()
    
    # 3. 获取配置
    rpc_url = os.getenv("WEB3_RPC_URL")
    private_key = os.getenv("WALLET_PRIVATE_KEY")
    
    # 调试打印：显示读取到的值（私钥只显示前10位）
    print(f"[DEBUG] WEB3_RPC_URL = {rpc_url}")
    print(f"[DEBUG] WALLET_PRIVATE_KEY = {private_key[:10] if private_key else None}...")
    
    if not rpc_url:
        raise ValueError("未找到 RPC 地址，请检查 .env 文件中的 WEB3_RPC_URL")
    if not private_key:
        raise ValueError("未找到私钥，请检查 .env 文件中的 WALLET_PRIVATE_KEY")
    
    # 4. 连接区块链
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        return f"错误: 无法连接到 RPC: {rpc_url}"
    
    # 5. 加载账户
    account = Account.from_key(private_key)
    from_addr = account.address
    
    # 6. 构造交易（向自己转账 0 ETH，hash 写入 data）
    nonce = w3.eth.get_transaction_count(from_addr)
    gas_price = w3.eth.gas_price
    
    # 估算 gas
    try:
        gas = w3.eth.estimate_gas({
            "from": from_addr,
            "to": from_addr,
            "value": 0,
            "data": data_hex
        })
        gas = int(gas * 1.5)  # 留余量
    except Exception:
        gas = 50000  # 兜底值
    
    tx = {
        "chainId": w3.eth.chain_id,
        "nonce": nonce,
        "to": from_addr,      # 自转账
        "value": 0,
        "data": data_hex,     # 证据 hash 写入 calldata
        "gas": gas,
        "gasPrice": gas_price,
    }
    
    # 7. 签名并发送交易
    try:
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = tx_hash.hex()
        
        return f"上链成功! 交易哈希: https://sepolia.etherscan.io/tx/0x{tx_hash_hex}"
    
    except Exception as e:
        return f"上链失败: {str(e)}"


# 封装为 FunctionTool，命名为 notarize_on_chain
notarize_on_chain = FunctionTool.from_defaults(
    fn=notarize_document,
    name="notarize_on_chain",
    description="对传入的文本内容计算 SHA256 哈希并上链存证到 Sepolia 测试网，返回交易哈希链接。",
)
