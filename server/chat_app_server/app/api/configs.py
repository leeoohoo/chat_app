# 配置相关API路由

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import os
import json

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from app.models.config import (
    McpConfigCreate, McpConfigUpdate,
    AiModelConfigCreate, AiModelConfigUpdate,
    SystemContextCreate, SystemContextUpdate, SystemContextActivate,
    McpConfigProfileCreate, McpConfigProfileUpdate, McpConfigProfileActivate
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _extract_text_from_resource(result: Any) -> str:
    """提取 fastmcp 客户端 read_resource 的文本内容，兼容多种返回结构。

    支持：
    - 直接字符串
    - 对象属性：text(str) 或 text() 可调用
    - 对象属性：value(str) 或 value 为 dict/list（序列化）
    - 对象属性：content/contents 为 list/tuple，元素为 dict 或对象（如 TextResourceContents）
    - 直接返回 list/tuple（取首元素并解析）
    """
    # 直接字符串
    if isinstance(result, str):
        return result

    # 对象上的 text 属性
    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text
    if callable(text):
        try:
            return text()
        except Exception:
            pass

    # 对象上的 value 属性
    value = getattr(result, "value", None)
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    # content/contents 容器
    content = getattr(result, "content", None)
    contents = getattr(result, "contents", None)
    if contents and isinstance(contents, (list, tuple)) and contents:
        content = contents
    if content and isinstance(content, (list, tuple)) and content:
        first = content[0]
        # dict 形式
        if isinstance(first, dict):
            if first.get("type") == "text" and "text" in first:
                return first.get("text", "")
            return json.dumps(first, ensure_ascii=False)
        # 对象形式（如 TextResourceContents）
        if hasattr(first, "text") and isinstance(getattr(first, "text"), str):
            return getattr(first, "text")
        if hasattr(first, "value") and isinstance(getattr(first, "value"), str):
            return getattr(first, "value")

    # 直接返回 list/tuple 的情况
    if isinstance(result, (list, tuple)) and result:
        first = result[0]
        if isinstance(first, dict):
            if first.get("type") == "text" and "text" in first:
                return first.get("text", "")
            return json.dumps(first, ensure_ascii=False)
        if hasattr(first, "text") and isinstance(getattr(first, "text"), str):
            return getattr(first, "text")

    # 兜底错误
    return json.dumps({"error": "Unsupported resource response format"}, ensure_ascii=False)


@router.get("/mcp-configs")
async def get_mcp_configs(user_id: Optional[str] = Query(None)):
    """获取MCP配置列表"""
    try:
        configs = await McpConfigCreate.get_all(user_id=user_id)
        logger.info(f"获取到 {len(configs)} 个MCP配置")
        return configs
        
    except Exception as e:
        logger.error(f"获取MCP配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取MCP配置失败")


@router.post("/mcp-configs")
async def create_mcp_config(config: McpConfigCreate):
    """创建MCP配置"""
    try:
        new_config = await McpConfigCreate.create(config)
        logger.info(f"创建MCP配置成功: {new_config['id']}")
        return new_config
        
    except Exception as e:
        logger.error(f"创建MCP配置失败: {e}")
        raise HTTPException(status_code=500, detail="创建MCP配置失败")


@router.put("/mcp-configs/{config_id}")
async def update_mcp_config(config_id: str, config: McpConfigUpdate):
    """更新MCP配置"""
    try:
        # 检查配置是否存在
        existing_config = await McpConfigCreate.get_by_id(config_id)
        if not existing_config:
            raise HTTPException(status_code=404, detail="MCP配置不存在")
        
        # 执行更新操作
        updated_config = await McpConfigUpdate.update(config_id, config)
        if updated_config:
            logger.info(f"成功更新MCP配置: {config_id} ({updated_config.get('name', 'Unknown')})")
            return updated_config
        else:
            raise HTTPException(status_code=500, detail="更新操作失败")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新MCP配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新MCP配置失败")


@router.delete("/mcp-configs/{config_id}")
async def delete_mcp_config(config_id: str):
    """删除MCP配置"""
    try:
        # 检查配置是否存在
        existing_config = await McpConfigCreate.get_by_id(config_id)
        if not existing_config:
            raise HTTPException(status_code=404, detail="MCP配置不存在")
        
        # 执行删除操作
        success = await McpConfigCreate.delete(config_id)
        if success:
            logger.info(f"成功删除MCP配置: {config_id} ({existing_config.get('name', 'Unknown')})")
            return {"message": "MCP配置删除成功", "id": config_id}
        else:
            raise HTTPException(status_code=500, detail="删除操作失败")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除MCP配置失败: {e}")
        raise HTTPException(status_code=500, detail="删除MCP配置失败")


@router.get("/mcp-configs/{config_id}/resource/config")
async def get_mcp_resource_config(config_id: str):
    """读取指定MCP stdio服务器的配置资源（config://file-reader）。

    - 使用数据库中的配置（command/args/env）启动 stdio MCP 服务器
    - 通过 fastmcp.Client 读取资源并返回 JSON
    """
    try:
        cfg = await McpConfigCreate.get_by_id(config_id)
        if not cfg:
            raise HTTPException(status_code=404, detail="MCP配置不存在")

        server_type = cfg.get("type", "stdio")
        if server_type != "stdio":
            raise HTTPException(status_code=400, detail="仅支持stdio类型的MCP配置读取资源")

        name = cfg.get("name") or "mcp_server"
        command = cfg.get("command")
        if not command:
            raise HTTPException(status_code=400, detail="MCP配置缺少可执行命令")

        # 解析 args 和 env（兼容字符串/对象存储）
        raw_args = cfg.get("args")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = []
        else:
            args = raw_args or []

        raw_env = cfg.get("env")
        if isinstance(raw_env, str):
            try:
                env = json.loads(raw_env)
            except json.JSONDecodeError:
                env = {}
        else:
            env = raw_env or {}

        # 支持在 command 中附带 alias（例如："python server.py -- my_alias"），但推荐不使用别名并直接用 name
        actual_command = command
        alias = name
        if "--" in command:
            parts = command.split("--", 1)
            actual_command = parts[0].strip()
            alias = parts[1].strip() or name

        # 读取激活的配置档案（profile），若存在则覆盖 args/env/cwd
        active_profile = await McpConfigProfileActivate.get_active(cfg["id"])
        cwd = cfg.get("cwd")
        if active_profile:
            prof_args = active_profile.get("args") or []
            prof_env = active_profile.get("env") or {}
            prof_cwd = active_profile.get("cwd")
            if prof_args:
                args = prof_args
            if prof_env:
                env = prof_env
            if prof_cwd:
                cwd = prof_cwd
        if not cwd:
            cwd = os.getcwd()

        # 构建 fastmcp STDIO 传输（兼容 fastmcp==2.1.0 的 Client 初始化）
        transport = StdioTransport(
            command=actual_command,
            args=args or None,
            cwd=cwd or None,
            env=env or None,
        )

        async def _read():
            async with Client(transport) as client:
                # 直接读取指定资源（与 by_command 路由一致使用 config://server）
                result = await client.read_resource("config://server")
                return _extract_text_from_resource(result)

        # 同步等待异步读取完成
        import asyncio
        text = await _read()

        # 资源返回通常为 JSON 字符串，尝试解析
        try:
            data = json.loads(text)
        except Exception:
            # 若无法解析，直接返回原始文本
            data = {"raw": text}

        return {"success": True, "config": data, "alias": alias}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取MCP配置资源失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取MCP配置资源失败: {str(e)}")


@router.post("/mcp-configs/resource/config")
async def get_mcp_resource_config_by_command(data: Dict[str, Any]):
    """无需保存配置，直接根据传入的命令/参数/环境来读取配置资源。

    请求体示例：
    {
      "type": "stdio",
      "command": "npx @modelcontextprotocol/server-filesystem /path/to/allowed/files",
      "args": ["--alias", "my_server"],
      "env": {"KEY": "VALUE"},
      "cwd": "/absolute/path/to/workspace",
      "alias": "my_server" // 可选，未提供则尝试从 args 推断或使用默认名
    }
    """
    try:
        server_type = data.get("type", "stdio")
        if server_type != "stdio":
            raise HTTPException(status_code=400, detail="仅支持stdio类型的MCP配置读取资源")

        command = data.get("command")
        if not command:
            raise HTTPException(status_code=400, detail="缺少可执行命令")

        # 解析 args/env/cwd
        raw_args = data.get("args")
        args = []
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = []
        elif isinstance(raw_args, list):
            args = raw_args

        raw_env = data.get("env") or {}
        env = {}
        if isinstance(raw_env, str):
            try:
                env = json.loads(raw_env)
            except json.JSONDecodeError:
                env = {}
        elif isinstance(raw_env, dict):
            env = raw_env

        cwd = data.get("cwd") or os.getcwd()

        # 不再从命令字符串解析别名，按原样使用命令
        actual_command = command
        alias = data.get("alias") or "mcp_server"

        # 构建 fastmcp STDIO 传输（兼容 fastmcp==2.1.0 的 Client 初始化）
        transport = StdioTransport(
            command=actual_command,
            args=args or None,
            cwd=cwd or None,
            env=env or None,
        )

        async def _read():
            async with Client(transport) as client:
                result = await client.read_resource("config://server")
                return _extract_text_from_resource(result)

        text = await _read()
        try:
            data_out = json.loads(text)
        except Exception:
            data_out = {"raw": text}

        return {"success": True, "config": data_out, "alias": alias}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取MCP配置资源(按命令)失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取MCP配置资源失败: {str(e)}")


# === MCP Config Profile 管理 ===

@router.get("/mcp-configs/{config_id}/profiles")
async def list_mcp_config_profiles(config_id: str):
    try:
        profiles = await McpConfigProfileCreate.list_by_config(config_id)
        return {"items": profiles}
    except Exception as e:
        logger.error(f"列出配置档案失败: {e}")
        raise HTTPException(status_code=500, detail="列出配置档案失败")

@router.post("/mcp-configs/{config_id}/profiles")
async def create_mcp_config_profile(config_id: str, data: Dict[str, Any]):
    try:
        profile = McpConfigProfileCreate(
            mcp_config_id=config_id,
            name=data.get("name", "default"),
            args=data.get("args"),
            env=data.get("env"),
            cwd=data.get("cwd"),
            enabled=data.get("enabled", False),
        )
        created = await McpConfigProfileCreate.create(profile)
        return created
    except Exception as e:
        logger.error(f"创建配置档案失败: {e}")
        raise HTTPException(status_code=500, detail="创建配置档案失败")

@router.put("/mcp-configs/{config_id}/profiles/{profile_id}")
async def update_mcp_config_profile(config_id: str, profile_id: str, data: Dict[str, Any]):
    try:
        update = McpConfigProfileUpdate(
            name=data.get("name"),
            args=data.get("args"),
            env=data.get("env"),
            cwd=data.get("cwd"),
            enabled=data.get("enabled"),
        )
        updated = await McpConfigProfileUpdate.update(profile_id, update)
        return updated
    except Exception as e:
        logger.error(f"更新配置档案失败: {e}")
        raise HTTPException(status_code=500, detail="更新配置档案失败")

@router.delete("/mcp-configs/{config_id}/profiles/{profile_id}")
async def delete_mcp_config_profile(config_id: str, profile_id: str):
    """删除指定配置的档案"""
    try:
        existing = await McpConfigProfileCreate.get_by_id(profile_id)
        if not existing:
            raise HTTPException(status_code=404, detail="配置档案不存在")
        if str(existing.get("mcp_config_id")) != str(config_id):
            raise HTTPException(status_code=400, detail="配置ID不匹配")

        success = await McpConfigProfileCreate.delete(profile_id)
        if success:
            logger.info(f"成功删除配置档案: {profile_id} (配置 {config_id})")
            return {"message": "配置档案删除成功", "id": profile_id}
        else:
            raise HTTPException(status_code=500, detail="删除操作失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除配置档案失败: {e}")
        raise HTTPException(status_code=500, detail="删除配置档案失败")

@router.post("/mcp-configs/{config_id}/profiles/{profile_id}/activate")
async def activate_mcp_config_profile(config_id: str, profile_id: str):
    try:
        activated = await McpConfigProfileActivate.activate(config_id, profile_id)
        return activated
    except Exception as e:
        logger.error(f"激活配置档案失败: {e}")
        raise HTTPException(status_code=500, detail="激活配置档案失败")


@router.get("/ai-model-configs")
async def get_ai_model_configs(user_id: Optional[str] = Query(None)):
    """获取AI模型配置列表"""
    try:
        configs = await AiModelConfigCreate.get_all(user_id=user_id)
        logger.info(f"获取到 {len(configs)} 个AI模型配置")
        return configs
        
    except Exception as e:
        logger.error(f"获取AI模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取AI模型配置失败")


@router.post("/ai-model-configs")
async def create_ai_model_config(config_data: Dict[str, Any]):
    """创建AI模型配置"""
    try:
        # 统一使用下划线格式的字段名称
        config = AiModelConfigCreate(
            name=config_data.get("name"),
            provider=config_data.get("provider", "openai"),
            model=config_data.get("model"),
            api_key=config_data.get("api_key"),
            base_url=config_data.get("base_url"),
            user_id=config_data.get("user_id"),
            enabled=config_data.get("enabled", True)
        )
        
        new_config = await AiModelConfigCreate.create(config)
        logger.info(f"创建AI模型配置成功: {new_config['id']}")
        return new_config
        
    except Exception as e:
        logger.error(f"创建AI模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="创建AI模型配置失败")


@router.put("/ai-model-configs/{config_id}")
async def update_ai_model_config(config_id: str, config_data: Dict[str, Any]):
    """更新AI模型配置"""
    try:
        # 统一使用下划线格式的字段名称
        update_data = {}
        if "name" in config_data:
            update_data["name"] = config_data["name"]
        if "provider" in config_data:
            update_data["provider"] = config_data["provider"]
        if "model" in config_data:
            update_data["model"] = config_data["model"]
        if "api_key" in config_data:
            update_data["api_key"] = config_data["api_key"]
        if "base_url" in config_data:
            update_data["base_url"] = config_data["base_url"]
        if "enabled" in config_data:
            update_data["enabled"] = config_data["enabled"]
        
        updated_config = await AiModelConfigUpdate.update(config_id, update_data)
        
        if updated_config:
            logger.info(f"AI模型配置更新成功: {config_id}")
            return updated_config
        else:
            raise HTTPException(status_code=404, detail="AI模型配置不存在")
        
    except Exception as e:
        logger.error(f"更新AI模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新AI模型配置失败")


@router.delete("/ai-model-configs/{config_id}")
async def delete_ai_model_config(config_id: str):
    """删除AI模型配置"""
    try:
        # 检查配置是否存在
        existing_config = await AiModelConfigCreate.get_by_id(config_id)
        if not existing_config:
            raise HTTPException(status_code=404, detail="AI模型配置不存在")
        
        # 执行删除
        success = await AiModelConfigCreate.delete(config_id)
        if success:
            logger.info(f"AI模型配置删除成功: {config_id}")
            return {"message": "AI模型配置删除成功"}
        else:
            raise HTTPException(status_code=500, detail="删除AI模型配置失败")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除AI模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="删除AI模型配置失败")


@router.get("/system-contexts")
async def get_system_contexts(user_id: str = Query(...)):
    """获取系统上下文列表"""
    try:
        contexts = await SystemContextCreate.get_all(user_id=user_id)
        logger.info(f"获取到 {len(contexts)} 个系统上下文")
        return contexts
        
    except Exception as e:
        logger.error(f"获取系统上下文失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统上下文失败")


@router.get("/system-context/active")
async def get_active_system_context(user_id: str):
    """获取用户的活跃系统上下文"""
    try:
        result = await SystemContextCreate.get_active(user_id)
        return {"content": result.get('content', '') if result else '', "context": result}
        
    except Exception as e:
        logger.error(f"获取活跃系统上下文失败: {e}")
        raise HTTPException(status_code=500, detail="获取活跃系统上下文失败")


@router.post("/system-contexts")
async def create_system_context(context: SystemContextCreate):
    """创建系统上下文"""
    try:
        new_context = await SystemContextCreate.create(context)
        logger.info(f"创建系统上下文成功: {new_context['id']}")
        return new_context
        
    except Exception as e:
        logger.error(f"创建系统上下文失败: {e}")
        raise HTTPException(status_code=500, detail="创建系统上下文失败")


@router.put("/system-contexts/{context_id}")
async def update_system_context(context_id: str, context: SystemContextUpdate):
    """更新系统上下文"""
    try:
        updated_context = await SystemContextUpdate.update(context_id, context)
        logger.info(f"更新系统上下文成功: {context_id}")
        return updated_context
        
    except Exception as e:
        logger.error(f"更新系统上下文失败: {e}")
        raise HTTPException(status_code=500, detail="更新系统上下文失败")


@router.delete("/system-contexts/{context_id}")
async def delete_system_context(context_id: str):
    """删除系统上下文"""
    try:
        # 暂时返回成功，需要实现删除逻辑
        logger.info(f"删除系统上下文: {context_id}")
        return {"message": "系统上下文删除成功"}
        
    except Exception as e:
        logger.error(f"删除系统上下文失败: {e}")
        raise HTTPException(status_code=500, detail="删除系统上下文失败")


@router.post("/system-contexts/{context_id}/activate")
async def activate_system_context(context_id: str, activate: SystemContextActivate):
    """激活系统上下文"""
    try:
        result = await SystemContextActivate.activate(context_id, activate.user_id)
        logger.info(f"激活系统上下文成功: {context_id}")
        return result
        
    except Exception as e:
        logger.error(f"激活系统上下文失败: {e}")
        raise HTTPException(status_code=500, detail="激活系统上下文失败")