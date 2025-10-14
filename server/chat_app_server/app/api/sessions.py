# 会话相关API路由

import json
import logging
import time
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from app.models.session import SessionCreate, SessionMcpServerCreate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sessions")
async def get_sessions(user_id: Optional[str] = Query(None)):
    """获取会话列表"""
    try:
        sessions = await SessionCreate.get_all(user_id=user_id)
        logger.info(f"获取到 {len(sessions)} 个会话")
        return sessions
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")

@router.post("/sessions")
async def create_session(session: SessionCreate):
    """创建新会话"""
    try:
        new_session = await SessionCreate.create(session)
        logger.info(f"创建会话成功: {new_session['id']}")
        return new_session
        
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建会话失败")

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取特定会话"""
    try:
        session = await SessionCreate.get_by_id(session_id)
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
        success = await SessionCreate.delete(session_id)
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
        servers = await SessionMcpServerCreate.get_by_session(session_id)
        logger.info(f"获取会话 {session_id} 的 {len(servers)} 个MCP服务器")
        return servers
        
    except Exception as e:
        logger.error(f"获取会话MCP服务器失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话MCP服务器失败")


@router.post("/sessions/{session_id}/mcp-servers")
async def add_session_mcp_server(session_id: str, server: SessionMcpServerCreate):
    try:
        server_id = str(int(time.time() * 1000))
        
        await db.execute(
            'INSERT INTO session_mcp_servers (id, session_id, mcp_config_id) VALUES (?, ?, ?)',
            (server_id, session_id, server.mcp_config_id)
        )
        
        db.connection.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        session_mcp_server = await db.fetchone(
            'SELECT * FROM session_mcp_servers WHERE id = ?',
            (server_id,)
        )
        return session_mcp_server
        
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.delete("/sessions/{session_id}/mcp-servers/{mcp_config_id}")
async def delete_session_mcp_server(session_id: str, mcp_config_id: str):
    try:
        await db.execute(
            'DELETE FROM session_mcp_servers WHERE session_id = ? AND mcp_config_id = ?',
            (session_id, mcp_config_id)
        )
        return {"success": True}
        
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))