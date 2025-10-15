"""
AI请求处理器 - Python实现
对应TypeScript中的AiRequestHandler类
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

logger = logging.getLogger(__name__)


class CallbackType(Enum):
    """回调类型枚举"""
    ON_CHUNK = "onChunk"
    ON_TOOL_CALL = "onToolCall"
    ON_TOOL_RESULT = "onToolResult"
    ON_TOOL_STREAM_CHUNK = "onToolStreamChunk"
    ON_COMPLETE = "onComplete"
    ON_ERROR = "onError"


@dataclass
class AiModelConfig:
    """AI模型配置"""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1000
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    type: str = "function"
    function: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式以支持JSON序列化"""
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function,
            "result": self.result
        }


@dataclass
class Message:
    """消息"""
    id: Optional[str] = None
    session_id: Optional[str] = None
    role: str = "user"
    content: str = ""
    status: str = "completed"
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[ToolCall]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": tc.function,
                    "result": tc.result
                }
                for tc in self.tool_calls
            ] if self.tool_calls else None
        }


class AiRequestHandler:
    """AI请求处理器，负责与OpenAI API交互"""
    
    def __init__(
        self,
        messages: List[Message],
        tools: List[Any],
        conversation_id: str,
        callback: Callable[[CallbackType, Any], None],
        model_config: AiModelConfig,
        config_url: str = "/api",
        session_id: Optional[str] = None,
        message_manager = None
    ):
        self.messages = messages
        self.tools = tools
        self.conversation_id = conversation_id
        self.callback = callback
        self.model_config = model_config
        self.config_url = config_url
        self.session_id = session_id or conversation_id
        self.message_manager = message_manager
        self.is_aborted = False
        self.current_task = None  # 存储当前运行的任务
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=model_config.api_key,
            base_url=model_config.base_url
        )
        
        logger.info(f"AiRequestHandler initialized - configUrl: {self.config_url}")
        logger.info(f"Model config base_url: {self.model_config.base_url}")

    def chat_completion(self) -> List[Message]:
        """
        发送聊天完成请求
        返回更新后的消息列表
        """
        try:
            if self.is_aborted:
                logger.info("Request aborted before starting")
                return self.messages
            
            # 准备消息格式
            formatted_messages = self._format_messages_for_api()
            
            # 准备请求参数
            request_params = {
                "model": self.model_config.model_name,
                "messages": formatted_messages,
                "temperature": self.model_config.temperature,
                "max_tokens": self.model_config.max_tokens,
                "stream": True
            }
            
            # 如果有工具，添加工具参数
            if self.tools:
                request_params["tools"] = self.tools
                request_params["tool_choice"] = "auto"
                logger.info(f"🔧 [DEBUG] 发送给AI的工具数量: {len(self.tools)}")
                logger.info(f"🔧 [DEBUG] 工具详情: {json.dumps(self.tools, indent=2, ensure_ascii=False)}")
            else:
                logger.info("🔧 [DEBUG] 没有工具发送给AI")
            
            logger.info(f"Sending chat completion request with {len(formatted_messages)} messages")
            logger.info(f"🔧 [DEBUG] 完整请求参数: {json.dumps({k: v for k, v in request_params.items() if k != 'messages'}, indent=2, ensure_ascii=False)}")
            
            # 发送同步请求
            stream = self.client.chat.completions.create(**request_params)
            # 处理流式响应
            return self._handle_openai_stream_response(stream)
            
            return updated_messages
            
        except Exception as e:
            import traceback
            error_details = f"Chat completion error: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            if self.callback:
                self.callback(CallbackType.ON_ERROR, str(e))
            return self.messages

    def _format_messages_for_api(self) -> List[Dict[str, Any]]:
        """将消息格式化为OpenAI API格式"""
        formatted = []
        
        logger.info(f"🔧 [FORMAT_DEBUG] Formatting {len(self.messages)} messages for API")
        
        for i, msg in enumerate(self.messages):
            logger.info(f"🔧 [FORMAT_MSG_{i}] Role: {msg.role}, Content length: {len(msg.content)}, Has tool_calls: {bool(msg.tool_calls)}")
            
            formatted_msg = {
                "role": msg.role,
                "content": msg.content
            }
            
            # 如果有工具调用，添加tool_calls字段
            if msg.tool_calls:
                formatted_msg["tool_calls"] = [tc.to_dict() for tc in msg.tool_calls]
                logger.info(f"🔧 [FORMAT_TOOL_CALLS_{i}] Added {len(msg.tool_calls)} tool calls")
            
            # 如果是工具消息，添加tool_call_id和name字段
            if msg.role == "tool" and msg.metadata:
                tool_call_id = msg.metadata.get("tool_call_id")
                tool_name = msg.metadata.get("tool_name")
                if tool_call_id:
                    formatted_msg["tool_call_id"] = tool_call_id
                    logger.info(f"🔧 [FORMAT_TOOL_MSG_{i}] Tool call ID: {tool_call_id}, Tool name: {tool_name}")
                if tool_name:
                    formatted_msg["name"] = tool_name
                
            formatted.append(formatted_msg)
            
        logger.info(f"🔧 [FORMAT_RESULT] Formatted {len(formatted)} messages for API")
        return formatted

    def _handle_openai_stream_response(self, stream) -> List[Message]:
        """
        处理OpenAI流式响应
        对应TypeScript中的handleOpenAIStreamResponse方法
        """
        try:
            accumulated_content = ""
            accumulated_tool_calls = []
            chunk_count = 0
            
            for chunk in stream:
                if self.is_aborted:
                    logger.info("Stream processing aborted")
                    break
                    
                chunk_count += 1
                
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    # 处理内容增量
                    if hasattr(delta, 'content') and delta.content:
                        accumulated_content += delta.content
                        
                        if self.callback:
                            self.callback(CallbackType.ON_CHUNK, {
                                "type": "chunk",
                                "content": delta.content,
                                "accumulated": accumulated_content
                            })
                    
                    # 处理工具调用增量
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        logger.info(f"🔧 [DEBUG] Received tool_calls delta with {len(delta.tool_calls)} calls")
                        tool_call_event_sent = False
                        
                        for tool_call_delta in delta.tool_calls:
                            logger.info(f"🔧 [DEBUG] Processing tool call delta: index={tool_call_delta.index}, id={getattr(tool_call_delta, 'id', None)}")
                            
                            # 确保accumulated_tool_calls有足够的元素
                            while len(accumulated_tool_calls) <= tool_call_delta.index:
                                accumulated_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            
                            # 更新工具调用信息
                            if tool_call_delta.id:
                                accumulated_tool_calls[tool_call_delta.index]["id"] = tool_call_delta.id
                                logger.info(f"🔧 [DEBUG] Set tool call id: {tool_call_delta.id}")
                            
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    accumulated_tool_calls[tool_call_delta.index]["function"]["name"] = tool_call_delta.function.name
                                    logger.info(f"🔧 [DEBUG] Set tool function name: {tool_call_delta.function.name}")
                                    
                                    # 当我们第一次收到工具名称时，发送ON_TOOL_CALL事件
                                    if not tool_call_event_sent and self.callback:
                                        # 准备当前的工具调用数据（不需要结果）
                                        current_tool_calls = []
                                        for tc in accumulated_tool_calls:
                                            if tc.get("id") and tc.get("function", {}).get("name"):
                                                tool_call_data = {
                                                    "id": tc.get("id", ""),
                                                    "type": tc.get("type", "function"),
                                                    "function": tc.get("function", {})
                                                }
                                                current_tool_calls.append(tool_call_data)
                                        
                                        if current_tool_calls:
                                            logger.info(f"🔧 [DEBUG] Sending ON_TOOL_CALL event with {len(current_tool_calls)} tool calls")
                                            self.callback(CallbackType.ON_TOOL_CALL, current_tool_calls)
                                            tool_call_event_sent = True
                                
                                if tool_call_delta.function.arguments:
                                    accumulated_tool_calls[tool_call_delta.index]["function"]["arguments"] += tool_call_delta.function.arguments
                                    logger.info(f"🔧 [DEBUG] Added function arguments: {tool_call_delta.function.arguments}")
                        
                        logger.info(f"🔧 [DEBUG] Current accumulated_tool_calls count: {len(accumulated_tool_calls)}")
                    
                    # 检查是否完成
                    if choice.finish_reason:
                        logger.info(f"Stream finished with reason: {choice.finish_reason}")
                        break
            
            logger.info(f"OpenAI stream completed. Processed {chunk_count} chunks.")
            
            # 创建新的助手消息
            assistant_message = Message(
                id=f"msg_{self.session_id}_{len(self.messages)}",
                session_id=self.session_id,
                role="assistant",
                content=accumulated_content,
                status="completed"
            )
            
            # 如果有工具调用，转换为 ToolCall 对象并添加到消息中
            if accumulated_tool_calls:
                logger.info(f"🔧 [DEBUG] Found {len(accumulated_tool_calls)} accumulated tool calls")
                for i, tc in enumerate(accumulated_tool_calls):
                    logger.info(f"🔧 [DEBUG] Tool call {i}: id={tc.get('id')}, function={tc.get('function', {}).get('name')}")
                
                assistant_message.tool_calls = [
                    ToolCall(
                        id=tc.get("id", ""),
                        type=tc.get("type", "function"),
                        function=tc.get("function"),
                        result=tc.get("result")
                    )
                    for tc in accumulated_tool_calls
                ]
                logger.info(f"🔧 [DEBUG] Created {len(assistant_message.tool_calls)} ToolCall objects")
            else:
                logger.info("🔧 [DEBUG] No accumulated tool calls found")
            
            # 更新消息列表
            updated_messages = self.messages.copy()
            updated_messages.append(assistant_message)
            
            # 直接保存AI消息到数据库
            if self.message_manager and self.session_id:
                try:
                    # 准备工具调用数据
                    tool_calls_data = []
                    if accumulated_tool_calls:
                        for tc in accumulated_tool_calls:
                            tool_call_data = {
                                "id": tc.get("id", ""),
                                "type": tc.get("type", "function"),
                                "function": tc.get("function", {})
                            }
                            # 只有在有结果时才添加result字段
                            if isinstance(tc, dict) and tc.get("result"):
                                tool_call_data["result"] = tc.get("result")
                            elif hasattr(tc, 'result') and tc.result:
                                tool_call_data["result"] = tc.result
                            
                            tool_calls_data.append(tool_call_data)
                    
                    # 保存助手消息
                    assistant_message_data = {
                        "sessionId": self.session_id,
                        "role": "assistant",
                        "content": assistant_message.content,
                        "status": "completed",
                        "createdAt": datetime.now(),
                        "metadata": {
                            "toolCalls": tool_calls_data
                        },
                        "toolCalls": tool_calls_data
                    }
                    
                    logger.info(f"🔧 [DEBUG] Directly saving assistant message with {len(tool_calls_data)} tool calls")
                    saved_message = self.message_manager.save_assistant_message_sync(assistant_message_data)
                    logger.info(f"🎯 Assistant message saved successfully: {saved_message.id}")
                    
                    # ON_TOOL_CALL事件已经在检测到工具调用时发送了，这里不需要重复发送
                    
                    # 当有工具调用时，不触发完成回调，因为对话还没有真正完成
                    # 只有在没有工具调用的情况下才触发完成回调
                    if not accumulated_tool_calls and self.callback:
                        self.callback(CallbackType.ON_COMPLETE, {
                            "message": assistant_message,
                            "accumulated_content": accumulated_content,
                            "tool_calls": accumulated_tool_calls,
                            "saved_message": saved_message,
                            "final": True  # 标记这是最终的完成事件
                        })
                        
                except Exception as e:
                    logger.error(f"Error saving assistant message: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                logger.warning("⚠️ No message_manager or session_id available for saving assistant message")
                # 只有在没有工具调用的情况下才触发完成回调
                if not accumulated_tool_calls and self.callback:
                    self.callback(CallbackType.ON_COMPLETE, {
                        "message": assistant_message,
                        "accumulated_content": accumulated_content,
                        "tool_calls": accumulated_tool_calls,
                        "final": True  # 标记这是最终的完成事件
                    })
            
            return updated_messages
            
        except Exception as e:
            import traceback
            error_details = f"Error handling OpenAI stream: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            if self.callback:
                self.callback(CallbackType.ON_ERROR, str(e))
            return self.messages

    def abort(self) -> None:
        """中止当前请求"""
        logger.info("🛑 [DEBUG] AiRequestHandler.abort 被调用")
        self.is_aborted = True
        logger.info("🛑 [DEBUG] AI request handler aborted")
        
        # 如果有正在运行的任务，取消它
        if self.current_task and not self.current_task.done():
            logger.info(f"🛑 [DEBUG] 正在取消任务，任务状态: {self.current_task}")
            self.current_task.cancel()
            logger.info("🛑 [DEBUG] Current AI task cancelled")
        else:
            if self.current_task is None:
                logger.warning("🛑 [DEBUG] current_task为None，无法取消")
            elif self.current_task.done():
                logger.warning("🛑 [DEBUG] current_task已完成，无需取消")

    def is_request_aborted(self) -> bool:
        """检查请求是否被中止"""
        return self.is_aborted