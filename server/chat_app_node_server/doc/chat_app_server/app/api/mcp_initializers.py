# MCP配置初始化器API路由（按需初始化，无导入时副作用）

import logging
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

logger = logging.getLogger(__name__)
router = APIRouter()


def _disabled(detail: str = "MCP 功能已移除"):
    """统一返回禁用提示"""
    raise HTTPException(status_code=410, detail=detail)


@router.post("/expert-stream/initialize", response_model=ConfigInitializerResponse)
async def initialize_expert_stream_config(request: ExpertStreamConfigRequest):
    """该功能已移除"""
    return _disabled("Expert Stream 配置初始化功能已移除")


@router.post("/file-reader/initialize", response_model=ConfigInitializerResponse)
async def initialize_file_reader_config(request: FileReaderConfigRequest):
    """该功能已移除"""
    return _disabled("File Reader 配置初始化功能已移除")


@router.get("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def get_expert_stream_config(alias: str):
    """该功能已移除"""
    return _disabled("Expert Stream 配置查询功能已移除")


@router.get("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def get_file_reader_config(alias: str):
    """该功能已移除"""
    return _disabled("File Reader 配置查询功能已移除")


@router.put("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def update_expert_stream_config(alias: str, request: ConfigUpdateRequest):
    """该功能已移除"""
    return _disabled("Expert Stream 配置更新功能已移除")


@router.put("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def update_file_reader_config(alias: str, request: ConfigUpdateRequest):
    """该功能已移除"""
    return _disabled("File Reader 配置更新功能已移除")


@router.get("/system-info")
async def get_system_info():
    """返回空的系统信息（MCP 功能已移除）"""
    return {
        "system_info": {},
        "available_servers": [],
        "current_config": {},
    }


@router.get("/list", response_model=ConfigListResponse)
async def list_all_configs():
    """返回空配置列表（MCP 功能已移除）"""
    return ConfigListResponse(configs=[], total=0)


@router.delete("/expert-stream/{alias}", response_model=ConfigInitializerResponse)
async def delete_expert_stream_config(alias: str):
    """该功能已移除"""
    return _disabled("Expert Stream 配置删除功能已移除")


@router.delete("/file-reader/{alias}", response_model=ConfigInitializerResponse)
async def delete_file_reader_config(alias: str):
    """该功能已移除"""
    return _disabled("File Reader 配置删除功能已移除")
