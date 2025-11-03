#!/usr/bin/env python3
"""
配置相关的数据模型
"""
import uuid
import json
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from .database_factory import get_database

def row_to_dict(row) -> Dict[str, Any]:
    """将数据库行转换为字典"""
    if row is None:
        return None
    # SQLite Row对象可以直接转换为字典
    return {key: row[key] for key in row.keys()}

class McpConfigCreate(BaseModel):
    name: str
    command: str
    type: str = "stdio"
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    user_id: Optional[str] = None
    enabled: bool = True

    @classmethod
    async def create(cls, config_data: "McpConfigCreate") -> Dict[str, Any]:
        """创建MCP配置"""
        db = get_database()
        config_id = str(uuid.uuid4())
        
        # 将列表和字典转换为JSON字符串
        args_json = json.dumps(config_data.args) if config_data.args else None
        env_json = json.dumps(config_data.env) if config_data.env else None
        
        query = """
        INSERT INTO mcp_configs (id, name, command, type, args, env, user_id, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        await db.execute_query_async(query, (
            config_id,
            config_data.name,
            config_data.command,
            config_data.type,
            args_json,
            env_json,
            config_data.user_id,
            config_data.enabled
        ))
        
        return await cls.get_by_id(config_id)

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有MCP配置"""
        db = get_database()
        if user_id and user_id.strip():
            query = "SELECT * FROM mcp_configs WHERE user_id = ? ORDER BY created_at DESC"
            rows = await db.fetch_all_async(query, (user_id,))
        else:
            query = "SELECT * FROM mcp_configs ORDER BY created_at DESC"
            rows = await db.fetch_all_async(query)
        
        configs = []
        for row in rows:
            config = row_to_dict(row)
            if config:
                # 解析JSON字段
                if config.get('args'):
                    try:
                        config['args'] = json.loads(config['args'])
                    except (json.JSONDecodeError, TypeError):
                        config['args'] = None
                
                if config.get('env'):
                    try:
                        config['env'] = json.loads(config['env'])
                    except (json.JSONDecodeError, TypeError):
                        config['env'] = None
                
                configs.append(config)
        
        return configs

    @classmethod
    async def get_by_id(cls, config_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取MCP配置"""
        db = get_database()
        query = "SELECT * FROM mcp_configs WHERE id = ?"
        row = await db.fetch_one_async(query, (config_id,))
        
        if row:
            config = row_to_dict(row)
            # 解析JSON字段
            if config.get('args'):
                try:
                    config['args'] = json.loads(config['args'])
                except (json.JSONDecodeError, TypeError):
                    config['args'] = None
            
            if config.get('env'):
                try:
                    config['env'] = json.loads(config['env'])
                except (json.JSONDecodeError, TypeError):
                    config['env'] = None
            
            return config
        return None

    @classmethod
    async def delete(cls, config_id: str) -> bool:
        """删除MCP配置"""
        db = get_database()
        query = "DELETE FROM mcp_configs WHERE id = ?"
        await db.execute_query_async(query, (config_id,))
        return True

class McpConfigUpdate(BaseModel):
    name: Optional[str] = None
    command: Optional[str] = None
    type: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None

    @classmethod
    async def update(cls, config_id: str, update_data: "McpConfigUpdate") -> Optional[Dict[str, Any]]:
        """更新MCP配置"""
        db = get_database()
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        if update_data.name is not None:
            update_fields.append("name = ?")
            update_values.append(update_data.name)
        
        if update_data.command is not None:
            update_fields.append("command = ?")
            update_values.append(update_data.command)
        
        if update_data.type is not None:
            update_fields.append("type = ?")
            update_values.append(update_data.type)
        
        if update_data.args is not None:
            update_fields.append("args = ?")
            update_values.append(json.dumps(update_data.args))
        
        if update_data.env is not None:
            update_fields.append("env = ?")
            update_values.append(json.dumps(update_data.env))
        
        if update_data.enabled is not None:
            update_fields.append("enabled = ?")
            update_values.append(update_data.enabled)
        
        if not update_fields:
            return await McpConfigCreate.get_by_id(config_id)
        
        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # 添加WHERE条件的值
        update_values.append(config_id)
        
        query = f"UPDATE mcp_configs SET {', '.join(update_fields)} WHERE id = ?"
        await db.execute_query_async(query, tuple(update_values))
        
        return await McpConfigCreate.get_by_id(config_id)

class AiModelConfigCreate(BaseModel):
    name: str
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    user_id: Optional[str] = None
    enabled: bool = True

    @classmethod
    async def create(cls, config_data: "AiModelConfigCreate") -> Dict[str, Any]:
        """创建AI模型配置"""
        db = get_database()
        config_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO ai_model_configs (id, name, provider, model, api_key, base_url, user_id, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        await db.execute_query_async(query, (
            config_id,
            config_data.name,
            config_data.provider,
            config_data.model,
            config_data.api_key,
            config_data.base_url,
            config_data.user_id,
            config_data.enabled
        ))
        
        return await cls.get_by_id(config_id)

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有AI模型配置"""
        db = get_database()
        if user_id and user_id.strip():
            query = "SELECT * FROM ai_model_configs WHERE user_id = ? ORDER BY created_at DESC"
            rows = await db.fetch_all_async(query, (user_id,))
        else:
            query = "SELECT * FROM ai_model_configs ORDER BY created_at DESC"
            rows = await db.fetch_all_async(query)
        
        return [row_to_dict(row) for row in rows if row]

    @classmethod
    async def get_by_id(cls, config_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取AI模型配置"""
        db = get_database()
        query = "SELECT * FROM ai_model_configs WHERE id = ?"
        row = await db.fetch_one_async(query, (config_id,))
        return row_to_dict(row) if row else None

    @classmethod
    async def delete(cls, config_id: str) -> bool:
        """删除AI模型配置"""
        db = get_database()
        query = "DELETE FROM ai_model_configs WHERE id = ?"
        await db.execute_query_async(query, (config_id,))
        return True

class AiModelConfigUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: Optional[bool] = None

    @classmethod
    async def update(cls, config_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新AI模型配置"""
        db = get_database()
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        for field in ['name', 'provider', 'model', 'api_key', 'base_url', 'enabled']:
            if field in update_data and update_data[field] is not None:
                update_fields.append(f"{field} = ?")
                update_values.append(update_data[field])
        
        if not update_fields:
            return await AiModelConfigCreate.get_by_id(config_id)
        
        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # 添加WHERE条件的值
        update_values.append(config_id)
        
        query = f"UPDATE ai_model_configs SET {', '.join(update_fields)} WHERE id = ?"
        await db.execute_query_async(query, tuple(update_values))
        
        return await AiModelConfigCreate.get_by_id(config_id)

class SystemContextCreate(BaseModel):
    name: str
    content: Optional[str] = None
    user_id: Optional[str] = None
    is_active: bool = False

    @classmethod
    async def create(cls, context_data: "SystemContextCreate") -> Dict[str, Any]:
        """创建系统上下文"""
        db = get_database()
        context_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO system_contexts (id, name, content, user_id, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        await db.execute_query_async(query, (
            context_id,
            context_data.name,
            context_data.content,
            context_data.user_id,
            context_data.is_active
        ))
        
        return await cls.get_by_id(context_id)

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有系统上下文"""
        db = get_database()
        if user_id and user_id.strip():
            query = "SELECT * FROM system_contexts WHERE user_id = ? ORDER BY created_at DESC"
            rows = await db.fetch_all_async(query, (user_id,))
        else:
            query = "SELECT * FROM system_contexts ORDER BY created_at DESC"
            rows = await db.fetch_all_async(query)
        
        return [row_to_dict(row) for row in rows if row]

    @classmethod
    async def get_by_id(cls, context_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取系统上下文"""
        db = get_database()
        query = "SELECT * FROM system_contexts WHERE id = ?"
        row = await db.fetch_one_async(query, (context_id,))
        return row_to_dict(row) if row else None

    @classmethod
    async def get_active(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """获取活跃的系统上下文"""
        db = get_database()
        query = "SELECT * FROM system_contexts WHERE user_id = ? AND is_active = 1 LIMIT 1"
        row = await db.fetch_one_async(query, (user_id,))
        return row_to_dict(row) if row else None

class SystemContextUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None

    @classmethod
    async def update(cls, context_id: str, update_data: "SystemContextUpdate") -> Optional[Dict[str, Any]]:
        """更新系统上下文"""
        db = get_database()
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        if update_data.name is not None:
            update_fields.append("name = ?")
            update_values.append(update_data.name)
        
        if update_data.content is not None:
            update_fields.append("content = ?")
            update_values.append(update_data.content)
        
        if update_data.is_active is not None:
            update_fields.append("is_active = ?")
            update_values.append(update_data.is_active)
        
        if not update_fields:
            return await SystemContextCreate.get_by_id(context_id)
        
        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # 添加WHERE条件的值
        update_values.append(context_id)
        
        query = f"UPDATE system_contexts SET {', '.join(update_fields)} WHERE id = ?"
        await db.execute_query_async(query, tuple(update_values))
        
        return await SystemContextCreate.get_by_id(context_id)

class SystemContextActivate(BaseModel):
    user_id: str
    is_active: bool = True

    @classmethod
    async def activate(cls, context_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """激活系统上下文（同时取消其他活跃状态）"""
        db = get_database()
        
        # 首先取消该用户的所有活跃上下文
        deactivate_query = "UPDATE system_contexts SET is_active = 0 WHERE user_id = ?"
        await db.execute_query_async(deactivate_query, (user_id,))
        
        # 然后激活指定的上下文
        activate_query = "UPDATE system_contexts SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?"
        await db.execute_query_async(activate_query, (context_id, user_id))
        
        return await SystemContextCreate.get_by_id(context_id)