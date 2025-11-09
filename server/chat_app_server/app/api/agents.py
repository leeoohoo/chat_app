from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio

from ..models.config import AgentCreate, AgentUpdate
from ..services.v2.agent import build_sse_stream_from_agent_id, load_model_config_for_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await AgentCreate.get_all(user_id=user_id)


@router.post("")
async def create_agent(payload: AgentCreate) -> Dict[str, Any]:
    # 校验必须字段
    if not payload.name or not payload.ai_model_config_id:
        raise HTTPException(status_code=400, detail="name 和 ai_model_config_id 为必填项")
    return await AgentCreate.create(payload)


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    agent = await AgentCreate.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return agent


@router.put("/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdate) -> Dict[str, Any]:
    existing = await AgentCreate.get_by_id(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    updated = await AgentUpdate.update(agent_id, payload)
    return updated or existing


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str) -> Dict[str, Any]:
    existing = await AgentCreate.get_by_id(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    await AgentCreate.delete(agent_id)
    return {"ok": True}


# ========== 新增：智能体聊天流式接口 ==========

class AgentChatRequest(BaseModel):
    session_id: str = Field(description="会话ID")
    content: str = Field(description="消息内容")
    agent_id: str = Field(description="智能体ID")
    user_id: Optional[str] = Field(default=None, description="用户ID，用于按用户加载MCP配置")


@router.post("/chat/stream")
def agent_chat_stream(request: AgentChatRequest):
    """基于智能体ID的流式聊天接口（SSE）。"""
    try:
        return StreamingResponse(
            build_sse_stream_from_agent_id(
                session_id=request.session_id,
                content=request.content,
                agent_id=request.agent_id,
                user_id=request.user_id,
            ),
            media_type="text/event-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))