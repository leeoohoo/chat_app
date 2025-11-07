from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

from ..models.config import AgentCreate, AgentUpdate

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