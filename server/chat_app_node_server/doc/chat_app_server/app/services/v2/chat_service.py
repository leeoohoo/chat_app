"""
聊天服务管理器
提供高级的聊天服务接口，管理多个AI服务器实例
"""
import time
from typing import Dict, List, Any, Optional, Callable

from .ai_server import AiServer
from ...models.message import MessageCreate
from ...models.session import SessionCreate


class ChatService:
    """聊天服务管理器"""
    
    def __init__(self, 
                 openai_api_key: str,
                 mcp_client,
                 default_model: str = "gpt-4",
                 default_temperature: float = 0.7):
        """
        初始化聊天服务
        
        Args:
            openai_api_key: OpenAI API密钥
            mcp_client: MCP客户端
            default_model: 默认模型
            default_temperature: 默认温度
        """
        self.ai_server = AiServer(
            openai_api_key=openai_api_key,
            mcp_client=mcp_client,
            default_model=default_model,
            default_temperature=default_temperature
        )
        
        # 服务统计
        self.service_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "start_time": int(time.time() * 1000)
        }
    
    def send_message(self, 
                    session_id: str,
                    message: str,
                    options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送消息
        
        Args:
            session_id: 会话ID
            message: 用户消息
            options: 可选配置
            
        Returns:
            响应结果
        """
        try:
            self.service_stats["total_requests"] += 1
            
            # 解析选项
            options = options or {}
            model = options.get("model")
            temperature = options.get("temperature")
            max_tokens = options.get("max_tokens")
            use_tools = options.get("use_tools", True)
            
            # 处理聊天
            result = self.ai_server.chat(
                session_id=session_id,
                user_message=message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                use_tools=use_tools
            )
            
            if result.get("success"):
                self.service_stats["successful_requests"] += 1
            else:
                self.service_stats["failed_requests"] += 1
            
            return result
            
        except Exception as e:
            self.service_stats["failed_requests"] += 1
            error_message = f"发送消息失败: {str(e)}"
            print(f"Error in send_message: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def send_message_stream(self, 
                           session_id: str,
                           message: str,
                           options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送流式消息
        
        Args:
            session_id: 会话ID
            message: 用户消息
            options: 可选配置
            
        Returns:
            流式响应结果
        """
        try:
            self.service_stats["total_requests"] += 1
            
            # 解析选项
            options = options or {}
            model = options.get("model")
            temperature = options.get("temperature")
            max_tokens = options.get("max_tokens")
            use_tools = options.get("use_tools", True)
            
            # 处理流式聊天
            result = self.ai_server.stream_chat(
                session_id=session_id,
                user_message=message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                use_tools=use_tools
            )
            
            if result.get("success"):
                self.service_stats["successful_requests"] += 1
            else:
                self.service_stats["failed_requests"] += 1
            
            return result
            
        except Exception as e:
            self.service_stats["failed_requests"] += 1
            error_message = f"发送流式消息失败: {str(e)}"
            print(f"Error in send_message_stream: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_conversation_history(self, 
                               session_id: str,
                               limit: int = 50,
                               offset: int = 0) -> Dict[str, Any]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            limit: 消息数量限制
            offset: 偏移量
            
        Returns:
            会话历史
        """
        try:
            # 这里应该从数据库获取消息历史
            # 暂时返回空列表，实际实现需要调用数据库服务
            messages = []
            
            return {
                "success": True,
                "messages": messages,
                "total_count": len(messages),
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            error_message = f"获取会话历史失败: {str(e)}"
            print(f"Error in get_conversation_history: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def create_session(self, 
                      session_id: Optional[str] = None,
                      config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            session_id: 指定的会话ID，如果为None则自动生成
            config: 会话配置
            
        Returns:
            创建结果
        """
        try:
            # 生成会话ID（如果未提供）
            if not session_id:
                session_id = f"session_{int(time.time() * 1000)}"
            
            # 设置会话配置
            if config:
                self.ai_server.update_session_config(session_id, config)
            
            return {
                "success": True,
                "session_id": session_id,
                "created_at": int(time.time() * 1000)
            }
            
        except Exception as e:
            error_message = f"创建会话失败: {str(e)}"
            print(f"Error in create_session: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            删除结果
        """
        try:
            # 重置会话（清除配置和缓存）
            reset_result = self.ai_server.reset_session(session_id)
            
            # 从数据库删除会话消息
            messages_deleted = MessageCreate.delete_by_session_sync(session_id)
            
            # 从数据库删除会话记录
            session_deleted = SessionCreate.delete_sync(session_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "messages_deleted": messages_deleted,
                "session_deleted": session_deleted,
                "reset_result": reset_result,
                "deleted_at": int(time.time() * 1000)
            }
            
        except Exception as e:
            error_message = f"删除会话失败: {str(e)}"
            print(f"Error in delete_session: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def update_session_config(self, 
                            session_id: str,
                            config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新会话配置
        
        Args:
            session_id: 会话ID
            config: 新配置
            
        Returns:
            更新结果
        """
        try:
            self.ai_server.update_session_config(session_id, config)
            
            return {
                "success": True,
                "message": "会话配置已更新",
                "session_id": session_id
            }
            
        except Exception as e:
            error_message = f"更新会话配置失败: {str(e)}"
            print(f"Error in update_session_config: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_session_config(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话配置
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话配置
        """
        try:
            config = self.ai_server.session_configs.get(session_id, {})
            
            return {
                "success": True,
                "session_id": session_id,
                "config": config
            }
            
        except Exception as e:
            error_message = f"获取会话配置失败: {str(e)}"
            print(f"Error in get_session_config: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        获取可用工具
        
        Returns:
            可用工具列表
        """
        try:
            tools = self.ai_server.get_available_tools()
            
            return {
                "success": True,
                "tools": tools,
                "count": len(tools)
            }
            
        except Exception as e:
            error_message = f"获取可用工具失败: {str(e)}"
            print(f"Error in get_available_tools: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            服务状态信息
        """
        try:
            server_status = self.ai_server.get_server_status()
            
            # 计算运行时间
            current_time = int(time.time() * 1000)
            uptime = current_time - self.service_stats["start_time"]
            
            return {
                "success": True,
                "service_status": "running",
                "uptime_ms": uptime,
                "stats": self.service_stats,
                "server_status": server_status
            }
            
        except Exception as e:
            error_message = f"获取服务状态失败: {str(e)}"
            print(f"Error in get_service_status: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态
        """
        try:
            # 检查AI服务器状态
            server_status = self.ai_server.get_server_status()
            
            is_healthy = server_status.get("status") == "running"
            
            return {
                "healthy": is_healthy,
                "timestamp": int(time.time() * 1000),
                "details": server_status
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "timestamp": int(time.time() * 1000),
                "error": str(e)
            }
    
    def shutdown(self) -> None:
        """关闭服务"""
        try:
            self.ai_server.shutdown()
            print("聊天服务已关闭")
            
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")