"""
工具结果处理器
负责处理工具执行结果，生成总结和保存消息
"""
import json
import time
from typing import Dict, List, Any, Optional


class ToolResultProcessor:
    """工具结果处理器"""
    
    def __init__(self, message_manager, ai_request_handler):
        """
        初始化工具结果处理器
        
        Args:
            message_manager: 消息管理器实例
            ai_request_handler: AI请求处理器实例
        """
        self.message_manager = message_manager
        self.ai_request_handler = ai_request_handler
    
    def process_tool_results(self, 
                           tool_results: List[Dict[str, Any]], 
                           session_id: str,
                           generate_summary: bool = True) -> Dict[str, Any]:
        """
        处理工具执行结果
        
        Args:
            tool_results: 工具执行结果列表
            session_id: 会话ID
            generate_summary: 是否生成总结
            
        Returns:
            处理结果，包含保存的消息和可选的总结
        """
        try:
            saved_messages = []
            
            # 保存每个工具结果为消息
            for tool_result in tool_results:
                metadata = {
                    "toolCallId": tool_result.get("tool_call_id"),
                    "toolName": tool_result.get("name"),
                    "isError": tool_result.get("is_error", False)
                }
                
                saved_message = self.message_manager.save_tool_message(
                    session_id=session_id,
                    content=self._format_tool_result_content(tool_result),
                    metadata=metadata
                )
                saved_messages.append(saved_message)
            
            result = {
                "success": True,
                "saved_messages": saved_messages,
                "tool_results_count": len(tool_results)
            }
            
            # 生成总结（如果需要）
            if generate_summary and tool_results:
                summary = self._generate_tool_results_summary(tool_results, session_id)
                if summary:
                    result["summary"] = summary
            
            return result
            
        except Exception as e:
            error_message = f"工具结果处理失败: {str(e)}"
            print(f"Error in process_tool_results: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def _format_tool_result_content(self, tool_result: Dict[str, Any]) -> str:
        """
        格式化工具结果内容
        
        Args:
            tool_result: 工具执行结果
            
        Returns:
            格式化后的内容字符串
        """
        try:
            if tool_result.get("is_error"):
                return f"工具执行错误: {tool_result.get('content', '未知错误')}"
            
            content = tool_result.get("content", "")
            
            # 如果内容是字典或列表，转换为JSON字符串
            if isinstance(content, (dict, list)):
                return json.dumps(content, ensure_ascii=False, indent=2)
            
            return str(content)
            
        except Exception as e:
            return f"格式化工具结果失败: {str(e)}"
    
    def _generate_tool_results_summary(self, 
                                     tool_results: List[Dict[str, Any]], 
                                     session_id: str) -> Optional[str]:
        """
        生成工具结果总结
        
        Args:
            tool_results: 工具执行结果列表
            session_id: 会话ID
            
        Returns:
            总结文本，如果生成失败则返回None
        """
        try:
            # 构建总结提示
            summary_prompt = self._build_summary_prompt(tool_results)
            
            # 准备消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的工具执行结果分析师。请根据提供的工具执行结果，生成一个简洁、准确的总结。"
                },
                {
                    "role": "user",
                    "content": summary_prompt
                }
            ]
            
            # 调用AI生成总结
            response = self.ai_request_handler.handle_request(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.3,
                max_tokens=500
            )
            
            if response.get("success") and response.get("choices"):
                summary = response["choices"][0]["message"]["content"]
                return summary.strip()
            
            return None
            
        except Exception as e:
            print(f"Error generating tool results summary: {str(e)}")
            return None
    
    def _build_summary_prompt(self, tool_results: List[Dict[str, Any]]) -> str:
        """
        构建总结提示
        
        Args:
            tool_results: 工具执行结果列表
            
        Returns:
            总结提示文本
        """
        prompt_parts = ["请总结以下工具执行结果：\n"]
        
        for i, tool_result in enumerate(tool_results, 1):
            tool_name = tool_result.get("name", "未知工具")
            is_error = tool_result.get("is_error", False)
            content = tool_result.get("content", "")
            
            if is_error:
                prompt_parts.append(f"{i}. 工具 {tool_name} 执行失败：{content}")
            else:
                # 限制内容长度以避免提示过长
                if len(str(content)) > 1000:
                    content = str(content)[:1000] + "..."
                prompt_parts.append(f"{i}. 工具 {tool_name} 执行成功：{content}")
        
        prompt_parts.append("\n请提供一个简洁的总结，说明这些工具执行的主要结果和意义。")
        
        return "\n".join(prompt_parts)
    
    def process_single_tool_result(self, 
                                 tool_result: Dict[str, Any], 
                                 session_id: str) -> Dict[str, Any]:
        """
        处理单个工具执行结果
        
        Args:
            tool_result: 单个工具执行结果
            session_id: 会话ID
            
        Returns:
            处理结果
        """
        return self.process_tool_results([tool_result], session_id, generate_summary=False)
    
    def get_tool_results_statistics(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取工具结果统计信息
        
        Args:
            tool_results: 工具执行结果列表
            
        Returns:
            统计信息字典
        """
        total_count = len(tool_results)
        success_count = sum(1 for result in tool_results if not result.get("is_error", False))
        error_count = total_count - success_count
        
        tool_names = [result.get("name", "未知工具") for result in tool_results]
        unique_tools = list(set(tool_names))
        
        return {
            "total_count": total_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "unique_tools": unique_tools,
            "tool_usage": {tool: tool_names.count(tool) for tool in unique_tools}
        }