#!/usr/bin/env python3
"""
会话相关的数据模型
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from .database_factory import get_database
import asyncio
import uuid


class SessionCreate(BaseModel):
    """会话创建模型"""
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionMcpServerCreate(BaseModel):
    """会话MCP服务器关联创建模型"""
    session_id: str
    mcp_server_name: str
    config: Optional[Dict[str, Any]] = None


class SessionService:
    """会话数据服务"""
    
    @classmethod
    def create(cls, session_data: SessionCreate) -> str:
        """创建会话"""
        session_id = str(uuid.uuid4())
        
        db = get_database()
        db.execute_sync(
            """
            INSERT INTO sessions (id, title, description, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, session_data.title, session_data.description, 
             str(session_data.metadata) if session_data.metadata else None, 
             datetime.now(), datetime.now())
        )
        return session_id
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """获取所有会话"""
        db = get_database()
        rows = db.fetchall_sync("SELECT * FROM sessions ORDER BY updated_at DESC")
        return [dict(row) for row in rows]
    
    @classmethod
    def get_by_id(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取会话"""
        db = get_database()
        row = db.fetchone_sync("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return dict(row) if row else None
    
    @classmethod
    def delete(cls, session_id: str) -> bool:
        """删除会话"""
        db = get_database()
        cursor = db.execute_sync("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0
    
    @classmethod
    async def delete_async(cls, session_id: str) -> bool:
        """异步删除会话"""
        return await asyncio.to_thread(cls.delete, session_id)


class SessionMcpServerService:
    """会话MCP服务器关联数据服务"""
    
    @classmethod
    def create(cls, server_data: SessionMcpServerCreate) -> int:
        """创建会话MCP服务器关联"""
        db = get_database()
        cursor = db.execute_sync(
            """
            INSERT INTO session_mcp_servers (session_id, mcp_server_name, config, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (server_data.session_id, server_data.mcp_server_name, 
             str(server_data.config) if server_data.config else None, datetime.now())
        )
        return cursor.lastrowid
    
    @classmethod
    def get_by_session(cls, session_id: str) -> List[Dict[str, Any]]:
        """根据会话ID获取MCP服务器关联"""
        db = get_database()
        rows = db.fetchall_sync("SELECT * FROM session_mcp_servers WHERE session_id = ?", (session_id,))
        return [dict(row) for row in rows]
    
    @classmethod
    def delete_by_session(cls, session_id: str) -> bool:
        """根据会话ID删除MCP服务器关联"""
        db = get_database()
        cursor = db.execute_sync("DELETE FROM session_mcp_servers WHERE session_id = ?", (session_id,))
        return cursor.rowcount > 0
    
    @classmethod
    async def delete_by_session_async(cls, session_id: str) -> bool:
        """异步根据会话ID删除MCP服务器关联"""
        return await asyncio.to_thread(cls.delete_by_session, session_id)


# 为了向后兼容，保留旧的类名作为别名
# 这样现有的代码仍然可以工作
class SessionOperations:
    """向后兼容的会话操作类（已弃用，请使用 SessionService）"""
    
    @classmethod
    def create(cls, session_data):
        """创建会话 - 向后兼容方法"""
        if isinstance(session_data, dict):
            # 如果传入的是字典，转换为 SessionCreate 模型
            session_model = SessionCreate(**session_data)
            return SessionService.create(session_model)
        elif hasattr(session_data, 'title'):
            # 如果传入的是 SessionCreate 模型
            return SessionService.create(session_data)
        else:
            # 如果是旧的调用方式（直接传参数）
            return SessionService.create(SessionCreate(
                title=session_data,
                description=None,
                metadata=None
            ))
    
    @classmethod
    def get_all(cls):
        return SessionService.get_all()
    
    @classmethod
    def get_by_id(cls, session_id: str):
        return SessionService.get_by_id(session_id)
    
    @classmethod
    def delete(cls, session_id: str):
        return SessionService.delete(session_id)
    
    @classmethod
    async def delete_async(cls, session_id: str):
        return await SessionService.delete_async(session_id)