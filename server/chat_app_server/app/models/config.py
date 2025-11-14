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
    cwd: Optional[str] = None
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
        INSERT INTO mcp_configs (id, name, command, type, args, env, cwd, user_id, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        await db.execute_query_async(query, (
            config_id,
            config_data.name,
            config_data.command,
            config_data.type,
            args_json,
            env_json,
            config_data.cwd,
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
                # 保留cwd为字符串（可为空）
                
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
            # 保留cwd原样
            
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
    cwd: Optional[str] = None
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
        
        if update_data.cwd is not None:
            update_fields.append("cwd = ?")
            update_values.append(update_data.cwd)
        
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


class McpConfigProfileCreate(BaseModel):
    mcp_config_id: str
    name: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    enabled: bool = False

    @classmethod
    async def create(cls, data: "McpConfigProfileCreate") -> Dict[str, Any]:
        db = get_database()
        profile_id = str(uuid.uuid4())
        args_json = json.dumps(data.args) if data.args else None
        env_json = json.dumps(data.env) if data.env else None
        query = """
        INSERT INTO mcp_config_profiles (id, mcp_config_id, name, args, env, cwd, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        await db.execute_query_async(query, (
            profile_id,
            data.mcp_config_id,
            data.name,
            args_json,
            env_json,
            data.cwd,
            data.enabled,
        ))
        return await McpConfigProfileCreate.get_by_id(profile_id)

    @classmethod
    async def get_by_id(cls, profile_id: str) -> Optional[Dict[str, Any]]:
        db = get_database()
        row = await db.fetch_one_async("SELECT * FROM mcp_config_profiles WHERE id = ?", (profile_id,))
        if not row:
            return None
        d = row_to_dict(row)
        if d.get("args"):
            try:
                d["args"] = json.loads(d["args"])
            except Exception:
                d["args"] = None
        if d.get("env"):
            try:
                d["env"] = json.loads(d["env"])
            except Exception:
                d["env"] = None
        return d

    @classmethod
    async def list_by_config(cls, mcp_config_id: str) -> List[Dict[str, Any]]:
        db = get_database()
        rows = await db.fetch_all_async("SELECT * FROM mcp_config_profiles WHERE mcp_config_id = ? ORDER BY created_at DESC", (mcp_config_id,))
        out: List[Dict[str, Any]] = []
        for row in rows:
            d = row_to_dict(row)
            if d.get("args"):
                try:
                    d["args"] = json.loads(d["args"])
                except Exception:
                    d["args"] = None
            if d.get("env"):
                try:
                    d["env"] = json.loads(d["env"])
                except Exception:
                    d["env"] = None
            out.append(d)
        return out

    @classmethod
    async def delete(cls, profile_id: str) -> bool:
        """删除配置档案"""
        db = get_database()
        await db.execute_query_async(
            "DELETE FROM mcp_config_profiles WHERE id = ?",
            (profile_id,)
        )
        return True

class McpConfigProfileUpdate(BaseModel):
    name: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    enabled: Optional[bool] = None

    @classmethod
    async def update(cls, profile_id: str, data: "McpConfigProfileUpdate") -> Optional[Dict[str, Any]]:
        db = get_database()
        fields = []
        values: List[Any] = []
        if data.name is not None:
            fields.append("name = ?")
            values.append(data.name)
        if data.args is not None:
            fields.append("args = ?")
            values.append(json.dumps(data.args))
        if data.env is not None:
            fields.append("env = ?")
            values.append(json.dumps(data.env))
        if data.cwd is not None:
            fields.append("cwd = ?")
            values.append(data.cwd)
        if data.enabled is not None:
            fields.append("enabled = ?")
            values.append(data.enabled)
        if not fields:
            return await McpConfigProfileCreate.get_by_id(profile_id)
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(profile_id)
        query = f"UPDATE mcp_config_profiles SET {', '.join(fields)} WHERE id = ?"
        await db.execute_query_async(query, tuple(values))
        return await McpConfigProfileCreate.get_by_id(profile_id)

class McpConfigProfileActivate(BaseModel):
    mcp_config_id: str
    profile_id: str

    @classmethod
    async def activate(cls, mcp_config_id: str, profile_id: str) -> Optional[Dict[str, Any]]:
        db = get_database()
        # 禁用该配置下其他档案
        await db.execute_query_async(
            "UPDATE mcp_config_profiles SET enabled = 0, updated_at = CURRENT_TIMESTAMP WHERE mcp_config_id = ?",
            (mcp_config_id,)
        )
        # 启用目标档案
        await db.execute_query_async(
            "UPDATE mcp_config_profiles SET enabled = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (profile_id,)
        )
        return await McpConfigProfileCreate.get_by_id(profile_id)

    @classmethod
    async def get_active(cls, mcp_config_id: str) -> Optional[Dict[str, Any]]:
        db = get_database()
        row = await db.fetch_one_async(
            "SELECT * FROM mcp_config_profiles WHERE mcp_config_id = ? AND enabled = 1",
            (mcp_config_id,)
        )
        if not row:
            return None
        d = row_to_dict(row)
        if d.get("args"):
            try:
                d["args"] = json.loads(d["args"])
            except Exception:
                d["args"] = None
        if d.get("env"):
            try:
                d["env"] = json.loads(d["env"])
            except Exception:
                d["env"] = None
        return d

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


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ai_model_config_id: str
    mcp_config_ids: Optional[List[str]] = None
    callable_agent_ids: Optional[List[str]] = None
    system_context_id: Optional[str] = None
    user_id: Optional[str] = None
    enabled: bool = True

    @classmethod
    async def create(cls, data: "AgentCreate") -> Dict[str, Any]:
        """创建智能体配置"""
        db = get_database()
        agent_id = str(uuid.uuid4())
        mcp_ids_json = json.dumps(data.mcp_config_ids or [])
        callable_ids_json = json.dumps(data.callable_agent_ids or [])
        query = """
        INSERT INTO agents (id, name, description, ai_model_config_id, mcp_config_ids, callable_agent_ids, system_context_id, user_id, enabled, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        await db.execute_query_async(query, (
            agent_id,
            data.name,
            data.description,
            data.ai_model_config_id,
            mcp_ids_json,
            callable_ids_json,
            data.system_context_id,
            data.user_id,
            data.enabled
        ))
        return await AgentCreate.get_by_id(agent_id)

    @classmethod
    async def get_by_id(cls, agent_id: str) -> Optional[Dict[str, Any]]:
        db = get_database()
        row = await db.fetch_one_async("SELECT * FROM agents WHERE id = ?", (agent_id,))
        if not row:
            return None
        d = row_to_dict(row)
        # 解析mcp_config_ids
        try:
            d["mcp_config_ids"] = json.loads(d.get("mcp_config_ids") or "[]")
        except Exception:
            d["mcp_config_ids"] = []
        # 解析callable_agent_ids
        try:
            d["callable_agent_ids"] = json.loads(d.get("callable_agent_ids") or "[]")
        except Exception:
            d["callable_agent_ids"] = []
        return d

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = get_database()
        if user_id and user_id.strip():
            rows = await db.fetch_all_async("SELECT * FROM agents WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
            rows = await db.fetch_all_async("SELECT * FROM agents ORDER BY created_at DESC")
        out: List[Dict[str, Any]] = []
        for row in rows:
            d = row_to_dict(row)
            try:
                d["mcp_config_ids"] = json.loads(d.get("mcp_config_ids") or "[]")
            except Exception:
                d["mcp_config_ids"] = []
            try:
                d["callable_agent_ids"] = json.loads(d.get("callable_agent_ids") or "[]")
            except Exception:
                d["callable_agent_ids"] = []
            out.append(d)
        return out

    @classmethod
    async def delete(cls, agent_id: str) -> bool:
        db = get_database()
        await db.execute_query_async("DELETE FROM agents WHERE id = ?", (agent_id,))
        return True


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ai_model_config_id: Optional[str] = None
    mcp_config_ids: Optional[List[str]] = None
    callable_agent_ids: Optional[List[str]] = None
    system_context_id: Optional[str] = None
    enabled: Optional[bool] = None

    @classmethod
    async def update(cls, agent_id: str, data: "AgentUpdate") -> Optional[Dict[str, Any]]:
        db = get_database()
        fields = []
        values: List[Any] = []
        if data.name is not None:
            fields.append("name = ?")
            values.append(data.name)
        if data.description is not None:
            fields.append("description = ?")
            values.append(data.description)
        if data.ai_model_config_id is not None:
            fields.append("ai_model_config_id = ?")
            values.append(data.ai_model_config_id)
        if data.mcp_config_ids is not None:
            fields.append("mcp_config_ids = ?")
            values.append(json.dumps(data.mcp_config_ids))
        if data.callable_agent_ids is not None:
            fields.append("callable_agent_ids = ?")
            values.append(json.dumps(data.callable_agent_ids))
        if data.system_context_id is not None:
            fields.append("system_context_id = ?")
            values.append(data.system_context_id)
        if data.enabled is not None:
            fields.append("enabled = ?")
            values.append(data.enabled)
        if not fields:
            return await AgentCreate.get_by_id(agent_id)
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(agent_id)
        query = f"UPDATE agents SET {', '.join(fields)} WHERE id = ?"
        await db.execute_query_async(query, tuple(values))
        return await AgentCreate.get_by_id(agent_id)


# ========== 应用（Application）模型 ==========
class ApplicationCreate(BaseModel):
    name: str
    url: str
    icon_url: Optional[str] = None
    user_id: Optional[str] = None

    @classmethod
    async def create(cls, data: "ApplicationCreate") -> Dict[str, Any]:
        db = get_database()
        app_id = str(uuid.uuid4())
        query = (
            "INSERT INTO applications (id, name, url, icon_url, user_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)"
        )
        await db.execute_query_async(
            query,
            (app_id, data.name, data.url, data.icon_url, data.user_id),
        )
        return await ApplicationCreate.get_by_id(app_id)

    @classmethod
    async def get_by_id(cls, application_id: str) -> Optional[Dict[str, Any]]:
        db = get_database()
        row = await db.fetch_one_async(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,),
        )
        return row_to_dict(row) if row else None

    @classmethod
    async def get_all(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = get_database()
        if user_id and user_id.strip():
            rows = await db.fetch_all_async(
                "SELECT * FROM applications WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
        else:
            rows = await db.fetch_all_async(
                "SELECT * FROM applications ORDER BY created_at DESC"
            )
        return [row_to_dict(row) for row in rows if row]

    @classmethod
    async def delete(cls, application_id: str) -> bool:
        db = get_database()
        await db.execute_query_async(
            "DELETE FROM applications WHERE id = ?",
            (application_id,),
        )
        return True


class ApplicationUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    icon_url: Optional[str] = None

    @classmethod
    async def update(cls, application_id: str, data: "ApplicationUpdate") -> Optional[Dict[str, Any]]:
        db = get_database()
        fields = []
        values: List[Any] = []
        if data.name is not None:
            fields.append("name = ?")
            values.append(data.name)
        if data.url is not None:
            fields.append("url = ?")
            values.append(data.url)
        if data.icon_url is not None:
            fields.append("icon_url = ?")
            values.append(data.icon_url)
        if not fields:
            return await ApplicationCreate.get_by_id(application_id)
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(application_id)
        query = f"UPDATE applications SET {', '.join(fields)} WHERE id = ?"
        await db.execute_query_async(query, tuple(values))
        return await ApplicationCreate.get_by_id(application_id)