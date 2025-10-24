"""
V2版本的AI服务模块
提供完整的聊天服务功能，包括消息管理、AI请求处理、工具执行等
"""

from .message_manager import MessageManager
from .ai_request_handler import AiRequestHandler
from .tool_result_processor import ToolResultProcessor
from .mcp_tool_execute import McpToolExecute
from .ai_client import AiClient
from .ai_server import AiServer
from .chat_service import ChatService

__all__ = [
    'MessageManager',
    'AiRequestHandler', 
    'ToolResultProcessor',
    'McpToolExecute',
    'AiClient',
    'AiServer',
    'ChatService'
]

__version__ = '2.0.0'