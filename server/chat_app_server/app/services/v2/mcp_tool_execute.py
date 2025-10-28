"""
MCP工具执行器
负责执行MCP工具调用，支持流式和普通调用
"""
import json
import time
import requests
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from mcp_framework.client.simple import SimpleClient
import aiohttp

# 导入配置读取工具
from ...utils.config_reader import get_config_dir




class McpToolExecute:
    """MCP工具执行器"""

    def __init__(self, mcp_servers=None, stdio_mcp_servers=None, config_dir=None):
        """
        初始化MCP工具执行器

        Args:
            mcp_servers: HTTP MCP服务器列表，格式: [{"name": "server_name", "url": "http://..."}]
            stdio_mcp_servers: stdio MCP服务器列表，格式: [{"name": "server_name", "command": "...", "alias": "...", "args": [...], "env": {...}}]
            config_dir: 配置目录路径，用于 stdio 服务器
        """
        self.mcp_servers = mcp_servers or []
        self.stdio_mcp_servers = stdio_mcp_servers or []
        # 使用全局配置目录，如果没有传入 config_dir 则从配置文件读取
        self.config_dir = get_config_dir()
        self.tools = []
        self.tool_metadata = {}
        self.session = requests.Session()
        self.session.timeout = 30

        # 存储 stdio 客户端连接
        self.stdio_clients = {}

    def init(self):
        """初始化，构建工具列表"""
        self.build_tools()

    def build_tools(self):
        """
        构建工具列表
        支持 HTTP 和 stdio 两种类型的 MCP 服务器
        """
        try:
            self.tools = []
            self.tool_metadata = {}

            # 处理 HTTP 类型的 MCP 服务器
            for mcp_server in self.mcp_servers:
                try:
                    server_name = mcp_server.get("name")
                    server_url = mcp_server.get("url")

                    if not server_name or not server_url:
                        # print(f"跳过无效的 HTTP 服务器配置: {mcp_server}")
                        continue

                    # 调用 MCP 服务获取 tools - 使用标准的 MCP 协议
                    request_data = {
                        "jsonrpc": "2.0",
                        "id": f"req_{int(time.time() * 1000)}_{hash(server_name) % 10000}",
                        "method": "tools/list",
                        "params": {}
                    }

                    # print(f"获取 HTTP MCP 服务器 {server_name} 的工具列表: {server_url}")
                    response = self.session.post(server_url, json=request_data)
                    response.raise_for_status()

                    response_data = response.json()

                    if response_data.get("error"):
                        raise Exception(f"MCP tools/list 失败: {response_data['error'].get('message', '未知错误')}")

                    # 获取工具列表
                    tools_result = response_data.get("result", {})
                    tools_list = tools_result.get("tools", [])

                    # print(f"从 HTTP 服务器 {server_name} 获取到 {len(tools_list)} 个工具")

                    # 处理每个工具
                    for tool in tools_list:
                        tool_name = tool.get("name")
                        if not tool_name:
                            continue

                        # 为工具名称添加服务器前缀以避免冲突
                        prefixed_tool_name = f"{server_name}_{tool_name}"

                        # 存储工具元数据
                        self.tool_metadata[prefixed_tool_name] = {
                            "original_name": tool_name,
                            "server_name": server_name,
                            "server_url": server_url,
                            "server_type": "http",
                            "tool_info": tool
                        }

                        # 转换为 OpenAI 工具格式
                        openai_tool = {
                            "type": "function",
                            "function": {
                                "name": prefixed_tool_name,
                                "description": tool.get("description", ""),
                                "parameters": tool.get("inputSchema", {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                })
                            }
                        }

                        self.tools.append(openai_tool)

                except Exception as e:
                    # print(f"获取 HTTP 服务器 {mcp_server.get('name', 'unknown')} 工具列表失败: {e}")
                    continue

            # 处理 stdio 类型的 MCP 服务器
            for stdio_server in self.stdio_mcp_servers:
                try:
                    server_name = stdio_server.get("name")
                    server_command = stdio_server.get("command")
                    server_alias = stdio_server.get("alias")

                    if not server_name or not server_command:
                        # print(f"跳过无效的 stdio 服务器配置: {stdio_server}")
                        continue

                    # print(f"获取 stdio MCP 服务器 {server_name} 的工具列表")

                    # 异步获取工具列表
                    async def get_stdio_tools():
                        # 使用临时客户端获取工具列表
                        async with SimpleClient(
                            server_script=server_command,
                            alias=server_alias,
                            config_dir=self.config_dir
                        ) as client:
                            # 获取工具对象列表（直接返回 Tool 对象）
                            tools_list = await client.list_tools()
                            return tools_list

                    # 运行异步函数
                    tools_list = asyncio.run(get_stdio_tools())

                    # print(f"从 stdio 服务器 {server_name} 获取到 {len(tools_list)} 个工具")

                    # 处理每个工具
                    for tool in tools_list:
                        if tool is None:
                            continue

                        tool_name = tool.name
                        if not tool_name:
                            continue

                        # 为工具名称添加服务器前缀以避免冲突
                        prefixed_tool_name = f"{server_name}_{tool_name}"

                        # 存储工具元数据
                        self.tool_metadata[prefixed_tool_name] = {
                            "original_name": tool_name,
                            "server_name": server_name,
                            "server_script": server_command,
                            "server_alias": server_alias,
                            "server_type": "stdio",
                            "tool_info": tool
                        }

                        # 转换为 OpenAI 工具格式
                        openai_tool = {
                            "type": "function",
                            "function": {
                                "name": prefixed_tool_name,
                                "description": tool.description or "",
                                "parameters": tool.input_schema or {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }
                        }

                        self.tools.append(openai_tool)

                except Exception as e:
                    # print(f"获取 stdio 服务器 {stdio_server.get('name', 'unknown')} 工具列表失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            # print(f"总共构建了 {len(self.tools)} 个工具 (HTTP: {len(self.mcp_servers)}, stdio: {len(self.stdio_mcp_servers)})")

        except Exception as e:
            # print(f"构建工具列表失败: {e}")
            import traceback
            traceback.print_exc()
            self.tools = []

    def find_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        根据工具名称查找工具信息

        Args:
            tool_name: 工具名称（包含服务器前缀）

        Returns:
            工具信息字典或None
        """
        return self.tool_metadata.get(tool_name)

    def execute_tools(self,
                     tool_calls: List[Dict[str, Any]],
                     on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        执行多个工具调用（仅支持流式调用）

        Args:
            tool_calls: 工具调用列表
            on_tool_result: 工具结果回调函数（用于流式处理）

        Returns:
            工具执行结果列表
        """
        return self.execute_tools_stream(tool_calls, on_tool_result)

    def execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个工具调用（仅支持流式调用）

        Args:
            tool_call: 工具调用信息

        Returns:
            工具执行结果
        """
        return self.execute_single_tool_stream(tool_call)



    async def _call_mcp_tool_stream(self, tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        流式调用MCP工具
        支持 stdio 和 HTTP SSE 两种类型的服务器

        Args:
            tool_name: 工具名称（包含服务器前缀）
            arguments: 工具参数

        Yields:
            str: 流式输出的内容块
        """
        try:
            # 添加调试日志
            # print(f"[DEBUG] _call_mcp_tool_stream - tool_name: {tool_name}")
            # print(f"[DEBUG] _call_mcp_tool_stream - arguments type: {type(arguments)}")
            # print(f"[DEBUG] _call_mcp_tool_stream - arguments value: {repr(arguments)}")
            
            # 验证参数类型
            if arguments is not None and not isinstance(arguments, dict):
                error_msg = f"arguments 必须是字典类型，当前类型: {type(arguments)}"
                # print(f"[DEBUG] _call_mcp_tool_stream - 参数类型错误: {error_msg}")
                raise TypeError(error_msg)
            
            # 确保 arguments 是字典
            if arguments is None:
                arguments = {}
            
            # 查找工具信息
            tool_info = self.find_tool_info(tool_name)
            if not tool_info:
                error_msg = f"工具未找到: {tool_name}"
                # print(f"[DEBUG] _call_mcp_tool_stream - 工具不存在: {error_msg}")
                raise Exception(error_msg)

            # 获取原始工具名称和服务器信息
            original_name = tool_info["original_name"]
            server_type = tool_info.get("server_type", "http")
            server_name = tool_info["server_name"]

            if server_type == "stdio":
                # 处理 stdio 类型的服务器
                # print(f"流式调用 stdio MCP 工具: {server_name} -> {original_name}")

                server_command = tool_info["server_script"]
                server_alias = tool_info.get("server_alias")

                # 调试信息：检查参数
                # print(f"调试信息 - server_command: {server_command}")
                # print(f"调试信息 - server_alias: {server_alias}")
                # print(f"调试信息 - config_dir: {self.config_dir}")
                
                # 确保所有必要参数都不是 None
                if not server_command:
                    raise ValueError("server_command 不能为空")
                if not self.config_dir:
                    raise ValueError("config_dir 不能为空")
                
                # 每次调用创建新的客户端连接
                # print(f"[DEBUG] 准备创建 SimpleClient 连接 - script: {server_command}, alias: {server_alias}")
                try:
                    async with SimpleClient(
                        server_script=server_command,
                        alias=server_alias,
                        config_dir=self.config_dir
                    ) as client:
                        # print(f"[DEBUG] SimpleClient 连接已建立")
                        # print(f"[DEBUG] stdio 流式调用开始 - tool: {original_name}, args: {arguments}")
                        # 流式调用工具
                        if arguments:
                            chunk_count = 0
                            async for chunk in client.call_stream(original_name, **arguments):
                                chunk_count += 1
                                # print(f"[DEBUG] stdio 流式返回 chunk #{chunk_count}: {repr(chunk)}")
                                yield chunk
                            # print(f"[DEBUG] stdio 流式调用完成 - 总共返回 {chunk_count} 个 chunks")
                        else:
                            chunk_count = 0
                            async for chunk in client.call_stream(original_name):
                                chunk_count += 1
                                # print(f"[DEBUG] stdio 流式返回 chunk #{chunk_count}: {repr(chunk)}")
                                yield chunk
                            # print(f"[DEBUG] stdio 流式调用完成 - 总共返回 {chunk_count} 个 chunks")
                        # print(f"[DEBUG] 即将退出 SimpleClient 上下文管理器")
                    # print(f"[DEBUG] SimpleClient 连接已关闭")
                except Exception as client_error:
                    # print(f"[DEBUG] SimpleClient 连接异常: {client_error}")
                    import traceback
                    traceback.print_exc()
                    raise

            else:
                # HTTP 服务器使用 SSE 流式调用
                # print(f"流式调用 HTTP SSE MCP 工具: {server_name} -> {original_name}")
                
                server_url = tool_info["server_url"]
                
                # 构造 SSE 请求数据
                request_data = {
                    "tool_name": original_name,
                    "arguments": arguments or {}
                }
                
                # print(f"[DEBUG] HTTP SSE 流式调用开始 - tool: {original_name}, args: {arguments}")
                # print(f"[DEBUG] HTTP SSE 请求数据: {request_data}")
                
                # 使用 SSE 端点进行流式调用
                sse_url = f"{server_url}/sse/tool/call"
                # print(f"[DEBUG] HTTP SSE URL: {sse_url}")
                
                # 发送 SSE 请求
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        sse_url,
                        json=request_data,
                        headers={
                            "Accept": "text/event-stream",
                            "Content-Type": "application/json"
                        }
                    ) as response:
                        # print(f"[DEBUG] HTTP SSE 响应状态: {response.status}")
                        if response.status != 200:
                            error_text = await response.text()
                            # print(f"[DEBUG] HTTP SSE 错误响应: {error_text}")
                            raise Exception(f"HTTP SSE 请求失败: {response.status} - {error_text}")
                        
                        # 解析 SSE 流
                        chunk_count = 0
                        async for line in response.content:
                            line_str = line.decode('utf-8').strip()
                            # print(f"[DEBUG] HTTP SSE 原始行: {repr(line_str)}")
                            
                            # 跳过空行和注释行
                            if not line_str or line_str.startswith(':'):
                                continue
                            
                            # 解析 SSE 数据
                            if line_str.startswith('data: '):
                                data = line_str[6:]  # 移除 'data: ' 前缀
                                # print(f"[DEBUG] HTTP SSE 数据部分: {repr(data)}")
                                
                                # 检查是否是结束标记
                                if data == '[DONE]':
                                    # print(f"[DEBUG] HTTP SSE 收到结束标记")
                                    break
                                
                                try:
                                    # 尝试解析 JSON 数据
                                    json_data = json.loads(data)
                                    if isinstance(json_data, dict) and 'content' in json_data:
                                        chunk_count += 1
                                        content = json_data['content']
                                        # print(f"[DEBUG] HTTP SSE 流式返回 chunk #{chunk_count}: {repr(content)}")
                                        yield content
                                    else:
                                        chunk_count += 1
                                        # print(f"[DEBUG] HTTP SSE 流式返回 chunk #{chunk_count}: {repr(data)}")
                                        yield data
                                except json.JSONDecodeError:
                                    # 如果不是 JSON，直接返回原始数据
                                    chunk_count += 1
                                    # print(f"[DEBUG] HTTP SSE 流式返回 chunk #{chunk_count} (非JSON): {repr(data)}")
                                    yield data
                        
                        # print(f"[DEBUG] HTTP SSE 流式调用完成 - 总共返回 {chunk_count} 个 chunks")

        except Exception as e:
            print(f"MCP流式工具调用失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"MCP流式工具调用失败: {str(e)}")

    def _accumulate_stream_result(self, tool_name: str, arguments: Dict[str, Any], on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None, tool_call_id: str = "") -> str:
        """
        累积流式结果为完整字符串的同步方法
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            str: 累积的完整结果
        """
        # print(f"[DEBUG] _accumulate_stream_result 开始 - tool: {tool_name}, args: {arguments}")
        try:
            # 运行异步流式调用并累积结果
            async def _accumulate():
                result_parts = []
                chunk_count = 0
                async for chunk in self._call_mcp_tool_stream(tool_name, arguments):
                    chunk_count += 1
                    chunk_str = str(chunk)
                    # print(f"[DEBUG] _accumulate_stream_result 累积 chunk #{chunk_count}: {repr(chunk_str)}")
                    result_parts.append(chunk_str)
                    
                    # 如果有回调函数，立即发送流式内容
                    if on_tool_stream:
                        stream_data = {
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "success": True,
                            "is_error": False,
                            "content": chunk_str,
                            "is_stream": True
                        }
                        on_tool_stream(stream_data)
                
                final_result = "".join(result_parts)
                print(f"[DEBUG] _accumulate_stream_result 完成 - 总共 {chunk_count} 个 chunks, 最终结果长度: {len(final_result)}")
                # print(f"[DEBUG] _accumulate_stream_result 最终结果: {repr(final_result)}")
                return final_result
            
            # 处理事件循环问题
            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建新的事件循环
                    import threading
                    result_container = []
                    exception_container = []
                    
                    def run_in_thread():
                        try:
                            # print(f"[DEBUG] 新线程开始 - 线程ID: {threading.current_thread().ident}")
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            # print(f"[DEBUG] 新事件循环已创建并设置")
                            result = new_loop.run_until_complete(_accumulate())
                            result_container.append(result)
                            # print(f"[DEBUG] 关闭新事件循环")
                            new_loop.close()
                            # print(f"[DEBUG] 新线程即将结束 - 线程ID: {threading.current_thread().ident}")
                        except Exception as e:
                            print(f"[DEBUG] 新线程异常: {e}")
                            exception_container.append(e)
                    
                    # print(f"[DEBUG] 创建新线程来运行异步任务")
                    thread = threading.Thread(target=run_in_thread)
                    thread.start()
                    # print(f"[DEBUG] 等待线程完成...")
                    thread.join()
                    print(f"[DEBUG] 线程已完成并回收")
                    
                    if exception_container:
                        raise exception_container[0]
                    
                    result = result_container[0] if result_container else ""
                else:
                    # 事件循环未运行，直接使用
                    result = loop.run_until_complete(_accumulate())
                    
            except RuntimeError:
                # 没有事件循环，创建新的
                result = asyncio.run(_accumulate())
            
            # print(f"[DEBUG] _accumulate_stream_result 返回结果: {repr(result)}")
            return result
            
        except Exception as e:
            error_msg = f"工具调用失败: {str(e)}"
            print(f"[DEBUG] _accumulate_stream_result 异常: {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用的工具列表

        Returns:
            可用工具列表（OpenAI 格式）
        """
        return self.tools

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取工具列表（与前端保持一致的方法名）

        Returns:
            工具列表
        """
        return self.tools



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
                                    on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        执行工具调用（带验证，支持流式回调）

        Args:
            tool_calls: 工具调用列表
            on_tool_stream: 工具流式内容回调函数

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
                    "success": False,
                    "content": validation["error_message"],
                    "is_error": True
                }
                results.append(error_result)

                if on_tool_stream:
                    on_tool_stream(error_result)
                continue

            # 执行工具调用（流式）
            try:
                result = self.execute_single_tool_stream(tool_call, on_tool_stream)
                results.append(result)

            except Exception as e:
                error_result = {
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "success": False,
                    "content": f"工具执行失败: {str(e)}",
                    "is_error": True
                }
                results.append(error_result)

                if on_tool_stream:
                    on_tool_stream(error_result)

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

    def execute_tools_stream(self,
                           tool_calls: List[Dict[str, Any]],
                           on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        流式执行多个工具调用，累积流式内容

        Args:
            tool_calls: 工具调用列表
            on_tool_result: 工具结果回调函数

        Returns:
            工具执行结果列表
        """
        results = []
        
        for tool_call in tool_calls:
            try:
                # 获取工具信息
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name")
                arguments_str = function_info.get("arguments", "{}")
                
                # 添加调试日志
                # print(f"[DEBUG] execute_tools_stream - tool_call: {tool_call}")
                # print(f"[DEBUG] execute_tools_stream - function_info: {function_info}")
                # print(f"[DEBUG] execute_tools_stream - tool_name: {tool_name}")
                # print(f"[DEBUG] execute_tools_stream - arguments_str type: {type(arguments_str)}")
                # print(f"[DEBUG] execute_tools_stream - arguments_str value: {repr(arguments_str)}")
                
                if not tool_name:
                    result = {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": "unknown",
                        "success": False,
                        "is_error": True,
                        "content": "工具名称不能为空"
                    }
                    results.append(result)
                    if on_tool_result:
                        on_tool_result(result)
                    continue
                
                # 解析参数
                try:
                    if isinstance(arguments_str, str):
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    elif isinstance(arguments_str, dict):
                        arguments = arguments_str
                    else:
                        arguments = {}
                    print(f"[DEBUG] execute_tools_stream - parsed arguments: {arguments}")
                except json.JSONDecodeError as e:
                    error_msg = f"参数解析失败: {str(e)}"
                    print(f"[DEBUG] execute_tools_stream - JSON解析错误: {error_msg}")
                    result = {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "success": False,
                        "is_error": True,
                        "content": error_msg
                    }
                    results.append(result)
                    if on_tool_result:
                        on_tool_result(result)
                    continue
                
                # 使用流式方法调用工具
                content = self._accumulate_stream_result(tool_name, arguments)
                
                result = {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_name,
                    "success": True,
                    "is_error": False,
                    "content": content
                }
                
                results.append(result)
                
                # 调用回调函数
                if on_tool_result:
                    on_tool_result(result)
                    
            except Exception as e:
                result = {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_name if 'tool_name' in locals() else "unknown",
                    "success": False,
                    "is_error": True,
                    "content": f"工具执行失败: {str(e)}"
                }
                results.append(result)
                if on_tool_result:
                    on_tool_result(result)
        
        return results

    def execute_single_tool_stream(self, tool_call: Dict[str, Any], on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        流式执行单个工具调用

        Args:
            tool_call: 工具调用信息

        Returns:
            工具执行结果
        """
        try:
            function_info = tool_call.get("function", {})
            tool_name = function_info.get("name")
            arguments_str = function_info.get("arguments", "{}")
            
            if not tool_name:
                return {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": "unknown",
                    "success": False,
                    "is_error": True,
                    "content": "工具名称不能为空"
                }
            
            # # 添加调试日志
            # print(f"[DEBUG] execute_single_tool_stream - tool_name: {tool_name}")
            # print(f"[DEBUG] execute_single_tool_stream - arguments_str type: {type(arguments_str)}")
            # print(f"[DEBUG] execute_single_tool_stream - arguments_str value: {repr(arguments_str)}")
            
            # 解析参数
            try:
                if isinstance(arguments_str, str):
                    arguments = json.loads(arguments_str) if arguments_str else {}
                elif isinstance(arguments_str, dict):
                    arguments = arguments_str
                else:
                    arguments = {}
                print(f"[DEBUG] execute_single_tool_stream - parsed arguments: {arguments}")
            except json.JSONDecodeError as e:
                error_msg = f"参数解析失败: {str(e)}"
                print(f"[DEBUG] execute_single_tool_stream - JSON解析错误: {error_msg}")
                return {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_name,
                    "success": False,
                    "is_error": True,
                    "content": error_msg
                }
            
            # 使用流式方法调用工具
            content = self._accumulate_stream_result(tool_name, arguments, on_tool_stream, tool_call.get("id", ""))
            
            return {
                "tool_call_id": tool_call.get("id", ""),
                "name": tool_name,
                "success": True,
                "is_error": False,
                "content": content
            }
            
        except Exception as e:
            return {
                "tool_call_id": tool_call.get("id", ""),
                "name": tool_name if 'tool_name' in locals() else "unknown",
                "success": False,
                "is_error": True,
                "content": f"工具执行失败: {str(e)}"
            }
