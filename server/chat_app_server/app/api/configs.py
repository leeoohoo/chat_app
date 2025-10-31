# 配置相关API路由

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from app.models.config import (
    McpConfigCreate, McpConfigUpdate,
    AiModelConfigCreate, AiModelConfigUpdate,
    SystemContextCreate, SystemContextUpdate, SystemContextActivate
)
from app.models import db

logger = logging.getLogger(__name__)
router = APIRouter()


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