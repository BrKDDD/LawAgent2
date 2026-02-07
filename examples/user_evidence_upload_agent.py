"""
用户证据上传上链代理 - 允许用户上传证据并自动上链存储

功能：
1. 接受用户上传的证据（文本或文件）
2. 验证证据格式和内容
3. 自动将证据上链存储到区块链
4. 返回上链交易信息和证据哈希
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools.base import BaseTool
from spoon_ai.tools import ToolManager
from spoon_ai.chat import ChatBot
from pydantic import Field

logger = logging.getLogger(__name__)

class UserEvidenceUploadTool(BaseTool):
    """用户证据上传工具"""

    name: str = "upload_user_evidence"
    description: str = "处理用户上传的证据并上链存储"
    parameters: dict = {
        "type": "object",
        "properties": {
            "evidence_content": {
                "type": "string",
                "description": "证据内容文本"
            },
            "evidence_type": {
                "type": "string",
                "description": "证据类型，如'message', 'document', 'image', 'audio'等",
                "enum": ["message", "document", "image", "audio", "video", "binary", "other"]
            },
            "source": {
                "type": "string",
                "description": "证据来源描述，如'用户手动上传', '微信聊天记录'等"
            },
            "description": {
                "type": "string",
                "description": "证据描述（可选）"
            },
            "uploader_address": {
                "type": "string",
                "description": "上传者地址（可选，用于记录）"
            },
            "file_name": {
                "type": "string",
                "description": "上传文件名（可选）"
            },
            "file_path": {
                "type": "string",
                "description": "如果是从文件上传，提供文件路径（可选）"
            },
            "metadata": {
                "type": "object",
                "description": "额外的元数据，如标签、描述等（可选）"
            },
            "sign_with": {
                "type": "string",
                "description": "用于签名的钱包地址或私钥ID"
            }
        },
        "required": ["evidence_content", "evidence_type", "source", "sign_with"]
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 延迟初始化证据存储工具
        self._evidence_storage_tool = None

    @property
    def evidence_storage_tool(self):
        if self._evidence_storage_tool is None:
            from examples.auto_evidence_agent import EvidenceStorageTool
            self._evidence_storage_tool = EvidenceStorageTool()
        return self._evidence_storage_tool

    async def execute(
        self,
        evidence_content: str,
        evidence_type: str,
        source: str,
        sign_with: str,
        description: str = "",
        uploader_address: str = "",
        file_name: str = "",
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """处理用户上传的证据并上链"""

        try:
            # 验证输入
            if not evidence_content or not evidence_content.strip():
                return json.dumps(
                    {"status": "error", "error": "empty_content", "message": "证据内容不能为空"},
                    ensure_ascii=True,
                    indent=2,
                )

            if evidence_type not in ["message", "document", "image", "audio", "video", "binary", "other"]:
                return json.dumps(
                    {
                        "status": "error",
                        "error": "unsupported_type",
                        "message": f"不支持的证据类型: {evidence_type}",
                    },
                    ensure_ascii=True,
                    indent=2,
                )

            # 如果提供了文件路径，尝试读取文件内容
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    evidence_content = f"{evidence_content}\n\n文件内容:\n{file_content}"
                except Exception as e:
                    logger.warning(f"读取文件失败: {e}")
                    # 继续使用原始内容

            # 构建证据数据结构
            merged_metadata: Dict[str, Any] = {}
            if isinstance(metadata, dict):
                merged_metadata.update(metadata)
            if description:
                merged_metadata["description"] = description
            if uploader_address:
                merged_metadata["uploader_address"] = uploader_address
            if file_name:
                merged_metadata["file_name"] = file_name

            evidence_data = {
                "content": evidence_content.strip(),
                "type": evidence_type,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "uploader": uploader_address or "user",  # 标识为用户上传
                "metadata": merged_metadata
            }

            # 添加文件信息（如果有）
            if file_path:
                evidence_data["file_info"] = {
                    "path": file_path,
                    "exists": os.path.exists(file_path),
                    "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }

            # 使用证据存储工具上链
            result = await self.evidence_storage_tool.execute(
                evidence_data=evidence_data,
                sign_with=sign_with
            )

            # 证据工具会返回 JSON 字符串（成功/失败），这里统一解析并封装返回
            try:
                onchain = json.loads(result) if isinstance(result, str) else {"raw": str(result)}
            except Exception:
                onchain = {"raw": result}

            if isinstance(onchain, dict) and onchain.get("status") == "error":
                return json.dumps(
                    {
                        "status": "error",
                        "error": "onchain_failed",
                        "message": "证据上链失败",
                        "onchain": onchain,
                    },
                    ensure_ascii=True,
                    indent=2,
                )

            return json.dumps(
                {
                    "status": "success",
                    "message": "证据上传并上链成功",
                    "evidence": {
                        "type": evidence_type,
                        "source": source,
                        "content_preview": evidence_content[:200],
                        "timestamp": evidence_data["timestamp"],
                        "uploader_address": uploader_address,
                        "file_name": file_name,
                    },
                    "onchain": onchain,
                },
                ensure_ascii=True,
                indent=2,
            )

        except Exception as e:
            logger.error(f"证据上传处理失败: {e}")
            return json.dumps(
                {"status": "error", "error": "exception", "message": f"处理失败: {str(e)}"},
                ensure_ascii=True,
                indent=2,
            )

class UserEvidenceUploadAgent(ToolCallAgent):
    """用户证据上传上链代理"""

    name: str = "user_evidence_upload_agent"
    description: str = "允许用户上传证据并自动上链存储的代理"

    system_prompt: str = """
    你是一个用户证据上传上链代理，负责：
    1. 接受用户上传的各种证据（文本、文件等）
    2. 验证证据内容的有效性
    3. 自动将证据数据结构化并上链存储
    4. 返回上链结果和交易信息

    工作流程：
    1. 接收用户的证据上传请求
    2. 使用upload_user_evidence工具处理证据
    3. 确保证据成功上链
    4. 向用户返回详细的上链确认信息

    支持的证据类型：
    - message: 消息记录
    - document: 文档文件
    - image: 图片文件
    - audio: 音频文件
    - video: 视频文件
    - other: 其他类型

    注意：所有证据都会被永久存储到区块链上，请确保内容准确和合法。
    """

    next_step_prompt: str = "等待用户上传证据或提供证据信息"

    def __init__(self, **kwargs):
        # 设置默认的llm如果没有提供
        if 'llm' not in kwargs:
            kwargs['llm'] = ChatBot()

        # 初始化工具
        tools = [
            UserEvidenceUploadTool()
        ]
        kwargs['available_tools'] = ToolManager(tools)
