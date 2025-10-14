# MCP配置初始化器API路由

import os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.models.mcp_config_models import (
    ExpertStreamConfigRequest,
    FileReaderConfigRequest,
    ConfigInitializerResponse,
    ConfigListResponse,
    ConfigUpdateRequest,
    ConfigDeleteRequest
)
from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer
from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer

logger = logging.getLogger(__name__)
router = APIRouter()

# 导入系统检测器
from app.mcp_manager.system_detector import SystemDetector

# 服务端配置目录路径
CONFIG_DIR = os.path.abspath(os.path.join(os.getcwd(), "mcp_config"))
MCP_SERVICES_DIR = os.path.abspath(os.path.join(os.getcwd(), "mcp_services"))

# 初始化系统检测器
system_detector = SystemDetector(MCP_SERVICES_DIR)

# 动态获取服务器脚本路径
EXPERT_STREAM_SERVER_SCRIPT = system_detector.get_server_executable_path("expert-stream-server")
FILE_READER_SERVER_SCRIPT = system_detector.get_server_executable_path("file-reader-server")

# 验证服务器路径
if not EXPERT_STREAM_SERVER_SCRIPT:
    logger.error("❌ 无法找到适合当前系统的 Expert Stream 服务器")
    raise RuntimeError("Expert Stream 服务器不可用")

if not FILE_READER_SERVER_SCRIPT:
    logger.error("❌ 无法找到适合当前系统的 File Reader 服务器")
    raise RuntimeError("File Reader 服务器不可用")

logger.info(f"✅ Expert Stream 服务器路径: {EXPERT_STREAM_SERVER_SCRIPT}")
logger.info(f"✅ File Reader 服务器路径: {FILE_READER_SERVER_SCRIPT}")


@router.post("/expert-stream/initialize", response_model=ConfigInitializerResponse)
async def initialize_expert_stream_config(request: ExpertStreamConfigRequest):
    """初始化 Expert Stream 配置"""
    try:
        initializer = ExpertStreamConfigInitializer(CONFIG_DIR, EXPERT_STREAM_SERVER_SCRIPT)
        
        # 调用初始化方法
        await initializer.initialize_config(
            alias=request.alias,
            config_template=request.config_template,
            custom_config=request.custom_config
        )
        
        # 获取配置数据
        config_data = await initializer.get_config(request.alias)
        
        return ConfigInitializerResponse(
            success=True,
            message=f"Expert Stream 配置 '{request.alias}' 初始化成功",
            config_path=str(Path(CONFIG_DIR) / f"expert_stream_server_alias_{request.alias}_server_config.json"),
            config_data=config_data
        )
        
    except Exception as e:
        logger.error(f"初始化 Expert Stream 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化配置失败: {str(e)}")


@router.post("/file-reader/initialize", response_model=ConfigInitializerResponse)
async def initialize_file_reader_config(request: FileReaderConfigRequest):
    """初始化 File Reader 配置"""
    try:
        initializer = FileReaderConfigInitializer(CONFIG_DIR, FILE_READER_SERVER_SCRIPT)
        
        # 调用初始化方法
        await initializer.initialize_config(
            alias=request.alias,
            config_template=request.config_template,
            project_root=None,  # 使用默认值
            custom_config=request.custom_config
        )
        
        # 获取配置数据
        config_data = await initializer.get_config(request.alias)
        
        return ConfigInitializerResponse(
            success=True,
            message=f"File Reader 配置 '{request.alias}' 初始化成功",
            config_path=str(Path(CONFIG_DIR) / f"File Reader MCP Server_alias_{request.alias}_server_config.json"),
            config_data=config_data
        )
        
    except Exception as e:
        logger.error(f"初始化 File Reader 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化配置失败: {str(e)}")


@router.get("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def get_expert_stream_config(alias: str):
    """获取 Expert Stream 配置"""
    try:
        initializer = ExpertStreamConfigInitializer(CONFIG_DIR, EXPERT_STREAM_SERVER_SCRIPT)
        config_data = await initializer.get_config(alias)
        
        if not config_data:
            raise HTTPException(status_code=404, detail=f"配置 '{alias}' 不存在")
        
        return ConfigInitializerResponse(
            success=True,
            message=f"获取 Expert Stream 配置 '{alias}' 成功",
            config_path=str(Path(CONFIG_DIR) / f"expert_stream_server_alias_{alias}_server_config.json"),
            config_data=config_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Expert Stream 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.get("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def get_file_reader_config(alias: str):
    """获取 File Reader 配置"""
    try:
        initializer = FileReaderConfigInitializer(CONFIG_DIR, FILE_READER_SERVER_SCRIPT)
        config_data = await initializer.get_config(alias)
        
        if not config_data:
            raise HTTPException(status_code=404, detail=f"配置 '{alias}' 不存在")
        
        return ConfigInitializerResponse(
            success=True,
            message=f"获取 File Reader 配置 '{alias}' 成功",
            config_path=str(Path(CONFIG_DIR) / f"File Reader MCP Server_alias_{alias}_server_config.json"),
            config_data=config_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 File Reader 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def update_expert_stream_config(alias: str, request: ConfigUpdateRequest):
    """更新 Expert Stream 配置"""
    try:
        initializer = ExpertStreamConfigInitializer(CONFIG_DIR, EXPERT_STREAM_SERVER_SCRIPT)
        
        # 更新配置
        await initializer.update_config(alias, request.config_data)
        
        # 获取更新后的配置数据
        config_data = await initializer.get_config(alias)
        
        return ConfigInitializerResponse(
            success=True,
            message=f"Expert Stream 配置 '{alias}' 更新成功",
            config_path=str(Path(CONFIG_DIR) / f"expert_stream_server_alias_{alias}_server_config.json"),
            config_data=config_data
        )
        
    except Exception as e:
        logger.error(f"更新 Expert Stream 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.put("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def update_file_reader_config(alias: str, request: ConfigUpdateRequest):
    """更新 File Reader 配置"""
    try:
        initializer = FileReaderConfigInitializer(CONFIG_DIR, FILE_READER_SERVER_SCRIPT)
        
        # 更新配置
        await initializer.update_config(alias, request.config_data)
        
        # 获取更新后的配置数据
        config_data = await initializer.get_config(alias)
        
        return ConfigInitializerResponse(
            success=True,
            message=f"File Reader 配置 '{alias}' 更新成功",
            config_path=str(Path(CONFIG_DIR) / f"File Reader MCP Server_alias_{alias}_server_config.json"),
            config_data=config_data
        )
        
    except Exception as e:
        logger.error(f"更新 File Reader 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/system-info")
async def get_system_info():
    """获取系统信息和可用服务器"""
    try:
        system_info = system_detector.get_system_info()
        available_servers = system_detector.get_available_servers()
        
        return {
            "system_info": system_info,
            "available_servers": available_servers,
            "current_config": {
                "expert_stream_server": EXPERT_STREAM_SERVER_SCRIPT,
                "file_reader_server": FILE_READER_SERVER_SCRIPT
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.get("/list", response_model=ConfigListResponse)
async def list_all_configs():
    """列出所有配置"""
    try:
        config_dir = Path(CONFIG_DIR)
        configs = []
        
        if config_dir.exists():
            # 查找所有配置文件
            for config_file in config_dir.glob("*.json"):
                try:
                    import json
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    configs.append({
                        "file_name": config_file.name,
                        "file_path": str(config_file),
                        "alias": config_data.get("alias", "unknown"),
                        "server_name": config_data.get("server_name", "unknown"),
                        "type": "expert_stream" if "expert_stream" in config_file.name else "file_reader"
                    })
                except Exception as e:
                    logger.warning(f"读取配置文件 {config_file} 失败: {e}")
                    continue
        
        return ConfigListResponse(
            configs=configs,
            total=len(configs)
        )
        
    except Exception as e:
        logger.error(f"列出配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出配置失败: {str(e)}")


@router.delete("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def delete_expert_stream_config(alias: str):
    """删除 Expert Stream 配置"""
    try:
        config_file = Path(CONFIG_DIR) / f"expert_stream_server_alias_{alias}_server_config.json"
        
        if not config_file.exists():
            raise HTTPException(status_code=404, detail=f"配置 '{alias}' 不存在")
        
        config_file.unlink()
        
        return ConfigInitializerResponse(
            success=True,
            message=f"Expert Stream 配置 '{alias}' 删除成功",
            config_path=str(config_file)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 Expert Stream 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


@router.delete("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def delete_file_reader_config(alias: str):
    """删除 File Reader 配置"""
    try:
        config_file = Path(CONFIG_DIR) / f"File Reader MCP Server_alias_{alias}_server_config.json"
        
        if not config_file.exists():
            raise HTTPException(status_code=404, detail=f"配置 '{alias}' 不存在")
        
        config_file.unlink()
        
        return ConfigInitializerResponse(
            success=True,
            message=f"File Reader 配置 '{alias}' 删除成功",
            config_path=str(config_file)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 File Reader 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")