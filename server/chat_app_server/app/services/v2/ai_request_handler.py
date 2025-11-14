"""
AI请求处理器
负责处理AI请求和响应，使用OpenAI客户端
"""
import json
import time
from typing import Dict, List, Any, Optional, Callable
from openai import OpenAI


class AiRequestHandler:
    """AI请求处理器"""
    
    def __init__(self, openai_client: OpenAI, message_manager):
        """
        初始化AI请求处理器
        
        Args:
            openai_client: OpenAI客户端实例
            message_manager: 消息管理器实例
        """
        self.openai_client = openai_client
        self.message_manager = message_manager
    
    def handle_request(self, 
                      messages: List[Dict[str, Any]], 
                      tools: Optional[List[Dict[str, Any]]] = None,
                      model: str = "gpt-4",
                      temperature: float = 0.7,
                      max_tokens: Optional[int] = None,
                      session_id: Optional[str] = None,
                      on_chunk: Optional[Callable[[str], None]] = None,
                      on_thinking_chunk: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        处理AI请求
        
        Args:
            messages: 消息列表
            tools: 可用工具列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大token数
            session_id: 会话ID
            on_chunk: 流式响应回调函数
            
        Returns:
            AI响应结果
        """
        try:
            # 准备请求参数
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
                
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            # 如果有流式回调，使用流式请求
            if on_chunk:
                return self._handle_stream_request(request_params, session_id, on_chunk, on_thinking_chunk)
            else:
                return self._handle_normal_request(request_params, session_id)
                
        except Exception as e:
            error_message = f"AI请求处理失败: {str(e)}"
            print(f"Error in handle_request: {error_message}")
            return {
                "error": error_message,
                "success": False
            }
    
    def _handle_normal_request(self, request_params: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """
        处理普通（非流式）AI请求
        
        Args:
            request_params: 请求参数
            session_id: 会话ID
            
        Returns:
            AI响应结果
        """
        try:
            response = self.openai_client.chat.completions.create(**request_params)
            
            choice = response.choices[0]
            message = choice.message
            
            # 构建响应数据
            # 提取可能存在的推理内容（不同模型字段可能不同）
            reasoning_text = None
            try:
                if hasattr(message, "reasoning_content") and message.reasoning_content:
                    reasoning_text = message.reasoning_content
                elif hasattr(message, "reasoning") and message.reasoning:
                    # 某些 SDK 将其命名为 reasoning
                    reasoning_text = message.reasoning
            except Exception:
                reasoning_text = None

            response_data = {
                "id": response.id,
                "model": response.model,
                "created": response.created,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "choices": [{
                    "index": choice.index,
                    "message": {
                        "role": message.role,
                        "content": message.content,
                        # 将推理内容一并返回（接口统一为 reasoning）
                        "reasoning": reasoning_text or ""
                    },
                    "finish_reason": choice.finish_reason
                }],
                "success": True
            }
            
            # 处理工具调用
            if message.tool_calls:
                response_data["choices"][0]["message"]["tool_calls"] = []
                for tool_call in message.tool_calls:
                    response_data["choices"][0]["message"]["tool_calls"].append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            # 保存助手消息到数据库
            if session_id and self.message_manager:
                metadata = {}
                if message.tool_calls:
                    metadata["toolCalls"] = response_data["choices"][0]["message"]["tool_calls"]
                
                self.message_manager.save_assistant_message(
                    session_id=session_id,
                    content=message.content or "",
                    reasoning=reasoning_text or None,
                    metadata=metadata if metadata else None
                )
            
            return response_data
            
        except Exception as e:
            error_message = f"普通AI请求失败: {str(e)}"
            print(f"Error in _handle_normal_request: {error_message}")
            return {
                "error": error_message,
                "success": False
            }
    
    def _handle_stream_request(self, 
                              request_params: Dict[str, Any], 
                              session_id: Optional[str],
                              on_chunk: Callable[[str], None],
                              on_thinking_chunk: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        处理流式AI请求
        
        Args:
            request_params: 请求参数
            session_id: 会话ID
            on_chunk: 流式响应回调函数
            
        Returns:
            AI响应结果
        """
        try:
            request_params["stream"] = True
            
            response = self.openai_client.chat.completions.create(**request_params)
            
            # 收集流式响应数据
            collected_content = ""
            collected_tool_calls = []
            collected_reasoning_content = ""
            response_id = None
            model = None
            created = None
            usage = None
            finish_reason = None
            
            for chunk in response:
                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    # 收集基本信息
                    if not response_id and chunk.id:
                        response_id = chunk.id
                    if not model and chunk.model:
                        model = chunk.model
                    if not created and chunk.created:
                        created = chunk.created
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage = chunk.usage
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                    
                    # 处理内容
                    if delta.content:
                        collected_content += delta.content
                        # 调用流式回调
                        on_chunk(delta.content)

                    # 处理推理内容（仅部分模型返回）
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        collected_reasoning_content += delta.reasoning_content
                        if on_thinking_chunk:
                            try:
                                on_thinking_chunk(delta.reasoning_content)
                            except Exception:
                                # 回调失败不影响主流程
                                pass
                    
                    # 处理工具调用
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            # 确保有足够的工具调用槽位
                            while len(collected_tool_calls) <= tool_call.index:
                                collected_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            
                            if tool_call.id:
                                collected_tool_calls[tool_call.index]["id"] = tool_call.id
                            if tool_call.function:
                                if tool_call.function.name:
                                    collected_tool_calls[tool_call.index]["function"]["name"] = tool_call.function.name
                                if tool_call.function.arguments:
                                    collected_tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
            
            # 构建最终响应
            response_data = {
                "id": response_id,
                "model": model,
                "created": created,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0
                },
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": collected_content,
                        "reasoning": collected_reasoning_content
                    },
                    "finish_reason": finish_reason
                }],
                "success": True
            }
            
            # 添加工具调用
            if collected_tool_calls:
                response_data["choices"][0]["message"]["tool_calls"] = collected_tool_calls
            
            # 保存助手消息到数据库
            if session_id and self.message_manager:
                metadata = {}
                if collected_tool_calls:
                    metadata["toolCalls"] = collected_tool_calls
                
                self.message_manager.save_assistant_message(
                    session_id=session_id,
                    content=collected_content,
                    reasoning=collected_reasoning_content or None,
                    metadata=metadata if metadata else None
                )
            
            return response_data
            
        except Exception as e:
            error_message = f"流式AI请求失败: {str(e)}"
            print(f"Error in _handle_stream_request: {error_message}")
            return {
                "error": error_message,
                "success": False
            }
    
    def prepare_messages_for_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为API调用准备消息格式
        
        Args:
            messages: 原始消息列表
            
        Returns:
            格式化后的消息列表
        """
        api_messages = []
        
        for message in messages:
            # 防御性检查：跳过None或非字典消息
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content", "")
            if role is None:
                # 没有角色的消息不参与API调用
                continue
            api_message = {
                "role": role,
                "content": content
            }
            
            # 处理工具调用
            metadata = message.get("metadata") or {}
            if isinstance(metadata, dict) and metadata.get("toolCalls"):
                api_message["tool_calls"] = metadata["toolCalls"]
            
            # 处理工具调用ID（用于tool角色消息）
            if role == "tool" and isinstance(metadata, dict) and metadata.get("toolCallId"):
                api_message["tool_call_id"] = metadata["toolCallId"]
            
            api_messages.append(api_message)
        
        return api_messages