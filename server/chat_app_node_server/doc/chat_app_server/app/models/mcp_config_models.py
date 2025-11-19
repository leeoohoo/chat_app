# MCP配置初始化器相关的数据模型

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class ConfigInitializerType(str, Enum):
    """配置初始化器类型"""
    EXPERT_STREAM = "expert_stream"
    FILE_READER = "file_reader"


class ExpertStreamConfigRequest(BaseModel):
    """Expert Stream 配置请求模型"""
    alias: str = Field(..., description="配置别名")
    config_template: Optional[Dict[str, Any]] = Field(None, description="配置模板")
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置")


class FileReaderConfigRequest(BaseModel):
    """File Reader 配置请求模型"""
    alias: str = Field(..., description="配置别名")
    project_root: str = Field(..., description="项目根目录路径")
    config_template: Optional[Dict[str, Any]] = Field(None, description="配置模板")
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置")


class ConfigInitializerResponse(BaseModel):
    """配置初始化器响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    config_path: Optional[str] = Field(None, description="配置文件路径")
    config_data: Optional[Dict[str, Any]] = Field(None, description="配置数据")


class ConfigListResponse(BaseModel):
    """配置列表响应模型"""
    configs: List[Dict[str, Any]] = Field(..., description="配置列表")
    total: int = Field(..., description="配置总数")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    alias: str = Field(..., description="配置别名")
    config_data: Dict[str, Any] = Field(..., description="新的配置数据")


class ConfigDeleteRequest(BaseModel):
    """配置删除请求模型"""
    alias: str = Field(..., description="要删除的配置别名")