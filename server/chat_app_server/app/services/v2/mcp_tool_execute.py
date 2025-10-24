"""
MCP工具执行器
负责执行MCP工具调用，支持流式和普通调用
"""
import json
import time
from typing import Dict, List, Any, Optional, Callable


class McpToolExecute:
    """MCP工具执行器"""
    
    def __init__(self, mcp_servers=None, mcp_client=None):
        """
        初始化MCP工具执行器
        
        Args:
            mcp_servers: MCP服务器列表（与原版本兼容）
            mcp_client: MCP客户端实例（v2版本特有）
        """
        self.mcp_servers = mcp_servers or []
        self.mcp_client = mcp_client
    
    def execute_tools(self, 
                     tool_calls: List[Dict[str, Any]], 
                     on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        执行多个工具调用
        
        Args:
            tool_calls: 工具调用列表
            on_tool_result: 工具结果回调函数（用于流式处理）
            
        Returns:
            工具执行结果列表
        """
        results = []
        
        for tool_call in tool_calls:
            try:
                result = self.execute_single_tool(tool_call)
                results.append(result)
                
                # 如果有回调函数，调用它
                if on_tool_result:
                    on_tool_result(result)
                    
            except Exception as e:
                error_result = {
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "content": f"工具执行失败: {str(e)}",
                    "is_error": True
                }
                results.append(error_result)
                
                if on_tool_result:
                    on_tool_result(error_result)
        
        return results
    
    def execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个工具调用
        
        Args:
            tool_call: 工具调用信息
            
        Returns:
            工具执行结果
        """
        try:
            tool_call_id = tool_call.get("id")
            function_info = tool_call.get("function", {})
            tool_name = function_info.get("name")
            arguments_str = function_info.get("arguments", "{}")
            
            # 解析参数
            try:
                arguments = json.loads(arguments_str) if arguments_str else {}
            except json.JSONDecodeError as e:
                return {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": f"参数解析失败: {str(e)}",
                    "is_error": True
                }
            
            # 执行工具调用
            result = self._call_mcp_tool(tool_name, arguments)
            
            return {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": result,
                "is_error": False
            }
            
        except Exception as e:
            return {
                "tool_call_id": tool_call.get("id"),
                "name": tool_call.get("function", {}).get("name", "unknown"),
                "content": f"工具执行异常: {str(e)}",
                "is_error": True
            }
    
    def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            # 检查MCP客户端是否可用
            if not self.mcp_client:
                raise Exception("MCP客户端未初始化")
            
            # 调用MCP工具
            result = self.mcp_client.call_tool(tool_name, arguments)
            
            # 处理结果
            if isinstance(result, dict):
                # 如果结果是字典，检查是否有错误
                if result.get("isError"):
                    raise Exception(result.get("content", "工具执行失败"))
                return result.get("content", result)
            
            return result
            
        except Exception as e:
            raise Exception(f"MCP工具调用失败: {str(e)}")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用的工具列表
        
        Returns:
            可用工具列表
        """
        try:
            # 如果有 mcp_client，使用它获取工具
            if self.mcp_client:
                tools = self.mcp_client.list_tools()
                
                # 转换为OpenAI工具格式
                openai_tools = []
                for tool in tools:
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool.get("name"),
                            "description": tool.get("description", ""),
                            "parameters": tool.get("inputSchema", {})
                        }
                    }
                    openai_tools.append(openai_tool)
                
                return openai_tools
            
            # 如果没有 mcp_client，返回空列表（兼容模式）
            return []
            
        except Exception as e:
            print(f"Error getting available tools: {str(e)}")
            return []
    
    def validate_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证工具调用
        
        Args:
            tool_call: 工具调用信息
            
        Returns:
            验证结果，包含is_valid和error_message
        """
        try:
            # 检查必需字段
            if not tool_call.get("id"):
                return {
                    "is_valid": False,
                    "error_message": "缺少工具调用ID"
                }
            
            function_info = tool_call.get("function", {})
            if not function_info.get("name"):
                return {
                    "is_valid": False,
                    "error_message": "缺少工具名称"
                }
            
            # 验证参数格式
            arguments_str = function_info.get("arguments", "{}")
            try:
                json.loads(arguments_str)
            except json.JSONDecodeError:
                return {
                    "is_valid": False,
                    "error_message": "工具参数格式无效"
                }
            
            # 检查工具是否存在
            available_tools = self.get_available_tools()
            tool_names = [tool["function"]["name"] for tool in available_tools]
            
            if function_info["name"] not in tool_names:
                return {
                    "is_valid": False,
                    "error_message": f"工具 '{function_info['name']}' 不存在"
                }
            
            return {
                "is_valid": True,
                "error_message": None
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "error_message": f"验证失败: {str(e)}"
            }
    
    def execute_tools_with_validation(self, 
                                    tool_calls: List[Dict[str, Any]], 
                                    on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        执行工具调用（带验证）
        
        Args:
            tool_calls: 工具调用列表
            on_tool_result: 工具结果回调函数
            
        Returns:
            工具执行结果列表
        """
        results = []
        
        for tool_call in tool_calls:
            # 验证工具调用
            validation = self.validate_tool_call(tool_call)
            
            if not validation["is_valid"]:
                error_result = {
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "content": validation["error_message"],
                    "is_error": True
                }
                results.append(error_result)
                
                if on_tool_result:
                    on_tool_result(error_result)
                continue
            
            # 执行工具调用
            try:
                result = self.execute_single_tool(tool_call)
                results.append(result)
                
                if on_tool_result:
                    on_tool_result(result)
                    
            except Exception as e:
                error_result = {
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "content": f"工具执行失败: {str(e)}",
                    "is_error": True
                }
                results.append(error_result)
                
                if on_tool_result:
                    on_tool_result(error_result)
        
        return results
    
    def get_tool_execution_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取工具执行统计信息
        
        Args:
            results: 工具执行结果列表
            
        Returns:
            统计信息
        """
        total_count = len(results)
        success_count = sum(1 for result in results if not result.get("is_error", False))
        error_count = total_count - success_count
        
        return {
            "total_count": total_count,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / total_count if total_count > 0 else 0
        }