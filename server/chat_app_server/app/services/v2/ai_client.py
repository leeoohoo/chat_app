"""
AI客户端
负责协调AI请求和工具调用的递归处理
"""
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from .conversation_summarizer import ConversationSummarizer
from .ai_request_handler import AiRequestHandler


class AiClient:
    """AI客户端，协调AI请求和工具调用"""
    
    def __init__(self, 
                 ai_request_handler, 
                 mcp_tool_execute, 
                 tool_result_processor, 
                 message_manager):
        """
        初始化AI客户端
        
        Args:
            ai_request_handler: AI请求处理器
            mcp_tool_execute: MCP工具执行器
            tool_result_processor: 工具结果处理器
            message_manager: 消息管理器
        """
        self.ai_request_handler = ai_request_handler
        self.mcp_tool_execute = mcp_tool_execute
        self.tool_result_processor = tool_result_processor
        self.message_manager = message_manager
        self.max_iterations = 25  # 最大递归次数，防止无限循环
        # 对话摘要相关配置
        self.summary_threshold = 6  # 当消息条数超过该阈值时触发摘要
        self.summary_keep_last_n = 2  # 摘要后保留最近N条原始消息（默认保留最近2条）
        self.summary_max_tokens = 30000  # 摘要生成的最大token数
        # 历史消息与系统提示配置（可配置）
        self.history_limit = 2  # 默认只取最近2条历史
        self.default_system_prompt: Optional[str] = None  # 默认系统提示（所有模式均可注入）
        # 摘要器：使用一个全新的 AiRequestHandler 实例，避免与主请求处理互相影响
        try:
            summarizer_handler = AiRequestHandler(
                openai_client=self.ai_request_handler.openai_client,
                message_manager=self.message_manager
            )
        except Exception as e:
            print(f"[AI_CLIENT] 创建摘要专用处理器失败，降级使用主处理器: {e}")
            summarizer_handler = self.ai_request_handler

        self.conversation_summarizer = ConversationSummarizer(
            ai_request_handler=summarizer_handler,
            message_manager=self.message_manager
        )

    def set_history_limit(self, limit: int) -> None:
        """设置加载历史消息的条数（>0）"""
        if isinstance(limit, int) and limit > 0:
            self.history_limit = limit

    def set_system_prompt(self, prompt: Optional[str]) -> None:
        """设置默认系统提示（所有模式都可注入）"""
        self.default_system_prompt = prompt
    
    def process_request(self, 
                       messages: List[Dict[str, Any]], 
                       session_id: str,
                       model: str = "gpt-4",
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       on_chunk: Optional[Callable[[str], None]] = None,
                       system_prompt: Optional[str] = None,
                       history_limit: Optional[int] = None,
                       on_tools_start: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
                       on_tools_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
                       on_tools_end: Optional[Callable[[List[Dict[str, Any]]], None]] = None) -> Dict[str, Any]:
        """
        处理AI请求，包括工具调用的递归处理
        
        Args:
            messages: 消息列表
            session_id: 会话ID
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大token数
            on_chunk: 流式响应回调
            on_tools_start: 工具开始调用回调
            on_tools_stream: 工具流式内容回调
            on_tools_end: 工具结束回调
            
        Returns:
            处理结果
        """
        print(f"[AI_CLIENT] 开始处理请求 - 会话ID: {session_id}, 模型: {model}, 消息数: {len(messages)}")
        
        try:
            # 获取可用工具
            available_tools = self.mcp_tool_execute.get_available_tools()
            print(f"[AI_CLIENT] 获取到可用工具数量: {len(available_tools)}")
            
            # 1) 加载历史上下文（从数据库）
            history_messages = []
            try:
                # 可配置历史条数（参数优先，其次实例默认值）
                hist_limit = history_limit if isinstance(history_limit, int) and history_limit > 0 else self.history_limit
                history_messages = self.message_manager.get_session_messages(session_id=session_id, limit=hist_limit) or []
            except Exception as e:
                print(f"[AI_CLIENT] 加载历史消息失败: {e}")

            # 2) 归一化系统提示并合并历史与当前消息（去重 system，保证 system 位于最前）
            combined_messages: List[Dict[str, Any]] = []
            # 收集输入中的系统消息内容（历史与当前）
            system_candidates: List[str] = []
            for src in (messages or []):
                if isinstance(src, dict) and src.get("role") == "system":
                    content = src.get("content")
                    if content:
                        system_candidates.append(str(content))
            for src in (history_messages or []):
                if isinstance(src, dict) and src.get("role") == "system":
                    content = src.get("content")
                    if content:
                        system_candidates.append(str(content))

            eff_system_prompt_input = system_prompt if system_prompt is not None else self.default_system_prompt
            eff_system_prompt = eff_system_prompt_input if eff_system_prompt_input else (system_candidates[0] if system_candidates else None)
            if eff_system_prompt:
                combined_messages.append({"role": "system", "content": eff_system_prompt})

            # 历史消息（跳过 system，统一结构）
            for msg in (history_messages or []):
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role")
                if not role or role == "system":
                    continue
                combined_messages.append({
                    "role": role,
                    "content": msg.get("content", ""),
                    "metadata": msg.get("metadata") or {}
                })

            # 当前消息（跳过 system，统一结构）
            for cur in (messages or []):
                if not isinstance(cur, dict):
                    continue
                role = cur.get("role")
                if not role or role == "system":
                    continue
                combined_messages.append({
                    "role": role,
                    "content": cur.get("content", ""),
                    "metadata": cur.get("metadata") or {}
                })

            api_messages = self.ai_request_handler.prepare_messages_for_api(combined_messages)
            
            # 开始递归处理
            result = self._process_with_tools(
                api_messages=api_messages,
                tools=available_tools,
                session_id=session_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                on_chunk=on_chunk,
                system_prompt=eff_system_prompt,
                on_tools_start=on_tools_start,
                on_tools_stream=on_tools_stream,
                on_tools_end=on_tools_end,
                iteration=0
            )
            
            print(f"[AI_CLIENT] 请求处理完成 - 会话ID: {session_id}, 成功: {result.get('success', False)}, 迭代次数: {result.get('iterations', 0)}")
            return result
            
        except Exception as e:
            error_message = f"AI请求处理失败: {str(e)}"
            print(f"Error in process_request: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def _process_with_tools(self, 
                           api_messages: List[Dict[str, Any]], 
                           tools: List[Dict[str, Any]],
                           session_id: str,
                           model: str,
                           temperature: float,
                           max_tokens: Optional[int],
                           on_chunk: Optional[Callable[[str], None]],
                           system_prompt: Optional[str],
                           on_tools_start: Optional[Callable[[List[Dict[str, Any]]], None]],
                           on_tools_stream: Optional[Callable[[Dict[str, Any]], None]],
                           on_tools_end: Optional[Callable[[List[Dict[str, Any]]], None]],
                           iteration: int) -> Dict[str, Any]:
        """
        递归处理AI请求和工具调用
        
        Args:
            api_messages: API格式的消息列表
            tools: 可用工具列表
            session_id: 会话ID
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            on_chunk: 流式回调
            on_tools_start: 工具开始调用回调
            on_tools_stream: 工具流式内容回调
            on_tools_end: 工具结束回调
            iteration: 当前迭代次数
            
        Returns:
            处理结果
        """
        # 添加方法入口日志
        print(f"[AI_CLIENT] 进入_process_with_tools - 会话ID: {session_id}, 迭代: {iteration}, 消息数: {len(api_messages)}")
        
        # 检查迭代次数限制
        if iteration >= self.max_iterations:
            print(f"[AI_CLIENT] 达到最大迭代次数限制 - 会话ID: {session_id}, 当前迭代: {iteration}, 最大限制: {self.max_iterations}")
            return {
                "success": False,
                "error": f"达到最大迭代次数限制 ({self.max_iterations})",
                "final_response": None
            }
        
        try:
            # 当消息过长时，先进行摘要
            if len(api_messages) > self.summary_threshold:
                print(f"[AI_CLIENT] 触发对话摘要 - 会话ID: {session_id}, 当前消息数: {len(api_messages)}, 阈值: {self.summary_threshold}")
                summary_text = self.conversation_summarizer.summarize(
                    api_messages=api_messages,
                    session_id=session_id,
                    model=model,
                    temperature=max(0.3, temperature - 0.2),  # 摘要用更稳定的温度
                    max_tokens=self.summary_max_tokens,
                    on_chunk=on_chunk
                )

                if summary_text:
                    print(f"[AI_CLIENT] 摘要成功，长度: {len(summary_text)} - 会话ID: {session_id}")
                    # 用摘要开启新对话：保留系统提示，摘要作为助手消息，仅追加本次用户消息，其余清除
                    next_messages: List[Dict[str, Any]] = []
                    # 直接从当前消息中抽取系统提示（置顶且唯一）
                    extracted_system: Optional[str] = None
                    for m in (api_messages or []):
                        if isinstance(m, dict) and m.get("role") == "system":
                            c = m.get("content")
                            if c:
                                extracted_system = str(c)
                                break
                    if extracted_system:
                        next_messages.append({
                            "role": "system",
                            "content": extracted_system
                        })
                    # 合并摘要与本次用户消息为单条用户消息
                    last_user_content: Optional[str] = None
                    for m in reversed(api_messages or []):
                        if isinstance(m, dict) and m.get("role") == "user":
                            last_user_content = m.get("content", "")
                            break
                    merged_user_lines = ["对话摘要：", summary_text or ""]
                    if last_user_content:
                        merged_user_lines.extend(["", "用户请求：", last_user_content])
                    merged_user_content = "\n".join(merged_user_lines).strip()
                    next_messages.append({
                        "role": "user",
                        "content": merged_user_content
                    })
                    api_messages = next_messages

                    # 清理该会话的缓存历史（优先会话级清理）
                    try:
                        if hasattr(self.message_manager, "clear_cache_for_session"):
                            self.message_manager.clear_cache_for_session(session_id)
                            print(f"[AI_CLIENT] 已清理会话缓存 - 会话ID: {session_id}")
                        elif hasattr(self.message_manager, "clear_cache"):
                            self.message_manager.clear_cache()
                            print(f"[AI_CLIENT] 已清理全局消息缓存 - 会话ID: {session_id}")
                    except Exception as ce:
                        print(f"[AI_CLIENT] 清理缓存失败: {ce}")
                else:
                    print(f"[AI_CLIENT] 摘要失败或无内容，继续使用原始消息 - 会话ID: {session_id}")

            # 发送AI请求
            print(f"[AI_CLIENT] 发送AI请求 - 会话ID: {session_id}, 迭代: {iteration}, 模型: {model}")
            
            ai_response = self.ai_request_handler.handle_request(
                messages=api_messages,
                tools=tools if tools else None,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                session_id=session_id,
                on_chunk=on_chunk
            )
            
            print(f"[AI_CLIENT] AI请求完成 - 会话ID: {session_id}, 迭代: {iteration}, 成功: {ai_response.get('success', False)}")
            
            if not ai_response.get("success"):
                return {
                    "success": False,
                    "error": ai_response.get("error", "AI请求失败"),
                    "final_response": None
                }
            
            # 检查是否有工具调用
            choice = ai_response.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls")
            
            print(f"[AI_CLIENT] 检查工具调用 - 会话ID: {session_id}, 迭代: {iteration}, 有工具调用: {bool(tool_calls)}")
            
            if not tool_calls:
                # 没有工具调用，返回最终结果
                print(f"[AI_CLIENT] 无工具调用，返回最终结果 - 会话ID: {session_id}, 迭代: {iteration}")
                return {
                    "success": True,
                    "final_response": ai_response,
                    "iterations": iteration + 1,
                    "has_tool_calls": False
                }
            
            # 工具调用开始回调和延迟
            print(f"[AI_CLIENT] 开始执行工具调用 - 会话ID: {session_id}, 迭代: {iteration}, 工具数量: {len(tool_calls)}")
            print(f"[AI_CLIENT] 工具调用详情: {[tc.get('function', {}).get('name', 'unknown') for tc in tool_calls]}")
            
            # 详细记录每个工具调用的结构
            for i, tool_call in enumerate(tool_calls):
                print(f"[AI_CLIENT] 工具调用 #{i+1}:")
                print(f"  - ID: {tool_call.get('id', 'N/A')}")
                print(f"  - Type: {tool_call.get('type', 'N/A')}")
                if 'function' in tool_call:
                    func_info = tool_call['function']
                    print(f"  - Function Name: {func_info.get('name', 'N/A')}")
                    print(f"  - Arguments: {func_info.get('arguments', 'N/A')}")
                else:
                    print(f"  - 完整结构: {tool_call}")
            
            # 调用工具开始回调
            if on_tools_start:
                try:
                    on_tools_start(tool_calls)
                    print(f"[AI_CLIENT] 工具开始回调已调用 - 会话ID: {session_id}, 迭代: {iteration}")
                except Exception as e:
                    print(f"[AI_CLIENT] 工具开始回调错误: {e}")
            
            # 工具开始前延迟1秒
            print(f"[AI_CLIENT] 工具开始前延迟1秒 - 会话ID: {session_id}, 迭代: {iteration}")
            time.sleep(1)
            
            # 执行工具调用
            tool_results = self.mcp_tool_execute.execute_tools_with_validation(
                tool_calls=tool_calls,
                on_tool_stream=on_tools_stream
            )

            print(f"[AI_CLIENT] 工具执行完成 - 会话ID: {session_id}, 迭代: {iteration}, 结果数量: {len(tool_results)}")

            # 工具结束前延迟1秒
            print(f"[AI_CLIENT] 工具结束前延迟1秒 - 会话ID: {session_id}, 迭代: {iteration}")
            time.sleep(1)
            
            # 调用工具结束回调
            if on_tools_end:
                try:
                    on_tools_end(tool_results)
                    print(f"[AI_CLIENT] 工具结束回调已调用 - 会话ID: {session_id}, 迭代: {iteration}")
                except Exception as e:
                    print(f"[AI_CLIENT] 工具结束回调错误: {e}")

            # 处理工具结果
            print(f"[AI_CLIENT] 开始处理工具结果 - 会话ID: {session_id}, 迭代: {iteration}")
            print(f"[AI_CLIENT] 工具结果概览: {[{'tool_name': tr.get('name', 'unknown'), 'success': tr.get('success', False)} for tr in tool_results]}")
            
            # 详细的工具结果日志
            for i, tr in enumerate(tool_results):
                print(f"[AI_CLIENT] 工具结果 {i+1}: {{'tool_call_id': '{tr.get('tool_call_id', 'unknown')}', 'tool_name': '{tr.get('name', 'unknown')}', 'success': {tr.get('success', False)}, 'content_length': {len(str(tr.get('content', '')))}}}")
                if not tr.get('success', False) and tr.get('error'):
                    print(f"[AI_CLIENT] 工具错误详情: {tr.get('error', 'No error details')}")
            
            tool_processing_result = self.tool_result_processor.process_tool_results(
                tool_results=tool_results,
                session_id=session_id,
                generate_summary=False  # 在递归过程中不生成总结
            )
            
            print(f"[AI_CLIENT] 工具结果处理完成 - 会话ID: {session_id}, 迭代: {iteration}, 处理结果: {tool_processing_result.get('success', False)}")
            
            if not tool_processing_result.get("success"):
                error_msg = tool_processing_result.get('error', 'Unknown error')
                print(f"[AI_CLIENT] 工具结果处理失败 - 会话ID: {session_id}, 迭代: {iteration}, 错误: {error_msg}")
                return {
                    "success": False,
                    "error": f"工具结果处理失败: {error_msg}",
                    "final_response": ai_response
                }
            
            # 将工具结果添加到消息列表
            updated_messages = api_messages.copy()
            
            # 添加助手消息（包含工具调用）
            updated_messages.append({
                "role": "assistant",
                "content": message.get("content", ""),
                "tool_calls": tool_calls
            })
            
            # 添加工具结果消息
            for tool_result in tool_results:
                updated_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["tool_call_id"],
                    "content": str(tool_result["content"])
                })
            
            # 递归调用处理下一轮
            print(f"[AI_CLIENT] 准备递归调用 - 会话ID: {session_id}, 当前迭代: {iteration}, 下一迭代: {iteration + 1}")
            print(f"[AI_CLIENT] 更新后消息数: {len(updated_messages)}")
            
            return self._process_with_tools(
                api_messages=updated_messages,
                tools=tools,
                session_id=session_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                on_chunk=on_chunk,
                system_prompt=system_prompt,
                on_tools_start=on_tools_start,
                on_tools_stream=on_tools_stream,
                on_tools_end=on_tools_end,
                iteration=iteration + 1
            )
            
        except Exception as e:
            error_message = f"工具处理迭代失败 (iteration {iteration}): {str(e)}"
            print(f"Error in _process_with_tools: {error_message}")
            return {
                "success": False,
                "error": error_message,
                "final_response": None,
                "iteration": iteration
            }

    def process_simple_request(self, 
                              messages: List[Dict[str, Any]], 
                              session_id: str,
                              model: str = "gpt-4",
                              temperature: float = 0.7,
                              max_tokens: Optional[int] = None,
                              system_prompt: Optional[str] = None,
                              history_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        处理简单AI请求（不使用工具）
        
        Args:
            messages: 消息列表
            session_id: 会话ID
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            AI响应结果
        """
        try:
            # 注入系统提示与历史消息（归一化：system 置顶、去重）
            combined_messages: List[Dict[str, Any]] = []

            # 历史消息（可配置条数）
            history_messages: List[Dict[str, Any]] = []
            try:
                hist_limit = history_limit if isinstance(history_limit, int) and history_limit > 0 else self.history_limit
                history_messages = self.message_manager.get_session_messages(session_id=session_id, limit=hist_limit) or []
            except Exception as e:
                print(f"[AI_CLIENT] 简单模式加载历史失败: {e}")

            # 归一化系统提示
            system_candidates: List[str] = []
            for src in (messages or []):
                if isinstance(src, dict) and src.get("role") == "system":
                    c = src.get("content")
                    if c:
                        system_candidates.append(str(c))
            for src in (history_messages or []):
                if isinstance(src, dict) and src.get("role") == "system":
                    c = src.get("content")
                    if c:
                        system_candidates.append(str(c))
            eff_system_prompt_input = system_prompt if system_prompt is not None else self.default_system_prompt
            eff_system_prompt = eff_system_prompt_input if eff_system_prompt_input else (system_candidates[0] if system_candidates else None)
            if eff_system_prompt:
                combined_messages.append({"role": "system", "content": eff_system_prompt})

            # 合并历史（跳过 system）
            for msg in (history_messages or []):
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role")
                if not role or role == "system":
                    continue
                combined_messages.append({
                    "role": role,
                    "content": msg.get("content", ""),
                    "metadata": msg.get("metadata") or {}
                })

            # 合并当前（跳过 system）
            for cur in (messages or []):
                if not isinstance(cur, dict):
                    continue
                role = cur.get("role")
                if not role or role == "system":
                    continue
                combined_messages.append({
                    "role": role,
                    "content": cur.get("content", ""),
                    "metadata": cur.get("metadata") or {}
                })

            api_messages = self.ai_request_handler.prepare_messages_for_api(combined_messages)
            
            response = self.ai_request_handler.handle_request(
                messages=api_messages,
                tools=None,  # 不使用工具
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                session_id=session_id
            )
            
            return response
            
        except Exception as e:
            error_message = f"简单AI请求处理失败: {str(e)}"
            print(f"Error in process_simple_request: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_conversation_context(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取会话上下文
        
        Args:
            session_id: 会话ID
            limit: 消息数量限制
            
        Returns:
            消息列表
        """
        try:
            # 这里应该从数据库获取消息，暂时返回空列表
            # 实际实现需要调用数据库服务
            return []
            
        except Exception as e:
            print(f"Error getting conversation context: {str(e)}")
            return []
    
    def set_max_iterations(self, max_iterations: int) -> None:
        """
        设置最大迭代次数
        
        Args:
            max_iterations: 最大迭代次数
        """
        if max_iterations > 0:
            self.max_iterations = max_iterations
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "max_iterations": self.max_iterations,
            "available_tools_count": len(self.mcp_tool_execute.get_available_tools()),
            "message_cache_stats": self.message_manager.get_cache_stats()
        }