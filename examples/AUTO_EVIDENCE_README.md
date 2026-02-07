# 自动取证上链代理

这个代理实现了自动监听微信/钉钉消息，检测敏感关键词并自动上链取证的功能。

## 功能特性

- **消息监听**: 模拟监听微信和钉钉消息
- **关键词检测**: 自动检测"加班"、"工资"等敏感关键词
- **区块链上链**: 使用Turnkey工具将证据安全存储到区块链
- **证据签名**: 对证据数据进行数字签名确保真实性

## 使用方法

### 1. 环境配置

首先确保你有以下环境变量配置（在`.env`文件中）：

```bash
# Turnkey API配置
TURNKEY_API_PUBLIC_KEY=your_public_key
TURNKEY_API_PRIVATE_KEY=your_private_key

# 钱包配置
WALLET_ADDRESS=your_wallet_address
```

### 2. 运行代理

```python
from examples.auto_evidence_agent import AutoEvidenceAgent
import asyncio

async def main():
    # 创建代理实例
    agent = AutoEvidenceAgent()

    # 配置监听参数
    platforms = ["wechat", "dingtalk"]
    keywords = ["加班", "工资", "薪资", "加班费"]
    sign_with = "your_wallet_address"

    # 构建任务
    task = f"""
    请监听 {platforms} 平台，检测关键词 {keywords}，
    如果发现敏感消息，使用钱包 {sign_with} 将其作为证据上链存储。
    """

    # 运行代理
    result = await agent.run(task)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 自定义配置

你可以修改代理的配置：

```python
class MyEvidenceAgent(AutoEvidenceAgent):
    # 自定义关键词
    custom_keywords = ["辞职", "离职", "赔偿"]

    # 自定义监听时长
    monitoring_duration = 60  # 60秒

    # 自定义区块链网络
    blockchain_network = "polygon"  # 或 "ethereum", "bsc" 等
```

## 代理架构

### MessageMonitorTool
- 监听指定平台的聊天消息
- 支持关键词过滤
- 返回检测到的敏感消息列表

### EvidenceStorageTool
- 将消息证据数据签名
- 使用Turnkey安全上链
- 返回交易哈希和证据ID

### AutoEvidenceAgent
- 协调消息监听和证据上链
- 自动工作流执行
- 提供详细的执行报告

## 安全考虑

- 所有证据数据都会被数字签名
- 使用Turnkey的安全签名服务
- 证据不可篡改地存储在区块链上
- 支持多链部署（Ethereum, Polygon, BSC等）

## 扩展开发

### 添加新的消息源
```python
class SlackMonitorTool(BaseTool):
    # 实现Slack消息监听
    pass
```

### 添加新的上链方式
```python
class IPFSStorageTool(BaseTool):
    # 使用IPFS存储证据
    pass
```

### 自定义关键词检测
```python
class AdvancedKeywordTool(BaseTool):
    # 使用NLP进行智能关键词检测
    pass
```

## 注意事项

1. **合规性**: 确保消息监听符合当地法律法规
2. **隐私保护**: 只监听和存储必要的证据数据
3. **API限制**: 注意各平台的API调用频率限制
4. **成本控制**: 区块链上链操作会产生gas费用

## 故障排除

- **Turnkey连接失败**: 检查API密钥配置
- **消息监听失败**: 确认平台权限和网络连接
- **上链失败**: 检查钱包余额和网络状态