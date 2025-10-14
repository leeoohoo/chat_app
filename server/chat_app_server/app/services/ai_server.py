"""
AI服务器 - Python实现
对应TypeScript中的AiServer类
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from .ai_client import AiClient
from .ai_request_handler import AiModelConfig, Message, CallbackType
from .message_manager import MessageManager
from .tool_result_processor import ToolResultProcessor
from .mcp_tool_execute import McpToolExecute

logger = logging.getLogger(__name__)


class AiServer:
    """
    AI服务器
    负责协调AI客户端、消息管理器、工具执行器等组件
    """
    
    def __init__(
        self,
        database_service,
        mcp_tool_execute: Optional[McpToolExecute] = None
    ):
        self.database_service = database_service
        self.message_manager = MessageManager(database_service)
        self.mcp_tool_execute = mcp_tool_execute or McpToolExecute()
        
        # AI客户端将在需要时创建
        self.ai_client: Optional[AiClient] = None
        self.tool_result_processor: Optional[ToolResultProcessor] = None
        
        # 回调函数
        self.callback: Optional[Callable] = None
        
    def set_callback(self, callback: Callable) -> None:
        """设置回调函数"""
        self.callback = callback
        
    def _create_ai_client(
        self, 
        model_config: AiModelConfig,
        messages: List[Message],
        conversation_id: str,
        tools: List[Any],
        callback: Callable[[CallbackType, Any], None]
    ) -> AiClient:
        """创建AI客户端"""
        ai_client = AiClient(
            messages=messages,
            conversation_id=conversation_id,
            tools=tools,
            model_config=model_config,
            callback=callback,
            mcp_tool_execute=self.mcp_tool_execute
        )
        
        # 创建工具结果处理器
        self.tool_result_processor = ToolResultProcessor(ai_client)
        
        return ai_client
    
    def send_message_sync(
        self,
        session_id: str,
        content: str,
        model_config: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> Message:
        """
        发送消息（同步版本）
        
        Args:
            session_id: 会话ID
            content: 消息内容
            model_config: 模型配置
            callback: 回调函数
            
        Returns:
            保存的用户消息
        """
        try:
            # 保存用户消息（同步版本）
            user_message_data = {
                "session_id": session_id,
                "role": "user",
                "content": content,
                "status": "completed",
                "created_at": datetime.now()
            }
            
            user_message = self.message_manager.save_user_message_sync(user_message_data)
            
            # 调用sendMessageDirect处理AI响应（同步版本）
            self.send_message_direct_sync(
                session_id=session_id,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                model_config=model_config,
                callback=callback
            )
            
            return user_message
            
        except Exception as e:
            import traceback
            error_details = f"Error in send_message_sync: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            if callback:
                callback("error", {"error": str(e)})
            raise

    async def send_message(
        self,
        session_id: str,
        content: str,
        model_config: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> Message:
        """
        发送消息
        
        Args:
            session_id: 会话ID
            content: 消息内容
            model_config: 模型配置
            callback: 回调函数
            
        Returns:
            保存的用户消息
        """
        try:
            # 保存用户消息
            user_message_data = {
                "session_id": session_id,
                "role": "user",
                "content": content,
                "status": "completed",
                "created_at": datetime.now()
            }
            
            user_message = await self.message_manager.save_user_message(user_message_data)
            
            # 调用sendMessageDirect处理AI响应
            await self.send_message_direct(
                session_id=session_id,
                messages=[{
                    "role": "user",
                    "content": content
                }],
                model_config=model_config,
                callback=callback
            )
            
            return user_message
            
        except Exception as e:
            import traceback
            error_details = f"Error in send_message: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            if callback:
                callback("error", {"error": str(e)})
            raise
    
    async def send_message_direct(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        model_config: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> None:
        """
        直接发送消息（不保存用户消息）
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            model_config: 模型配置
            callback: 回调函数
        """
        try:
            # 创建模型配置
            if model_config:
                ai_model_config = AiModelConfig(
                    model_name=model_config.get("model_name", "gpt-3.5-turbo"),
                    temperature=model_config.get("temperature", 0.7),
                    max_tokens=model_config.get("max_tokens", 1000),
                    api_key=model_config.get("api_key", ""),
                    base_url=model_config.get("base_url", "https://api.openai.com/v1")
                )
            else:
                # 使用默认配置
                ai_model_config = AiModelConfig()
            
            # 设置回调函数
            effective_callback = callback or self.callback
            
            # 创建内部回调函数来处理各种事件
            async def internal_callback_async(callback_type: str, data: Any):
                try:
                    if callback_type == "chunk":
                        # 处理文本块
                        if effective_callback:
                            effective_callback("chunk", data)
                    
                    elif callback_type == "tool_call":
                        # 处理工具调用
                        if effective_callback:
                            effective_callback("tool_call", data)
                    
                    elif callback_type == "tool_result":
                        # 处理工具结果
                        tool_call_id = data.get("tool_call_id")
                        result = data.get("result")
                        
                        # 使用工具结果处理器处理结果
                        if self.tool_result_processor and result:
                            processed_result = await self.tool_result_processor.process_tool_result(
                                tool_call_id=tool_call_id,
                                tool_name=data.get("tool_name", "unknown"),
                                result=result,
                                callback=effective_callback
                            )
                            
                            # 更新结果
                            data["result"] = processed_result
                        
                        if effective_callback:
                            effective_callback("tool_result", data)
                    
                    elif callback_type == "tool_stream_chunk":
                        # 处理工具流式块
                        if effective_callback:
                            effective_callback("tool_stream_chunk", data)
                    
                    elif callback_type == "complete":
                        # 处理完成事件
                        assistant_message = data.get("message")
                        
                        if assistant_message:
                            # 构建工具调用数据
                            tool_calls_data = []
                            if assistant_message.tool_calls:
                                for tc in assistant_message.tool_calls:
                                    tool_call_data = {
                                        "id": tc.get("id") if isinstance(tc, dict) else tc.id,
                                        "type": tc.get("type", "function") if isinstance(tc, dict) else tc.type,
                                        "function": {
                                            "name": tc.get("function", {}).get("name") if isinstance(tc, dict) else tc.function.name,
                                            "arguments": tc.get("function", {}).get("arguments") if isinstance(tc, dict) else tc.function.arguments
                                        }
                                    }
                                    # 只有在有结果时才添加result字段
                                    if isinstance(tc, dict) and tc.get("result"):
                                        tool_call_data["result"] = tc.get("result")
                                    elif hasattr(tc, 'result') and tc.result:
                                        tool_call_data["result"] = tc.result
                                    
                                    tool_calls_data.append(tool_call_data)
                            
                            # 保存助手消息
                            assistant_message_data = {
                                "session_id": session_id,
                                "role": "assistant",
                                "content": assistant_message.content,
                                "status": "completed",
                                "created_at": datetime.now(),
                                "metadata": {
                                    "tool_calls": tool_calls_data
                                },
                                "tool_calls": tool_calls_data  # 同时保存在tool_calls字段中
                            }
                            
                            logger.info(f"🔧 [DEBUG] Saving assistant message with {len(tool_calls_data)} tool calls")
                            saved_message = await self.message_manager.save_assistant_message(assistant_message_data)
                            
                            # 更新数据中的消息
                            data["message"] = saved_message
                        
                        if effective_callback:
                            effective_callback("complete", data)
                    
                    elif callback_type == "error":
                        # 处理错误
                        if effective_callback:
                            effective_callback("error", data)
                    
                    elif callback_type == "summary_chunk":
                        # 处理摘要块（来自工具结果处理器）
                        if effective_callback:
                            effective_callback("summary_chunk", data)
                    
                    else:
                        # 其他类型的回调
                        if effective_callback:
                            effective_callback(callback_type, data)
                            
                except Exception as e:
                    logger.error(f"Error in internal callback: {e}")
                    if effective_callback:
                            effective_callback("error", {"error": str(e)})
            
            # 创建同步包装器
            def internal_callback(callback_type: str, data: Any):
                """同步包装器，用于调度异步回调"""
                import asyncio
                try:
                    # 获取当前事件循环
                    loop = asyncio.get_event_loop()
                    # 创建任务但不等待
                    loop.create_task(internal_callback_async(callback_type, data))
                except RuntimeError:
                    # 如果没有运行的事件循环，创建一个新的
                    asyncio.create_task(internal_callback_async(callback_type, data))
                except Exception as e:
                    logger.error(f"Error scheduling async callback: {e}")
            
            # 将字典格式的消息转换为Message对象
            message_objects = []
            for msg_dict in messages:
                message_obj = Message(
                    role=msg_dict.get("role", "user"),
                    content=msg_dict.get("content", ""),
                    session_id=session_id
                )
                message_objects.append(message_obj)
            
            # 获取可用工具
            available_tools = self.get_available_tools()
            
            # 创建AI客户端
            self.ai_client = self._create_ai_client(
                model_config=ai_model_config,
                messages=message_objects,
                conversation_id=session_id,
                tools=available_tools,
                callback=internal_callback
            )
            
            # 启动AI客户端
            await self.ai_client.start()
            
        except Exception as e:
            import traceback
            error_details = f"Error in send_message_direct: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            if callback:
                callback("error", {"error": str(e)})
            raise
    
    def send_message_direct_sync(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        model_config: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> None:
        """
        直接发送消息（同步版本，不保存用户消息）
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            model_config: 模型配置
            callback: 回调函数
        """
        try:
            # 创建模型配置
            if model_config:
                ai_model_config = AiModelConfig(
                    model_name=model_config.get("model_name", "gpt-3.5-turbo"),
                    temperature=model_config.get("temperature", 0.7),
                    max_tokens=model_config.get("max_tokens", 1000),
                    api_key=model_config.get("api_key", ""),
                    base_url=model_config.get("base_url", "https://api.openai.com/v1")
                )
            else:
                # 使用默认配置
                ai_model_config = AiModelConfig()
            
            # 设置回调函数
            effective_callback = callback or self.callback
            
            # 创建内部回调函数来处理各种事件（同步版本）
            def internal_callback(callback_type: str, data: Any):
                try:
                    if callback_type == "chunk":
                        # 处理文本块
                        if effective_callback:
                            effective_callback("chunk", data)
                    
                    elif callback_type == "tool_call":
                        # 处理工具调用
                        if effective_callback:
                            effective_callback("tool_call", data)
                    
                    elif callback_type == "tool_result":
                        # 处理工具结果
                        tool_call_id = data.get("tool_call_id")
                        result = data.get("result")
                        
                        # 使用工具结果处理器处理结果（同步版本）
                        if self.tool_result_processor and result:
                            processed_result = self.tool_result_processor.process_tool_result_sync(
                                tool_call_id=tool_call_id,
                                tool_name=data.get("tool_name", "unknown"),
                                result=result,
                                callback=effective_callback
                            )
                            
                            # 更新结果
                            data["result"] = processed_result
                        
                        if effective_callback:
                            effective_callback("tool_result", data)
                    
                    elif callback_type == "tool_stream_chunk":
                        # 处理工具流式块
                        if effective_callback:
                            effective_callback("tool_stream_chunk", data)
                    
                    elif callback_type == "complete":
                        # 处理完成事件
                        assistant_message = data.get("message")
                        
                        if assistant_message:
                            # 构建工具调用数据
                            tool_calls_data = []
                            if assistant_message.tool_calls:
                                for tc in assistant_message.tool_calls:
                                    tool_call_data = {
                                        "id": tc.get("id") if isinstance(tc, dict) else tc.id,
                                        "type": tc.get("type", "function") if isinstance(tc, dict) else tc.type,
                                        "function": {
                                            "name": tc.get("function", {}).get("name") if isinstance(tc, dict) else tc.function.name,
                                            "arguments": tc.get("function", {}).get("arguments") if isinstance(tc, dict) else tc.function.arguments
                                        }
                                    }
                                    # 只有在有结果时才添加result字段
                                    if isinstance(tc, dict) and tc.get("result"):
                                        tool_call_data["result"] = tc.get("result")
                                    elif hasattr(tc, 'result') and tc.result:
                                        tool_call_data["result"] = tc.result
                                    
                                    tool_calls_data.append(tool_call_data)
                            
                            # 保存助手消息（同步版本）
                            assistant_message_data = {
                                "session_id": session_id,
                                "role": "assistant",
                                "content": assistant_message.content,
                                "status": "completed",
                                "created_at": datetime.now(),
                                "metadata": {
                                    "tool_calls": tool_calls_data
                                },
                                "tool_calls": tool_calls_data  # 同时保存在tool_calls字段中
                            }
                            
                            logger.info(f"🔧 [DEBUG] Saving assistant message with {len(tool_calls_data)} tool calls")
                            saved_message = self.message_manager.save_assistant_message_sync(assistant_message_data)
                            
                            # 更新数据中的消息
                            data["message"] = saved_message
                        
                        if effective_callback:
                            effective_callback("complete", data)
                    
                    elif callback_type == "error":
                        # 处理错误
                        if effective_callback:
                            effective_callback("error", data)
                    
                    elif callback_type == "summary_chunk":
                        # 处理摘要块（来自工具结果处理器）
                        if effective_callback:
                            effective_callback("summary_chunk", data)
                    
                    else:
                        # 其他类型的回调
                        if effective_callback:
                            effective_callback(callback_type, data)
                            
                except Exception as e:
                    logger.error(f"Error in internal callback: {e}")
                    if effective_callback:
                        effective_callback("error", {"error": str(e)})
            
            # 将字典格式的消息转换为Message对象
            message_objects = []
            for msg_dict in messages:
                message_obj = Message(
                    role=msg_dict.get("role", "user"),
                    content=msg_dict.get("content", ""),
                    session_id=session_id
                )
                message_objects.append(message_obj)
            
            # 获取可用工具
            available_tools = self.get_available_tools()
            
            # 创建AI客户端
            self.ai_client = self._create_ai_client(
                model_config=ai_model_config,
                messages=message_objects,
                conversation_id=session_id,
                tools=available_tools,
                callback=internal_callback
            )
            
            # 启动AI客户端（同步版本）
            self.ai_client.start_sync()
            
        except Exception as e:
            import traceback
            error_details = f"Error in send_message_direct_sync: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            if callback:
                callback("error", {"error": str(e)})
            raise
    
    def abort_request(self) -> None:
        """中止当前请求"""
        logger.info("🛑 [DEBUG] AiServer.abort_request 被调用")
        if self.ai_client:
            logger.info(f"🛑 [DEBUG] ai_client存在，类型: {type(self.ai_client)}")
            self.ai_client.abort()
            logger.info("🛑 [DEBUG] AI request aborted")
        else:
            logger.warning("🛑 [DEBUG] ai_client为None，无法中止请求")
    
    def is_request_aborted(self) -> bool:
        """检查请求是否被中止"""
        if self.ai_client:
            return self.ai_client.is_request_aborted()
        return False
    
    def reset_abort_state(self) -> None:
        """重置中止状态"""
        if self.ai_client:
            self.ai_client.reset_abort_state()
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self.mcp_tool_execute.get_tools()
    
    def get_servers_info(self) -> List[Dict[str, Any]]:
        """获取MCP服务器信息"""
        return self.mcp_tool_execute.get_servers_info()
    
    async def get_session_messages(self, session_id: str) -> List[Message]:
        """获取会话消息"""
        try:
            messages_data = await self.database_service.get_messages_by_session(session_id)
            
            messages = []
            for msg_data in messages_data:
                message = Message(
                    id=msg_data.get('id'),
                    session_id=msg_data.get('session_id'),
                    role=msg_data.get('role'),
                    content=msg_data.get('content'),
                    status=msg_data.get('status', 'completed'),
                    created_at=msg_data.get('created_at'),
                    metadata=msg_data.get('metadata'),
                    tool_calls=msg_data.get('tool_calls')
                )
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []
    
    def clear_message_cache(self) -> None:
        """清除消息缓存"""
        self.message_manager.clear_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self.message_manager.get_cache_stats()