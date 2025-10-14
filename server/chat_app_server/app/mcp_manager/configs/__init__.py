"""
MCP Manager 配置模块
提供不同类型MCP服务器的配置初始化和管理功能
"""

from .config_factory import ConfigInitializerFactory
from .expert_stream_config import ExpertStreamConfigInitializer
from .file_reader_config import FileReaderConfigInitializer

__all__ = [
    "ConfigInitializerFactory",
    "ExpertStreamConfigInitializer", 
    "FileReaderConfigInitializer"
]

__version__ = "1.0.0"