#!/usr/bin/env python3
"""
消息相关的数据模型
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from .database_factory import get_database
import asyncio
import uuid
import json

def row_to_dict(row) -> Dict[str, Any]:
    """将数据库行转换为字典"""
    if row is None:
        return None
    # SQLite Row对象可以直接转换为字典
    return {key: row[key] for key in row.keys()}

class MessageCreate(BaseModel):
    # 前端发送的字段名（驼峰命名）
    id: Optional[str] = None
    sessionId: str
    role: str
    content: str
    summary: Optional[str] = None
    toolCalls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    # 用于持久化的推理字段（内部统一使用该字段）
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None
    status: Optional[str] = None
    
    # 内部属性，用于数据库操作
    @property
    def session_id(self) -> str:
        return self.sessionId
    
    @session_id.setter
    def session_id(self, value: str):
        self.sessionId = value
    
    @property
    def tool_calls_str(self) -> Optional[str]:
        """将toolCalls转换为JSON字符串"""
        if self.toolCalls:
            return json.dumps(self.toolCalls)
        return None
    
    @property
    def metadata_str(self) -> Optional[str]:
        """将metadata转换为JSON字符串"""
        if self.metadata:
            return json.dumps(self.metadata)
        return None

    # 已不再需要统一属性，直接使用 reasoning 字段

    @classmethod
    async def create(cls, message_data: "MessageCreate") -> Dict[str, Any]:
        """创建新消息"""
        # 使用前端提供的ID，如果没有则生成新的
        message_id = message_data.id or str(uuid.uuid4())
        
        query = """
        INSERT INTO messages (id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        db = get_database()
        await db.execute_query_async(query, (
            message_id,
            message_data.session_id,  # 使用属性访问器
            message_data.role,
            message_data.content,
            message_data.summary,
            message_data.tool_calls_str,  # 使用JSON字符串转换
            message_data.tool_call_id,
            message_data.reasoning,
            message_data.metadata_str  # 使用JSON字符串转换
        ))
        
        return await cls.get_by_id(message_id)

    @classmethod
    def create_sync(cls, message_data: "MessageCreate") -> Dict[str, Any]:
        """创建新消息（同步版本）"""
        # 使用前端提供的ID，如果没有则生成新的
        message_id = message_data.id or str(uuid.uuid4())
        
        query = """
        INSERT INTO messages (id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        db = get_database()
        db.execute_sync(query, (
            message_id,
            message_data.session_id,  # 使用属性访问器
            message_data.role,
            message_data.content,
            message_data.summary,
            message_data.tool_calls_str,  # 使用JSON字符串转换
            message_data.tool_call_id,
            message_data.reasoning,
            message_data.metadata_str  # 使用JSON字符串转换
        ))
        
        return cls.get_by_id_sync(message_id)

    @classmethod
    def get_by_id_sync(cls, message_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取消息（同步版本）"""
        query = "SELECT * FROM messages WHERE id = ?"
        db = get_database()
        row = db.fetchone_sync(query, (message_id,))
        return row_to_dict(row)

    @classmethod
    async def get_by_session(cls, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取会话的所有消息"""
        query = "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC"
        params = (session_id,)
        
        if limit:
            query += " LIMIT ?"
            params = (session_id, limit)
        
        db = get_database()
        rows = await db.fetch_all_async(query, params)
        return [row_to_dict(row) for row in rows]

    @classmethod
    def get_by_session_sync(cls, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取会话的所有消息（同步版本）"""
        query = "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC"
        params = (session_id,)
        
        if limit:
            query += " LIMIT ?"
            params = (session_id, limit)
        
        db = get_database()
        rows = db.fetchall_sync(query, params)
        return [row_to_dict(row) for row in rows]

    @classmethod
    async def get_by_id(cls, message_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取消息"""
        query = "SELECT * FROM messages WHERE id = ?"
        db = get_database()
        row = await db.fetch_one_async(query, (message_id,))
        return row_to_dict(row)

    @classmethod
    async def delete_by_session(cls, session_id: str) -> bool:
        """删除会话的所有消息"""
        query = "DELETE FROM messages WHERE session_id = ?"
        db = get_database()
        cursor = await db.execute_query_async(query, (session_id,))
        return cursor.rowcount > 0

    @classmethod
    def delete_by_session_sync(cls, session_id: str) -> bool:
        """删除会话的所有消息（同步版本）"""
        query = "DELETE FROM messages WHERE session_id = ?"
        db = get_database()
        cursor = db.execute_sync(query, (session_id,))
        return cursor.rowcount > 0

class ChatStopRequest(BaseModel):
    session_id: str