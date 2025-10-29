"""
MCP 配置管理模块
提供不同类型MCP服务器的配置初始化和管理功能
"""

from .config_factory import ConfigInitializerFactory
from .expert_stream_config import ExpertStreamConfigInitializer
from .file_reader_config import FileReaderConfigInitializer
from .mcp_startup_manager import (
    MCPStartupManager,
    get_startup_manager,
    startup_initialize_mcp
)

__all__ = [
    "ConfigInitializerFactory",
    "ExpertStreamConfigInitializer", 
    "FileReaderConfigInitializer",
    "MCPStartupManager",
    "get_startup_manager",
    "startup_initialize_mcp"
]

__version__ = "1.0.0"