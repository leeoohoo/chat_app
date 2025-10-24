"""
AI客户端
负责协调AI请求和工具调用的递归处理
"""
import time
from typing import Dict, List, Any, Optional, Callable


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
        self.max_iterations = 10  # 最大递归次数，防止无限循环
    
    def process_request(self, 
                       messages: List[Dict[str, Any]], 
                       session_id: str,
                       model: str = "gpt-4",
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       on_chunk: Optional[Callable[[str], None]] = None,
                       on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        处理AI请求，包括工具调用的递归处理
        
        Args:
            messages: 消息列表
            session_id: 会话ID
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大token数
            on_chunk: 流式响应回调
            on_tool_result: 工具结果回调
            
        Returns:
            处理结果
        """
        try:
            # 获取可用工具
            available_tools = self.mcp_tool_execute.get_available_tools()
            
            # 准备API消息格式
            api_messages = self.ai_request_handler.prepare_messages_for_api(messages)
            
            # 开始递归处理
            result = self._process_with_tools(
                api_messages=api_messages,
                tools=available_tools,
                session_id=session_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                on_chunk=on_chunk,
                on_tool_result=on_tool_result,
                iteration=0
            )
            
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
                           on_tool_result: Optional[Callable[[Dict[str, Any]], None]],
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
            on_tool_result: 工具结果回调
            iteration: 当前迭代次数
            
        Returns:
            处理结果
        """
        # 检查迭代次数限制
        if iteration >= self.max_iterations:
            return {
                "success": False,
                "error": f"达到最大迭代次数限制 ({self.max_iterations})",
                "final_response": None
            }
        
        try:
            # 发送AI请求
            ai_response = self.ai_request_handler.handle_request(
                messages=api_messages,
                tools=tools if tools else None,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                session_id=session_id,
                on_chunk=on_chunk
            )
            
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
            
            if not tool_calls:
                # 没有工具调用，返回最终结果
                return {
                    "success": True,
                    "final_response": ai_response,
                    "iterations": iteration + 1,
                    "has_tool_calls": False
                }
            
            # 执行工具调用
            tool_results = self.mcp_tool_execute.execute_tools_with_validation(
                tool_calls=tool_calls,
                on_tool_result=on_tool_result
            )
            
            # 处理工具结果
            tool_processing_result = self.tool_result_processor.process_tool_results(
                tool_results=tool_results,
                session_id=session_id,
                generate_summary=False  # 在递归过程中不生成总结
            )
            
            if not tool_processing_result.get("success"):
                return {
                    "success": False,
                    "error": f"工具结果处理失败: {tool_processing_result.get('error')}",
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
            return self._process_with_tools(
                api_messages=updated_messages,
                tools=tools,
                session_id=session_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                on_chunk=on_chunk,
                on_tool_result=on_tool_result,
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
                              max_tokens: Optional[int] = None) -> Dict[str, Any]:
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
            api_messages = self.ai_request_handler.prepare_messages_for_api(messages)
            
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