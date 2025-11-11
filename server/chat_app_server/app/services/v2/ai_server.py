"""
AI服务器
主要的AI服务入口，管理会话和配置
"""
import time
from typing import Dict, List, Any, Optional, Callable
from openai import OpenAI

from .message_manager import MessageManager
from .ai_request_handler import AiRequestHandler
from .tool_result_processor import ToolResultProcessor
from .mcp_tool_execute import McpToolExecute
from .ai_client import AiClient


class AiServer:
    """AI服务器，主要的AI服务入口"""
    
    def __init__(self, 
                 openai_api_key: str,
                 mcp_tool_execute: McpToolExecute,
                 default_model: str = "gpt-4",
                 default_temperature: float = 0.7,
                 base_url: Optional[str] = None):
        """
        初始化AI服务器
        
        Args:
            openai_api_key: OpenAI API密钥
            mcp_tool_execute: MCP工具执行器实例
            default_model: 默认模型
            default_temperature: 默认温度
            base_url: API基础URL（可选）
        """
        self.default_model = default_model
        self.default_temperature = default_temperature
        
        # 初始化OpenAI客户端
        client_kwargs = {"api_key": openai_api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.openai_client = OpenAI(**client_kwargs)
        
        # 初始化各个组件
        self.message_manager = MessageManager()
        self.ai_request_handler = AiRequestHandler(self.openai_client, self.message_manager)
        self.mcp_tool_execute = mcp_tool_execute
        self.tool_result_processor = ToolResultProcessor(self.message_manager, self.ai_request_handler)
        self.ai_client = AiClient(
            self.ai_request_handler,
            self.mcp_tool_execute,
            self.tool_result_processor,
            self.message_manager
        )
        
        # 会话配置缓存
        self.session_configs: Dict[str, Dict[str, Any]] = {}
    
    def chat(self, 
             session_id: str,
             user_message: str,
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             use_tools: bool = True,
             on_chunk: Optional[Callable[[str], None]] = None,
             on_tools_start: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
             on_tools_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
             on_tools_end: Optional[Callable[[List[Dict[str, Any]]], None]] = None) -> Dict[str, Any]:
        """
        处理聊天请求
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大token数
            use_tools: 是否使用工具
            on_chunk: 流式响应回调
            on_tools_start: 工具开始调用回调
            on_tools_stream: 工具流式内容回调
            on_tools_end: 工具结束回调
            
        Returns:
            聊天响应结果
        """
        try:
            # 使用配置或默认值
            actual_model = model or self.get_session_config(session_id, "model", self.default_model)
            actual_temperature = temperature if temperature is not None else self.get_session_config(session_id, "temperature", self.default_temperature)
            
            # 保存用户消息
            saved_user_message = self.message_manager.save_user_message(
                session_id=session_id,
                content=user_message
            )
            
            # 获取会话历史
            conversation_history = self._get_conversation_history(session_id)
            
            # 添加当前用户消息
            conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # 处理AI请求
            if use_tools:
                result = self.ai_client.process_request(
                    messages=conversation_history,
                    session_id=session_id,
                    model=actual_model,
                    temperature=actual_temperature,
                    max_tokens=max_tokens,
                    on_chunk=on_chunk,
                    on_tools_start=on_tools_start,
                    on_tools_stream=on_tools_stream,
                    on_tools_end=on_tools_end
                )
            else:
                result = self.ai_client.process_simple_request(
                    messages=conversation_history,
                    session_id=session_id,
                    model=actual_model,
                    temperature=actual_temperature,
                    max_tokens=max_tokens
                )
            
            # 添加用户消息信息到结果
            result["user_message"] = saved_user_message
            
            return result
            
        except Exception as e:
            error_message = f"聊天处理失败: {str(e)}"
            print(f"Error in chat: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def stream_chat(self, 
                   session_id: str,
                   user_message: str,
                   model: Optional[str] = None,
                   temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None,
                   use_tools: bool = True) -> Dict[str, Any]:
        """
        流式聊天处理
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大token数
            use_tools: 是否使用工具
            
        Returns:
            流式响应生成器和相关信息
        """
        try:
            chunks = []
            tool_stream_events: List[Dict[str, Any]] = []
            tool_results: List[Dict[str, Any]] = []
            
            def on_chunk(chunk: str):
                chunks.append(chunk)
            
            def on_tools_stream(result: Dict[str, Any]):
                tool_stream_events.append(result)
                # 也将最终结果收集到 tool_results，便于汇总
                if isinstance(result, dict) and (
                    result.get("success") is not None or result.get("is_error") is not None
                ):
                    tool_results.append(result)
            
            # 处理聊天
            result = self.chat(
                session_id=session_id,
                user_message=user_message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                use_tools=use_tools,
                on_chunk=on_chunk,
                on_tools_stream=on_tools_stream
            )
            
            # 返回收集的数据
            result["stream_chunks"] = chunks
            result["tool_stream_events"] = tool_stream_events
            result["tool_results"] = tool_results
            
            return result
            
        except Exception as e:
            error_message = f"流式聊天处理失败: {str(e)}"
            print(f"Error in stream_chat: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_session_config(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        获取会话配置
        
        Args:
            session_id: 会话ID
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.session_configs.get(session_id, {}).get(key, default)
    
    def set_session_config(self, session_id: str, key: str, value: Any) -> None:
        """
        设置会话配置
        
        Args:
            session_id: 会话ID
            key: 配置键
            value: 配置值
        """
        if session_id not in self.session_configs:
            self.session_configs[session_id] = {}
        self.session_configs[session_id][key] = value
    
    def update_session_config(self, session_id: str, config: Dict[str, Any]) -> None:
        """
        更新会话配置
        
        Args:
            session_id: 会话ID
            config: 配置字典
        """
        if session_id not in self.session_configs:
            self.session_configs[session_id] = {}
        self.session_configs[session_id].update(config)
    
    def clear_session_config(self, session_id: str) -> None:
        """
        清除会话配置
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.session_configs:
            del self.session_configs[session_id]
    
    def _get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            limit: 消息数量限制
            
        Returns:
            消息列表
        """
        try:
            # 这里应该从数据库获取消息历史
            # 暂时返回空列表，实际实现需要调用数据库服务
            return []
            
        except Exception as e:
            print(f"Error getting conversation history: {str(e)}")
            return []
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            可用工具列表
        """
        return self.mcp_tool_execute.get_available_tools()
    
    def get_server_status(self) -> Dict[str, Any]:
        """
        获取服务器状态
        
        Returns:
            服务器状态信息
        """
        try:
            available_tools = self.get_available_tools()
            processing_stats = self.ai_client.get_processing_stats()
            
            return {
                "status": "running",
                "default_model": self.default_model,
                "default_temperature": self.default_temperature,
                "available_tools_count": len(available_tools),
                "active_sessions": len(self.session_configs),
                "processing_stats": processing_stats,
                "timestamp": int(time.time() * 1000)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }
    
    def reset_session(self, session_id: str) -> Dict[str, Any]:
        """
        重置会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            重置结果
        """
        try:
            # 清除会话配置
            self.clear_session_config(session_id)
            
            # 清除消息缓存（如果需要）
            self.message_manager.clear_cache()
            
            return {
                "success": True,
                "message": f"会话 {session_id} 已重置"
            }
            
        except Exception as e:
            error_message = f"重置会话失败: {str(e)}"
            print(f"Error in reset_session: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def shutdown(self) -> None:
        """关闭服务器"""
        try:
            # 清理资源
            self.session_configs.clear()
            self.message_manager.clear_cache()
            print("AI服务器已关闭")
            
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")