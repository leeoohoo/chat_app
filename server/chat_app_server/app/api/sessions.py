# 会话相关API路由

import json
import logging
import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from app.models.session import SessionCreate, SessionMcpServerCreate, SessionService, SessionMcpServerService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sessions")
async def get_sessions(
    user_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    """获取会话列表"""
    try:
        # 支持按 user_id / project_id 过滤
        if user_id or project_id:
            sessions = await SessionService.get_by_user_project_async(user_id=user_id, project_id=project_id)
            logger.info(f"按过滤条件获取到 {len(sessions)} 个会话 user_id={user_id}, project_id={project_id}")
        else:
            sessions = await SessionService.get_all_async()
            logger.info(f"获取到 {len(sessions)} 个会话（未过滤）")
        return sessions
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")

@router.post("/sessions")
async def create_session(session: SessionCreate):
    """创建新会话"""
    try:
        session_id = await SessionService.create_async(session)
        # 获取创建的会话信息返回
        new_session = await SessionService.get_by_id_async(session_id)
        if new_session:
            new_session['id'] = session_id
        logger.info(f"创建会话成功: {session_id}")
        return new_session or {"id": session_id, "title": session.title}
        
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建会话失败")

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取特定会话"""
    try:
        session = await SessionService.get_by_id_async(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话失败")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        success = await SessionService.delete_async(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        logger.info(f"删除会话成功: {session_id}")
        return {"message": "会话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail="删除会话失败")

@router.get("/sessions/{session_id}/mcp-servers")
async def get_session_mcp_servers(session_id: str):
    """获取会话的MCP服务器配置"""
    try:
        servers = await SessionMcpServerService.get_by_session_async(session_id)
        logger.info(f"获取会话 {session_id} 的 {len(servers)} 个MCP服务器")
        return servers
        
    except Exception as e:
        logger.error(f"获取会话MCP服务器失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话MCP服务器失败")


@router.post("/sessions/{session_id}/mcp-servers")
async def add_session_mcp_server(session_id: str, server: SessionMcpServerCreate):
    """添加会话MCP服务器关联"""
    try:
        # 设置会话ID
        server.session_id = session_id
        server_id = await SessionMcpServerService.create_async(server)
        
        logger.info(f"为会话 {session_id} 添加MCP服务器成功: {server_id}")
        return {"id": server_id, "session_id": session_id, "mcp_server_name": server.mcp_server_name}
        
    except Exception as e:
        logger.error(f"添加会话MCP服务器失败: {e}")
        raise HTTPException(status_code=500, detail="添加会话MCP服务器失败")


@router.delete("/sessions/{session_id}/mcp-servers/{mcp_config_id}")
async def delete_session_mcp_server(session_id: str, mcp_config_id: str):
    """删除会话MCP服务器关联"""
    try:
        success = await SessionMcpServerService.delete_by_session_async(session_id)
        logger.info(f"删除会话 {session_id} 的MCP服务器关联成功")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"删除会话MCP服务器关联失败: {e}")
        raise HTTPException(status_code=500, detail="删除会话MCP服务器关联失败")