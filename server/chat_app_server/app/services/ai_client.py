"""
AI客户端 - Python实现
对应TypeScript中的AiClient类
"""
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .ai_request_handler import AiRequestHandler, AiModelConfig, Message, ToolCall, CallbackType
from .tool_result_processor import ToolResultProcessor
from .message_manager import MessageManager
from .mcp_tool_execute import McpToolExecute

logger = logging.getLogger(__name__)



class AiClient:
    """AI客户端类，处理消息流和工具调用"""
    
    def __init__(
        self,
        messages: List[Message],
        conversation_id: str,
        tools: List[Any],
        model_config: AiModelConfig,
        callback: Callable[[CallbackType, Any], None],
        mcp_tool_execute: Optional[McpToolExecute] = None,
        message_manager: Optional[MessageManager] = None,
        config_url: str = "/api",
        external_abort_controller: Optional[Any] = None,
        session_id: Optional[str] = None
    ):
        self.messages = messages
        self.conversation_id = conversation_id
        self.tools = tools
        self.model_config = model_config
        self.callback = callback
        self.mcp_tool_execute = mcp_tool_execute
        self.message_manager = message_manager
        self.config_url = config_url
        self.session_id = session_id or conversation_id
        
        # 状态管理
        self.is_aborted = False
        self.current_ai_request_handler: Optional[AiRequestHandler] = None
        
        # 初始化组件
        if message_manager:
            self.tool_result_processor = ToolResultProcessor(self)
        else:
            self.tool_result_processor = None
        
        logger.info(f"AiClient initialized - configUrl: {self.config_url}")

    def start(self) -> None:
        """开始AI对话处理"""
        try:
            max_rounds = 10
            current_round = 0
            
            while current_round < max_rounds:
                if self.is_aborted:
                    logger.info("AI processing aborted by user")
                    break
                    
                current_round += 1
                logger.info(f"Starting round {current_round}")
                
                # 处理AI响应
                has_tool_calls = self._process_ai_response()
                
                if self.is_aborted:
                    break
                
                # 如果有工具调用，执行工具
                if has_tool_calls:
                    last_message = self.messages[-1] if self.messages else None
                    if (last_message and 
                        last_message.role == "assistant" and 
                        last_message.tool_calls and 
                        len(last_message.tool_calls) > 0):
                        
                        # 执行工具调用
                        self._execute_tools(last_message.tool_calls)
                        
                        if self.is_aborted:
                            break
                        
                        # 继续下一轮处理
                        continue
                else:
                    # 没有工具调用，对话结束
                    # ai_request_handler已经在没有工具调用时发送了ON_COMPLETE事件，这里不需要重复发送
                    logger.info("🎯 Conversation completed, ON_COMPLETE event already sent by ai_request_handler")
                    break
                    
            if current_round >= max_rounds:
                self.callback(CallbackType.ON_ERROR, "Maximum rounds reached")
                
        except Exception as e:
            import traceback
            error_details = f"Error in AI processing: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            self.callback(CallbackType.ON_ERROR, str(e))

    def start_sync(self) -> None:
        """开始AI对话处理（同步版本，与start方法相同）"""
        return self.start()

    def _execute_tools(self, tool_calls: List[ToolCall]) -> None:
        """执行工具调用"""
        if not self.mcp_tool_execute:
            logger.warning("No MCP tool executor available")
            return
            
        try:
            logger.info(f"🔧 [TOOL_EXECUTION] Starting execution of {len(tool_calls)} tool calls")
            
            # 将ToolCall对象转换为可序列化的字典
            serializable_tool_calls = []
            for tool_call in tool_calls:
                if hasattr(tool_call, 'to_dict'):
                    serializable_tool_calls.append(tool_call.to_dict())
                else:
                    # 如果是字典格式，直接使用
                    serializable_tool_calls.append(tool_call)
            
            # 打印工具调用详情
            for i, tool_call_dict in enumerate(serializable_tool_calls):
                tool_name = tool_call_dict.get("function", {}).get("name") or tool_call_dict.get("name")
                tool_args = tool_call_dict.get("function", {}).get("arguments", {})
                tool_id = tool_call_dict.get("id", "unknown")
                logger.info(f"🔧 [TOOL_CALL_{i+1}] Tool: {tool_name}, ID: {tool_id}")
                logger.info(f"🔧 [TOOL_ARGS_{i+1}] Arguments: {json.dumps(tool_args, ensure_ascii=False, indent=2)}")
            
            # 注意：ON_TOOL_CALL事件已经在ai_request_handler.py中发送，这里不需要重复发送
            
            # 存储工具响应消息，用于添加到对话历史
            tool_response_messages = []
            
            # 执行每个工具调用
            for i, tool_call in enumerate(tool_calls):
                if self.is_aborted:
                    break
                    
                # 从ToolCall对象获取工具名称
                if hasattr(tool_call, 'function') and tool_call.function:
                    tool_name = tool_call.function.get("name")
                else:
                    tool_name = None
                    
                if not tool_name:
                    logger.warning(f"🔧 [TOOL_SKIP_{i+1}] Skipping tool call without name")
                    continue
                    
                # 检查工具是否支持流式输出
                supports_streaming = self.mcp_tool_execute.supports_streaming(tool_name)
                
                if supports_streaming:
                    logger.info(f"🔧 [TOOL_EXEC_{i+1}] Using streaming execution for tool: {tool_name}")
                    
                    # 提取工具参数
                    tool_arguments = {}
                    if hasattr(tool_call, 'function') and tool_call.function:
                        tool_arguments = tool_call.function.get("arguments", {})
                        if isinstance(tool_arguments, str):
                            try:
                                tool_arguments = json.loads(tool_arguments)
                            except json.JSONDecodeError:
                                tool_arguments = {}
                    
                    tool_call_id = tool_call.id if hasattr(tool_call, 'id') else f"call_{tool_name}_{int(datetime.now().timestamp())}"
                    
                    logger.info(f"🔧 [STREAM_START_{i+1}] Tool: {tool_name}, ID: {tool_call_id}")
                    logger.info(f"🔧 [STREAM_ARGS_{i+1}] Arguments: {json.dumps(tool_arguments, ensure_ascii=False, indent=2)}")
                    
                    # 流式执行工具
                    tool_result = {"content": "", "tool_name": tool_name}
                    chunk_count = 0
                    
                    def on_chunk(chunk: str):
                        nonlocal chunk_count
                        chunk_count += 1
                        processed_chunk = self._process_chunk(chunk)
                        tool_result["content"] += processed_chunk
                        
                        logger.info(f"🔧 [STREAM_CHUNK_{i+1}_{chunk_count}] Tool: {tool_name}, Chunk: {processed_chunk[:100]}{'...' if len(processed_chunk) > 100 else ''}")
                        
                        # 通知前端工具流式数据
                        self.callback(CallbackType.ON_TOOL_STREAM_CHUNK, {
                            "tool_call_id": tool_call_id,
                            "chunk": processed_chunk,
                            "tool_name": tool_name
                        })
                    
                    def on_complete():
                        logger.info(f"🔧 [STREAM_COMPLETE_{i+1}] Tool: {tool_name}, Total chunks: {chunk_count}, Total length: {len(tool_result['content'])}")
                    
                    def on_error(error: Exception):
                        logger.error(f"🔧 [STREAM_ERROR_{i+1}] Tool: {tool_name}, Error: {error}")
                        self.callback(CallbackType.ON_ERROR, str(error))
                    
                    self.mcp_tool_execute.execute_stream_sync(
                        tool_name, tool_arguments, tool_call_id, on_chunk, on_complete, on_error
                    )
                    
                    # 处理工具结果
                    logger.info(f"🔧 [STREAM_RAW_RESULT_{i+1}] Tool: {tool_name}, Raw result length: {len(tool_result['content'])}")
                    logger.info(f"🔧 [STREAM_RAW_CONTENT_{i+1}] Tool: {tool_name}, Raw content: {tool_result['content'][:500]}{'...' if len(tool_result['content']) > 500 else ''}")
                    
                    if self.tool_result_processor:
                        processed_result = self.tool_result_processor.process_tool_result_sync(
                            tool_call_id, tool_name, tool_result["content"]
                        )
                        logger.info(f"🔧 [STREAM_PROCESSED_{i+1}] Tool: {tool_name}, Processed result length: {len(processed_result)}")
                    else:
                        processed_result = tool_result["content"]
                        logger.info(f"🔧 [STREAM_NO_PROCESSOR_{i+1}] Tool: {tool_name}, Using raw result")
                    
                    logger.info(f"🔧 [STREAM_FINAL_RESULT_{i+1}] Tool: {tool_name}, Final result: {processed_result[:500]}{'...' if len(processed_result) > 500 else ''}")
                    
                    # 保存工具消息到数据库
                    if self.message_manager:
                        try:
                            tool_message_data = {
                                "session_id": self.session_id,
                                "role": "tool",
                                "content": processed_result,
                                "status": "completed",
                                "metadata": {
                                    "tool_call_id": tool_call_id,
                                    "tool_name": tool_name
                                }
                            }
                            
                            saved_tool_message = self.message_manager.save_tool_message_sync(tool_message_data)
                            logger.info(f"🔧 [STREAM_SAVE_{i+1}] Saved tool message: {tool_name} (ID: {saved_tool_message.id})")
                            
                        except Exception as e:
                            logger.error(f"🔧 [STREAM_SAVE_ERROR_{i+1}] Failed to save tool message: {e}")
                    
                    # 构造工具响应消息
                    tool_response_message = Message(
                        id=f"tool_msg_{tool_call_id}",
                        session_id=self.session_id,
                        role="tool",
                        content=processed_result,
                        status="completed",
                        metadata={"tool_call_id": tool_call_id, "tool_name": tool_name}
                    )
                    tool_response_messages.append(tool_response_message)
                    
                    # 构造执行结果用于前端回调
                    execute_result = {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": tool_name,
                        "result": processed_result
                    }
                    
                    logger.info(f"🔧 [STREAM_CALLBACK_{i+1}] Tool: {tool_name}, Sending result to frontend")
                    # 通知前端工具执行结果 - 包装成数组格式以匹配前端期望
                    self.callback(CallbackType.ON_TOOL_RESULT, [execute_result])
                        
                else:
                    # 非流式执行
                    logger.info(f"🔧 [TOOL_EXEC_{i+1}] Using non-streaming execution for tool: {tool_name}")
                    
                    # 提取工具参数
                    tool_arguments = {}
                    if hasattr(tool_call, 'function') and tool_call.function:
                        tool_arguments = tool_call.function.get("arguments", {})
                        if isinstance(tool_arguments, str):
                            try:
                                tool_arguments = json.loads(tool_arguments)
                            except json.JSONDecodeError:
                                tool_arguments = {}
                    
                    tool_call_id = tool_call.id if hasattr(tool_call, 'id') else f"call_{tool_name}_{int(datetime.now().timestamp())}"
                    
                    logger.info(f"🔧 [NON_STREAM_START_{i+1}] Tool: {tool_name}, ID: {tool_call_id}")
                    logger.info(f"🔧 [NON_STREAM_ARGS_{i+1}] Arguments: {json.dumps(tool_arguments, ensure_ascii=False, indent=2)}")
                    
                    # 调用工具执行
                    result_content = self.mcp_tool_execute.execute_sync(tool_name, tool_arguments)
                    
                    logger.info(f"🔧 [NON_STREAM_RAW_RESULT_{i+1}] Tool: {tool_name}, Raw result length: {len(str(result_content))}")
                    logger.info(f"🔧 [NON_STREAM_RAW_CONTENT_{i+1}] Tool: {tool_name}, Raw content: {str(result_content)[:500]}{'...' if len(str(result_content)) > 500 else ''}")
                    
                    # 处理工具结果
                    if self.tool_result_processor:
                        processed_result = self.tool_result_processor.process_tool_result_sync(
                            tool_call_id, tool_name, result_content
                        )
                        logger.info(f"🔧 [NON_STREAM_PROCESSED_{i+1}] Tool: {tool_name}, Processed result length: {len(processed_result)}")
                    else:
                        processed_result = result_content
                        logger.info(f"🔧 [NON_STREAM_NO_PROCESSOR_{i+1}] Tool: {tool_name}, Using raw result")
                    
                    logger.info(f"🔧 [NON_STREAM_FINAL_RESULT_{i+1}] Tool: {tool_name}, Final result: {str(processed_result)[:500]}{'...' if len(str(processed_result)) > 500 else ''}")
                    
                    # 保存工具消息到数据库
                    if self.message_manager:
                        try:
                            tool_message_data = {
                                "session_id": self.session_id,
                                "role": "tool",
                                "content": processed_result,
                                "status": "completed",
                                "metadata": {
                                    "tool_call_id": tool_call_id,
                                    "tool_name": tool_name
                                }
                            }
                            
                            saved_tool_message = self.message_manager.save_tool_message_sync(tool_message_data)
                            logger.info(f"🔧 [NON_STREAM_SAVE_{i+1}] Saved tool message: {tool_name} (ID: {saved_tool_message.id})")
                            
                        except Exception as e:
                            logger.error(f"🔧 [NON_STREAM_SAVE_ERROR_{i+1}] Failed to save tool message: {e}")
                    
                    # 构造工具响应消息
                    tool_response_message = Message(
                        id=f"tool_msg_{tool_call_id}",
                        session_id=self.session_id,
                        role="tool",
                        content=processed_result,
                        status="completed",
                        metadata={"tool_call_id": tool_call_id, "tool_name": tool_name}
                    )
                    tool_response_messages.append(tool_response_message)
                    
                    # 构造执行结果用于前端回调
                    execute_result = {
                        "tool_call_id": tool_call_id,
                        "role": "tool",
                        "name": tool_name,
                        "result": processed_result
                    }
                    
                    logger.info(f"🔧 [NON_STREAM_CALLBACK_{i+1}] Tool: {tool_name}, Sending result to frontend")
                
                # 通知前端工具执行结果 - 包装成数组格式以匹配前端期望
                self.callback(CallbackType.ON_TOOL_RESULT, [execute_result])
            
            # 将工具响应消息添加到对话历史
            if tool_response_messages:
                logger.info(f"🔧 [TOOL_COMPLETION] Adding {len(tool_response_messages)} tool response messages to conversation")
                self.messages.extend(tool_response_messages)
            
            logger.info(f"🔧 [TOOL_EXECUTION] Completed execution of {len(tool_calls)} tool calls successfully")
                
        except Exception as e:
            logger.error(f"🔧 [TOOL_ERROR] Error executing tools: {e}")
            import traceback
            logger.error(f"🔧 [TOOL_ERROR_TRACE] Traceback: {traceback.format_exc()}")
            self.callback(CallbackType.ON_ERROR, str(e))

    def _process_ai_response(self) -> bool:
        """处理AI响应，返回是否有工具调用"""
        try:
            logger.info(f"🔧 [DEBUG] Starting AI response processing with {len(self.tools)} tools available")
            
            # 创建AI请求处理器
            self.current_ai_request_handler = AiRequestHandler(
                self.messages,
                self.tools,
                self.conversation_id,
                self.callback,
                self.model_config,
                self.config_url,
                self.session_id,
                self.message_manager
            )
            
            # 发送聊天完成请求
            updated_messages = self.current_ai_request_handler.chat_completion()
            
            # 更新消息列表
            if updated_messages:
                self.messages = updated_messages
                
                # 检查最后一条消息
                last_message = self.messages[-1] if self.messages else None
                if last_message:
                    logger.info(f"🔧 [DEBUG] Last message content: {last_message.content[:100]}...")
                    logger.info(f"🔧 [DEBUG] Last message has tool_calls: {bool(last_message.tool_calls)}")
                    
                    # 检查是否有工具调用需要执行
                    if last_message.tool_calls and len(last_message.tool_calls) > 0:
                        logger.info(f"🔧 [DEBUG] Found {len(last_message.tool_calls)} tool calls to execute")
                        return True  # 有工具调用
                    else:
                        logger.info("🔧 [DEBUG] No tool calls found, conversation completed")
                        # ai_request_handler在没有工具调用时会调用ON_COMPLETE，这里不需要重复调用
                        return False  # 没有工具调用
            
            return False  # 没有更新的消息
                    
        except Exception as e:
            import traceback
            error_details = f"Error in AI response processing: {str(e)}\nTraceback: {traceback.format_exc()}"
            logger.error(error_details)
            self.callback(CallbackType.ON_ERROR, str(e))
            return False

    def _process_chunk(self, chunk: Any, has_data: bool = False) -> str:
        """
        处理单个chunk数据，提取实际文本内容
        对应TypeScript中的processChunk方法
        """
        if not chunk or not isinstance(chunk, str):
            return str(chunk) if chunk else ""
        
        try:
            # 清理chunk数据
            clean_chunk = chunk
            if clean_chunk.startswith('data: '):
                clean_chunk = clean_chunk[6:]
            
            # 尝试解析JSON
            try:
                parsed_chunk = json.loads(clean_chunk)
                if parsed_chunk and isinstance(parsed_chunk, dict):
                    # 提取内容
                    if "content" in parsed_chunk:
                        content = parsed_chunk["content"]
                        if isinstance(content, str) and content.startswith('data: '):
                            return self._process_chunk(content, False)
                        return ("\n" + content) if has_data else content
                    elif "data" in parsed_chunk:
                        data = parsed_chunk["data"]
                        if isinstance(data, str) and data.startswith('data: '):
                            return self._process_chunk(data, True)
                        return data
                    elif "ai_stream_chunk" in parsed_chunk:
                        ai_chunk = parsed_chunk["ai_stream_chunk"]
                        if isinstance(ai_chunk, str) and ai_chunk.startswith('data: '):
                            return self._process_chunk(ai_chunk, False)
                        return ai_chunk
                        
            except json.JSONDecodeError:
                pass
                
            return chunk
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            return chunk

    def abort(self) -> None:
        """中止当前处理"""
        logger.info("🛑 [DEBUG] AiClient.abort 被调用")
        self.is_aborted = True
        if self.current_ai_request_handler:
            logger.info(f"🛑 [DEBUG] current_ai_request_handler存在，类型: {type(self.current_ai_request_handler)}")
            self.current_ai_request_handler.abort()
        else:
            logger.warning("🛑 [DEBUG] current_ai_request_handler为None，无法中止请求")

    def is_request_aborted(self) -> bool:
        """检查请求是否被中止"""
        return self.is_aborted

    def reset_abort_state(self) -> None:
        """重置中止状态"""
        self.is_aborted = False