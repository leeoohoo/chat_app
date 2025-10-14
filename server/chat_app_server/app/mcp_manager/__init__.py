"""
MCP管理器包
用于管理MCP服务器的启动、配置和生命周期
"""

from .mcp_manager import McpManager
from .system_detector import SystemDetector
from .config_manager import ConfigManager

__all__ = ['McpManager', 'SystemDetector', 'ConfigManager']