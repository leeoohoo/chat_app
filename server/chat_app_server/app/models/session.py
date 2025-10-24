# 会话相关数据模型

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import json
from . import db

def row_to_dict(row) -> Dict[str, Any]:
    """将数据库行转换为字典"""
    if row is None:
        return None
    # SQLite Row对象可以直接转换为字典
    return {key: row[key] for key in row.keys()}

class SessionCreate(BaseModel):
    title: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None

    @classmethod
    async def create(cls, session_data: "SessionCreate") -> Dict[str, Any]:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO sessions (id, title, user_id, project_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        
        await db.execute(query, (
            session_id,
            session_data.title,
            session_data.user_id,
            session_data.project_id
        ))
        
        # 返回创建的会话
        return await cls.get_by_id(session_id)

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有会话"""
        if user_id:
            query = "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC"
            rows = await db.fetchall(query, (user_id,))
        else:
            query = "SELECT * FROM sessions ORDER BY updated_at DESC"
            rows = await db.fetchall(query)
        
        return [row_to_dict(row) for row in rows]

    @classmethod
    async def get_by_id(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取会话"""
        query = "SELECT * FROM sessions WHERE id = ?"
        row = await db.fetchone(query, (session_id,))
        return row_to_dict(row)

    @classmethod
    async def delete(cls, session_id: str) -> bool:
        """删除会话"""
        query = "DELETE FROM sessions WHERE id = ?"
        cursor = await db.execute(query, (session_id,))
        return cursor.rowcount > 0

    @classmethod
    def delete_sync(cls, session_id: str) -> bool:
        """删除会话（同步版本）"""
        query = "DELETE FROM sessions WHERE id = ?"
        cursor = db.execute_sync(query, (session_id,))
        return cursor.rowcount > 0

class SessionMcpServerCreate(BaseModel):
    session_id: str
    mcp_config_id: str
    enabled: bool = True

    @classmethod
    async def create(cls, data: "SessionMcpServerCreate") -> Dict[str, Any]:
        """创建会话MCP服务器关联"""
        server_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO session_mcp_servers (id, session_id, mcp_config_id, enabled, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        await db.execute(query, (
            server_id,
            data.session_id,
            data.mcp_config_id,
            data.enabled
        ))
        
        return await cls.get_by_id(server_id)

    @classmethod
    async def get_by_session(cls, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的MCP服务器"""
        query = """
        SELECT sms.*, mc.name, mc.command, mc.type, mc.args, mc.env
        FROM session_mcp_servers sms
        JOIN mcp_configs mc ON sms.mcp_config_id = mc.id
        WHERE sms.session_id = ? AND sms.enabled = true
        """
        rows = await db.fetchall(query, (session_id,))
        return [row_to_dict(row) for row in rows]

    @classmethod
    async def get_by_id(cls, server_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取会话MCP服务器"""
        query = "SELECT * FROM session_mcp_servers WHERE id = ?"
        row = await db.fetchone(query, (server_id,))
        return row_to_dict(row)