# MCP配置初始化器API路由（按需初始化，无导入时副作用）

import logging
from pathlib import Path
from functools import lru_cache
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
from app.mcp_manager.system_detector import SystemDetector

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache(maxsize=1)
def _get_mcp_context() -> Dict[str, Any]:
    """按需构建并缓存 MCP 相关上下文。
    返回包含项目根目录、配置目录、服务目录、系统检测器以及各服务器脚本路径。
    """
    project_root = Path(__file__).parent.parent.parent.absolute()
    config_dir_path = project_root / "mcp_config"
    services_dir_path = project_root / "mcp_services"

    # 仅在需要时创建目录
    config_dir_path.mkdir(parents=True, exist_ok=True)
    services_dir_path.mkdir(parents=True, exist_ok=True)

    detector = SystemDetector(str(services_dir_path))
    expert_script = detector.get_server_executable_path("expert-stream-server")
    file_reader_script = detector.get_server_executable_path("file-reader-server")

    # 记录基础信息（不抛异常，路由内按需校验）
    logger.info(f"📁 项目根目录: {project_root}")
    logger.info(f"📁 配置目录: {config_dir_path}")
    logger.info(f"📁 MCP服务目录: {services_dir_path}")

    return {
        "project_root": project_root,
        "config_dir": str(config_dir_path),
        "services_dir": str(services_dir_path),
        "detector": detector,
        "expert_script": expert_script,
        "file_reader_script": file_reader_script,
    }


@router.post("/expert-stream/initialize", response_model=ConfigInitializerResponse)
async def initialize_expert_stream_config(request: ExpertStreamConfigRequest):
    """初始化 Expert Stream 配置"""
    try:
        ctx = _get_mcp_context()
        if not ctx["expert_script"]:
            raise HTTPException(status_code=500, detail="Expert Stream 服务器不可用")

        initializer = ExpertStreamConfigInitializer(ctx["config_dir"], ctx["expert_script"])

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
            config_path=str(Path(ctx["config_dir"]) / f"expert_stream_server_alias_{request.alias}_server_config.json"),
            config_data=config_data
        )

    except Exception as e:
        logger.error(f"初始化 Expert Stream 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化配置失败: {str(e)}")


@router.post("/file-reader/initialize", response_model=ConfigInitializerResponse)
async def initialize_file_reader_config(request: FileReaderConfigRequest):
    """初始化 File Reader 配置"""
    try:
        ctx = _get_mcp_context()
        if not ctx["file_reader_script"]:
            raise HTTPException(status_code=500, detail="File Reader 服务器不可用")

        initializer = FileReaderConfigInitializer(ctx["config_dir"], ctx["file_reader_script"])

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
            config_path=str(Path(ctx["config_dir"]) / f"File Reader MCP Server_alias_{request.alias}_server_config.json"),
            config_data=config_data
        )

    except Exception as e:
        logger.error(f"初始化 File Reader 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化配置失败: {str(e)}")


@router.get("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def get_expert_stream_config(alias: str):
    """获取 Expert Stream 配置"""
    try:
        ctx = _get_mcp_context()
        if not ctx["expert_script"]:
            raise HTTPException(status_code=500, detail="Expert Stream 服务器不可用")
        initializer = ExpertStreamConfigInitializer(ctx["config_dir"], ctx["expert_script"])
        config_data = await initializer.get_config(alias)

        if not config_data:
            raise HTTPException(status_code=404, detail=f"配置 '{alias}' 不存在")

        return ConfigInitializerResponse(
            success=True,
            message=f"获取 Expert Stream 配置 '{alias}' 成功",
            config_path=str(Path(ctx["config_dir"]) / f"expert_stream_server_alias_{alias}_server_config.json"),
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
        ctx = _get_mcp_context()
        if not ctx["file_reader_script"]:
            raise HTTPException(status_code=500, detail="File Reader 服务器不可用")
        initializer = FileReaderConfigInitializer(ctx["config_dir"], ctx["file_reader_script"])
        config_data = await initializer.get_config(alias)

        if not config_data:
            raise HTTPException(status_code=404, detail=f"配置 '{alias}' 不存在")

        return ConfigInitializerResponse(
            success=True,
            message=f"获取 File Reader 配置 '{alias}' 成功",
            config_path=str(Path(ctx["config_dir"]) / f"File Reader MCP Server_alias_{alias}_server_config.json"),
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
        ctx = _get_mcp_context()
        if not ctx["expert_script"]:
            raise HTTPException(status_code=500, detail="Expert Stream 服务器不可用")
        initializer = ExpertStreamConfigInitializer(ctx["config_dir"], ctx["expert_script"])

        # 更新配置
        await initializer.update_config(alias, request.config_data)

        # 获取更新后的配置数据
        config_data = await initializer.get_config(alias)

        return ConfigInitializerResponse(
            success=True,
            message=f"Expert Stream 配置 '{alias}' 更新成功",
            config_path=str(Path(ctx["config_dir"]) / f"expert_stream_server_alias_{alias}_server_config.json"),
            config_data=config_data
        )

    except Exception as e:
        logger.error(f"更新 Expert Stream 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.put("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def update_file_reader_config(alias: str, request: ConfigUpdateRequest):
    """更新 File Reader 配置"""
    try:
        ctx = _get_mcp_context()
        if not ctx["file_reader_script"]:
            raise HTTPException(status_code=500, detail="File Reader 服务器不可用")
        initializer = FileReaderConfigInitializer(ctx["config_dir"], ctx["file_reader_script"])

        # 更新配置
        await initializer.update_config(alias, request.config_data)

        # 获取更新后的配置数据
        config_data = await initializer.get_config(alias)

        return ConfigInitializerResponse(
            success=True,
            message=f"File Reader 配置 '{alias}' 更新成功",
            config_path=str(Path(ctx["config_dir"]) / f"File Reader MCP Server_alias_{alias}_server_config.json"),
            config_data=config_data
        )

    except Exception as e:
        logger.error(f"更新 File Reader 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/system-info")
async def get_system_info():
    """获取系统信息和可用服务器"""
    try:
        ctx = _get_mcp_context()
        system_info = ctx["detector"].get_system_info()
        available_servers = ctx["detector"].get_available_servers()

        return {
            "system_info": system_info,
            "available_servers": available_servers,
            "current_config": {
                "expert_stream_server": ctx["expert_script"],
                "file_reader_server": ctx["file_reader_script"],
            },
        }

    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.get("/list", response_model=ConfigListResponse)
async def list_all_configs():
    """列出所有配置"""
    try:
        ctx = _get_mcp_context()
        config_dir = Path(ctx["config_dir"])
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
        ctx = _get_mcp_context()
        config_file = Path(ctx["config_dir"]) / f"expert_stream_server_alias_{alias}_server_config.json"

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
        ctx = _get_mcp_context()
        config_file = Path(ctx["config_dir"]) / f"File Reader MCP Server_alias_{alias}_server_config.json"

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
