#!/usr/bin/env python3
"""
Chat API v2 (Agent 版本)
使用新的 Agent 封装实现 /v2/chat/stream 流式接口
"""

import json
import logging
import os
import queue
import threading
import time
from typing import Dict, Any, Optional, Generator, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.v2.agent import build_sse_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2")


# ===== 数据模型（与 chat_api_v2 保持一致） =====

class ModelConfigV2(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_name: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=4000, gt=0, description="最大token数")
    use_tools: bool = Field(default=True, description="是否使用工具")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")


class ChatRequestV2(BaseModel):
    session_id: str = Field(description="会话ID")
    content: str = Field(description="消息内容")
    ai_model_config: Optional[ModelConfigV2] = Field(default=None, description="模型配置")
    user_id: Optional[str] = Field(default=None, description="用户ID，用于按用户加载MCP配置")






@router.post("/chat/stream")
def chat_stream_v2_agent(request: ChatRequestV2):
    """基于 Agent 的流式聊天接口（SSE）。"""
    try:
        model_config = request.ai_model_config.dict() if request.ai_model_config else None
        return StreamingResponse(
            build_sse_stream(
                session_id=request.session_id,
                content=request.content,
                model_config=model_config,
                user_id=request.user_id,
            ),
            media_type="text/event-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"chat_stream_v2_agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))