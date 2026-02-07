# 自动取证上链代理 - 真实消息监听实现

这个代理实现了自动检测微信/钉钉消息，出现"加班""工资"等关键字时自动取证上链的功能。

## 🎯 功能特性

- **企业微信集成**: 使用官方API监听企业微信消息
- **钉钉机器人集成**: 通过Webhook接收钉钉群消息
- **微信网页版支持**: 提供itchat库集成方案
- **智能关键词检测**: 自动识别敏感关键词
- **区块链取证**: 使用Turnkey将证据安全上链
- **多平台支持**: 支持微信、钉钉等多平台监听

## 🔧 技术实现方案

### 1. 企业微信监听

#### 配置步骤
1. 注册企业微信开发者账号
2. 创建应用并获取CorpID、Secret、AgentID
3. 配置消息接收回调URL
4. 实现消息解密和处理逻辑

#### 代码实现
```python
# 企业微信配置
corp_id = "your_corp_id"
corp_secret = "your_corp_secret"
agent_id = "your_agent_id"

# 获取Access Token
token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"
# 处理消息回调...
```

### 2. 钉钉机器人监听

#### 配置步骤
1. 在钉钉群中添加自定义机器人
2. 获取Webhook URL和Secret
3. 配置消息接收和签名验证
4. 实现关键词过滤逻辑

#### 代码实现
```python
# 钉钉机器人配置
webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
secret = "your_robot_secret"

# 签名验证
timestamp = str(int(time.time() * 1000))
string_to_sign = f"{timestamp}\n{secret}"
signature = base64.b64encode(hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest())
```

### 3. 微信网页版监听

#### 技术方案
使用itchat库实现微信网页版自动化：

```bash
pip install itchat
```

#### 代码实现
```python
import itchat

@itchat.msg_register(itchat.content.TEXT)
def text_reply(msg):
    """处理文本消息"""
    if any(kw in msg['Text'] for kw in keywords):
        # 检测到敏感关键词
        handle_sensitive_message(msg)

# 登录并运行
itchat.auto_login(hotReload=True)
itchat.run()
```

## 🚀 快速开始

### 环境准备

1. **安装依赖**
```bash
pip install spoon-ai-sdk itchat aiohttp
```

2. **配置环境变量**
```bash
# .env文件
# 企业微信
WECHAT_CORP_ID=your_corp_id
WECHAT_CORP_SECRET=your_corp_secret
WECHAT_AGENT_ID=your_agent_id

# 钉钉机器人
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=your_secret

# Turnkey区块链
TURNKEY_API_PUBLIC_KEY=your_public_key
TURNKEY_API_PRIVATE_KEY=your_private_key
WALLET_ADDRESS=your_wallet_address
```

### 使用示例

```python
from examples.auto_evidence_agent import RealMessageMonitorAgent
import asyncio

async def main():
    # 创建代理
    agent = RealMessageMonitorAgent()

    # 配置监听任务
    task = """
    请监听企业微信和钉钉消息，检测以下关键词：
    - 加班、工资、薪资、加班费、奖金
    - 辞职、离职、赔偿

    当检测到敏感消息时，自动将消息内容作为证据上链存储。
    """

    # 执行任务
    result = await agent.run(task)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 API配置详情

### 企业微信API

| 参数 | 说明 | 获取方式 |
|------|------|----------|
| CorpID | 企业ID | 企业微信管理后台 |
| CorpSecret | 应用密钥 | 应用管理页面 |
| AgentID | 应用ID | 应用管理页面 |

**回调URL配置：**
- URL: `https://your-domain.com/wechat/callback`
- Token: 自定义字符串
- EncodingAESKey: 自动生成

### 钉钉机器人API

| 参数 | 说明 | 获取方式 |
|------|------|----------|
| Webhook URL | 机器人推送地址 | 群机器人设置 |
| Secret | 签名密钥 | 群机器人设置 |

**安全验证：**
- 使用HMAC-SHA256签名验证消息真实性
- 时间戳验证防止重放攻击

## 🔐 安全与合规

### 法律合规
- **隐私保护**: 仅监听和存储必要的工作相关消息
- **用户同意**: 确保获得相关方同意
- **数据最小化**: 只保留必要的证据信息
- **透明度**: 明确告知监听目的和范围

### 技术安全
- **消息加密**: 使用平台提供的加密机制
- **访问控制**: 严格限制API访问权限
- **审计日志**: 记录所有操作和取证行为
- **数据隔离**: 敏感数据单独存储和处理

## ⚠️ 注意事项

### 平台限制
1. **企业微信**: 需要企业账号，个人微信不支持
2. **钉钉**: 需要群主权限添加机器人
3. **微信网页版**: 可能违反微信使用协议，存在账号风险

### 技术挑战
1. **消息加密**: 处理平台的消息加密解密
2. **连接稳定性**: 处理网络中断和重连
3. **频率限制**: 遵守平台的API调用限制
4. **账号安全**: 保护登录凭据和API密钥

---

**重要提醒**: 请确保所有实现符合当地法律法规，仅用于合法的取证和合规目的。</content>
<parameter name="filePath">c:\Users\a2517\CODE\spoon-core\examples\REAL_MESSAGE_MONITOR_README.md