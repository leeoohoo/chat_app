# 配置相关数据模型

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json
from . import db

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
        config_id = str(uuid.uuid4())
        
        # 将列表和字典转换为JSON字符串
        args_json = json.dumps(config_data.args) if config_data.args else None
        env_json = json.dumps(config_data.env) if config_data.env else None
        
        query = """
        INSERT INTO mcp_configs (id, name, command, type, args, env, user_id, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        await db.execute(query, (
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
        if user_id and user_id.strip():
            query = "SELECT * FROM mcp_configs WHERE user_id = ? ORDER BY created_at DESC"
            rows = await db.fetchall(query, (user_id,))
        else:
            query = "SELECT * FROM mcp_configs ORDER BY created_at DESC"
            rows = await db.fetchall(query)
        
        configs = []
        for row in rows:
            config = row_to_dict(row)
            # 解析JSON字段
            if config.get('args'):
                try:
                    config['args'] = json.loads(config['args'])
                except json.JSONDecodeError:
                    config['args'] = None
            if config.get('env'):
                try:
                    config['env'] = json.loads(config['env'])
                except json.JSONDecodeError:
                    config['env'] = None
            configs.append(config)
        
        return configs

    @classmethod
    async def get_by_id(cls, config_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取MCP配置"""
        query = "SELECT * FROM mcp_configs WHERE id = ?"
        row = await db.fetchone(query, (config_id,))
        if row:
            config = row_to_dict(row)
            # 解析JSON字段
            if config.get('args'):
                try:
                    config['args'] = json.loads(config['args'])
                except json.JSONDecodeError:
                    config['args'] = None
            if config.get('env'):
                try:
                    config['env'] = json.loads(config['env'])
                except json.JSONDecodeError:
                    config['env'] = None
            return config
        return None

    @classmethod
    async def delete(cls, config_id: str) -> bool:
        """删除MCP配置"""
        query = "DELETE FROM mcp_configs WHERE id = ?"
        result = await db.execute(query, (config_id,))
        return result.rowcount > 0

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
        # 构建更新字段和值
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
            # 没有字段需要更新
            return await McpConfigCreate.get_by_id(config_id)
        
        # 添加更新时间
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # 构建SQL查询
        query = f"UPDATE mcp_configs SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(config_id)
        
        # 执行更新
        result = await db.execute(query, tuple(update_values))
        
        if result.rowcount > 0:
            return await McpConfigCreate.get_by_id(config_id)
        else:
            return None

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
        """创建新的AI模型配置"""
        config_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO ai_model_configs (id, name, provider, model, api_key, base_url, user_id, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        await db.execute(query, (
            config_id,
            config_data.name,
            config_data.provider,
            config_data.model,
            config_data.api_key,
            config_data.base_url,
            config_data.user_id,
            config_data.enabled
        ))
        
        # 返回创建的配置
        return await cls.get_by_id(config_id)

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有AI模型配置"""
        if user_id and user_id.strip():
            query = "SELECT * FROM ai_model_configs WHERE user_id = ? ORDER BY created_at DESC"
            rows = await db.fetchall(query, (user_id,))
        else:
            query = "SELECT * FROM ai_model_configs ORDER BY created_at DESC"
            rows = await db.fetchall(query)
        
        return [row_to_dict(row) for row in rows]

    @classmethod
    async def get_by_id(cls, config_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取AI模型配置"""
        query = "SELECT * FROM ai_model_configs WHERE id = ?"
        row = await db.fetchone(query, (config_id,))
        return row_to_dict(row)

    @classmethod
    async def delete(cls, config_id: str) -> bool:
        """删除AI模型配置"""
        query = "DELETE FROM ai_model_configs WHERE id = ?"
        await db.execute(query, (config_id,))
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
        # 构建更新字段
        update_fields = []
        update_values = []
        
        if "name" in update_data and update_data["name"] is not None:
            update_fields.append("name = ?")
            update_values.append(update_data["name"])
        
        if "provider" in update_data and update_data["provider"] is not None:
            update_fields.append("provider = ?")
            update_values.append(update_data["provider"])
            
        if "model" in update_data and update_data["model"] is not None:
            update_fields.append("model = ?")
            update_values.append(update_data["model"])
            
        if "api_key" in update_data and update_data["api_key"] is not None:
            update_fields.append("api_key = ?")
            update_values.append(update_data["api_key"])
            
        if "base_url" in update_data and update_data["base_url"] is not None:
            update_fields.append("base_url = ?")
            update_values.append(update_data["base_url"])
            
        if "enabled" in update_data and update_data["enabled"] is not None:
            update_fields.append("enabled = ?")
            update_values.append(update_data["enabled"])
        
        if not update_fields:
            # 没有字段需要更新
            return await AiModelConfigCreate.get_by_id(config_id)
        
        # 添加 updated_at 字段
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # 添加config_id到参数列表
        update_values.append(config_id)
        
        query = f"UPDATE ai_model_configs SET {', '.join(update_fields)} WHERE id = ?"
        
        await db.execute(query, tuple(update_values))
        
        # 返回更新后的配置
        return await AiModelConfigCreate.get_by_id(config_id)

class SystemContextCreate(BaseModel):
    name: str
    content: Optional[str] = None
    user_id: Optional[str] = None
    is_active: bool = False

    @classmethod
    async def create(cls, context_data: "SystemContextCreate") -> Dict[str, Any]:
        """创建系统上下文"""
        context_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO system_contexts (id, name, content, user_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        
        await db.execute(query, (
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
        if user_id and user_id.strip():
            query = "SELECT * FROM system_contexts WHERE user_id = ? ORDER BY created_at DESC"
            rows = await db.fetchall(query, (user_id,))
        else:
            query = "SELECT * FROM system_contexts ORDER BY created_at DESC"
            rows = await db.fetchall(query)
        
        return [row_to_dict(row) for row in rows]

    @classmethod
    async def get_by_id(cls, context_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取系统上下文"""
        query = "SELECT * FROM system_contexts WHERE id = ?"
        row = await db.fetchone(query, (context_id,))
        return row_to_dict(row)

    @classmethod
    async def get_active(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """获取活跃的系统上下文"""
        query = "SELECT * FROM system_contexts WHERE user_id = ? AND is_active = true LIMIT 1"
        row = await db.fetchone(query, (user_id,))
        return row_to_dict(row)

class SystemContextUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None

    @classmethod
    async def update(cls, context_id: str, update_data: "SystemContextUpdate") -> Optional[Dict[str, Any]]:
        """更新系统上下文"""
        # 构建动态更新查询
        fields = []
        params = []
        
        if update_data.name is not None:
            fields.append("name = ?")
            params.append(update_data.name)
        if update_data.content is not None:
            fields.append("content = ?")
            params.append(update_data.content)
        if update_data.is_active is not None:
            fields.append("is_active = ?")
            params.append(update_data.is_active)
        
        if not fields:
            return await SystemContextCreate.get_by_id(context_id)
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(context_id)
        
        query = f"UPDATE system_contexts SET {', '.join(fields)} WHERE id = ?"
        await db.execute(query, tuple(params))
        
        return await SystemContextCreate.get_by_id(context_id)

class SystemContextActivate(BaseModel):
    user_id: str
    is_active: bool = True

    @classmethod
    async def activate(cls, context_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """激活系统上下文（同时取消其他活跃状态）"""
        # 首先取消该用户的所有活跃上下文
        await db.execute(
            "UPDATE system_contexts SET is_active = false WHERE user_id = ?",
            (user_id,)
        )
        
        # 激活指定上下文
        await db.execute(
            "UPDATE system_contexts SET is_active = true, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (context_id,)
        )
        
        return await SystemContextCreate.get_by_id(context_id)