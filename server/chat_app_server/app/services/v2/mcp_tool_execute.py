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
                        print(f"跳过无效的 HTTP 服务器配置: {mcp_server}")
                        continue

                    # 调用 MCP 服务获取 tools - 使用标准的 MCP 协议
                    request_data = {
                        "jsonrpc": "2.0",
                        "id": f"req_{int(time.time() * 1000)}_{hash(server_name) % 10000}",
                        "method": "tools/list",
                        "params": {}
                    }

                    print(f"获取 HTTP MCP 服务器 {server_name} 的工具列表: {server_url}")
                    response = self.session.post(server_url, json=request_data)
                    response.raise_for_status()

                    response_data = response.json()

                    if response_data.get("error"):
                        raise Exception(f"MCP tools/list 失败: {response_data['error'].get('message', '未知错误')}")

                    # 获取工具列表
                    tools_result = response_data.get("result", {})
                    tools_list = tools_result.get("tools", [])

                    print(f"从 HTTP 服务器 {server_name} 获取到 {len(tools_list)} 个工具")

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
                    print(f"获取 HTTP 服务器 {mcp_server.get('name', 'unknown')} 工具列表失败: {e}")
                    continue

            # 处理 stdio 类型的 MCP 服务器
            for stdio_server in self.stdio_mcp_servers:
                try:
                    server_name = stdio_server.get("name")
                    server_command = stdio_server.get("command")
                    server_alias = stdio_server.get("alias")

                    if not server_name or not server_command:
                        print(f"跳过无效的 stdio 服务器配置: {stdio_server}")
                        continue

                    print(f"获取 stdio MCP 服务器 {server_name} 的工具列表")

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

                    print(f"从 stdio 服务器 {server_name} 获取到 {len(tools_list)} 个工具")

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
                    print(f"获取 stdio 服务器 {stdio_server.get('name', 'unknown')} 工具列表失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f"总共构建了 {len(self.tools)} 个工具 (HTTP: {len(self.mcp_servers)}, stdio: {len(self.stdio_mcp_servers)})")

        except Exception as e:
            print(f"构建工具列表失败: {e}")
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
                     on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None,
                     use_streaming: bool = True) -> List[Dict[str, Any]]:
        """
        执行多个工具调用（默认使用流式调用）

        Args:
            tool_calls: 工具调用列表
            on_tool_result: 工具结果回调函数（用于流式处理）
            use_streaming: 是否使用流式调用，默认为 True

        Returns:
            工具执行结果列表
        """
        if use_streaming:
            # 使用流式调用
            return self.execute_tools_stream(tool_calls, on_tool_result)
        
        # 使用传统调用方式
        results = []

        for tool_call in tool_calls:
            try:
                result = self.execute_single_tool(tool_call, use_streaming=False)
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

    def execute_single_tool(self, tool_call: Dict[str, Any], use_streaming: bool = True) -> Dict[str, Any]:
        """
        执行单个工具调用（默认使用流式调用）

        Args:
            tool_call: 工具调用信息
            use_streaming: 是否使用流式调用，默认为 True

        Returns:
            工具执行结果
        """
        if use_streaming:
            # 使用流式调用
            return self.execute_single_tool_stream(tool_call)
        
        # 使用传统调用方式
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
        支持 HTTP 和 stdio 两种类型的服务器

        Args:
            tool_name: 工具名称（包含服务器前缀）
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        try:
            # 查找工具信息
            tool_info = self.find_tool_info(tool_name)
            if not tool_info:
                raise Exception(f"工具未找到: {tool_name}")

            # 获取原始工具名称和服务器信息
            original_name = tool_info["original_name"]
            server_type = tool_info.get("server_type", "http")
            server_name = tool_info["server_name"]

            if server_type == "stdio":
                # 处理 stdio 类型的服务器
                print(f"调用 stdio MCP 工具: {server_name} -> {original_name}")

                server_command = tool_info["server_script"]
                server_alias = tool_info.get("server_alias")

                # 异步调用工具
                async def call_stdio_tool():
                    # 调试信息：检查参数
                    print(f"调试信息 - server_command: {server_command}")
                    print(f"调试信息 - server_alias: {server_alias}")
                    print(f"调试信息 - config_dir: {self.config_dir}")
                    
                    # 确保所有必要参数都不是 None
                    if not server_command:
                        raise ValueError("server_command 不能为空")
                    if not self.config_dir:
                        raise ValueError("config_dir 不能为空")
                    
                    # 每次调用创建新的客户端连接
                    async with SimpleClient(
                        server_script=server_command,
                        alias=server_alias,
                        config_dir=self.config_dir
                    ) as client:
                        # 调用工具 - 使用 call 方法而不是 call_stream
                        result = await client.call(original_name, **arguments) if arguments else await client.call(original_name)
                        return result

                # 运行异步函数
                result = asyncio.run(call_stdio_tool())
                return result

            else:
                # 处理 HTTP 类型的服务器
                server_url = tool_info["server_url"]

                # 构建 JSON-RPC 请求
                request_data = {
                    "jsonrpc": "2.0",
                    "id": f"req_{int(time.time() * 1000)}_{hash(tool_name) % 10000}",
                    "method": "tools/call",
                    "params": {
                        "name": original_name,
                        "arguments": arguments or {}
                    }
                }

                print(f"调用 HTTP MCP 工具: {server_url} -> {original_name}")

                # 发送请求到 MCP 服务器
                response = self.session.post(server_url, json=request_data)
                response.raise_for_status()

                response_data = response.json()

                if response_data.get("error"):
                    raise Exception(f"MCP 工具调用失败: {response_data['error'].get('message', '未知错误')}")

                return response_data.get("result")

        except Exception as e:
            print(f"MCP工具调用失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"MCP工具调用失败: {str(e)}")

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
            # 验证参数类型
            if arguments is not None and not isinstance(arguments, dict):
                raise TypeError(f"arguments 必须是字典类型，当前类型: {type(arguments)}")
            
            # 确保 arguments 是字典
            if arguments is None:
                arguments = {}
            
            # 查找工具信息
            tool_info = self.find_tool_info(tool_name)
            if not tool_info:
                raise Exception(f"工具未找到: {tool_name}")

            # 获取原始工具名称和服务器信息
            original_name = tool_info["original_name"]
            server_type = tool_info.get("server_type", "http")
            server_name = tool_info["server_name"]

            if server_type == "stdio":
                # 处理 stdio 类型的服务器
                print(f"流式调用 stdio MCP 工具: {server_name} -> {original_name}")

                server_command = tool_info["server_script"]
                server_alias = tool_info.get("server_alias")

                # 调试信息：检查参数
                print(f"调试信息 - server_command: {server_command}")
                print(f"调试信息 - server_alias: {server_alias}")
                print(f"调试信息 - config_dir: {self.config_dir}")
                
                # 确保所有必要参数都不是 None
                if not server_command:
                    raise ValueError("server_command 不能为空")
                if not self.config_dir:
                    raise ValueError("config_dir 不能为空")
                
                # 每次调用创建新的客户端连接
                async with SimpleClient(
                    server_script=server_command,
                    alias=server_alias,
                    config_dir=self.config_dir
                ) as client:
                    # 流式调用工具
                    if arguments:
                        async for chunk in client.call_stream(original_name, **arguments):
                            yield chunk
                    else:
                        async for chunk in client.call_stream(original_name):
                            yield chunk

            else:
                # HTTP 服务器使用 SSE 流式调用
                print(f"流式调用 HTTP SSE MCP 工具: {server_name} -> {original_name}")
                
                server_url = tool_info["server_url"]
                
                # 构造 SSE 请求数据
                request_data = {
                    "tool_name": original_name,
                    "arguments": arguments or {}
                }
                
                # 使用 SSE 端点进行流式调用
                sse_url = f"{server_url}/sse/tool/call"
                
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
                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"HTTP SSE 请求失败: {response.status} - {error_text}")
                        
                        # 解析 SSE 流
                        async for line in response.content:
                            line_str = line.decode('utf-8').strip()
                            
                            # 跳过空行和注释行
                            if not line_str or line_str.startswith(':'):
                                continue
                            
                            # 解析 SSE 数据
                            if line_str.startswith('data: '):
                                data = line_str[6:]  # 移除 'data: ' 前缀
                                
                                # 检查是否是结束标记
                                if data == '[DONE]':
                                    break
                                
                                try:
                                    # 尝试解析 JSON 数据
                                    json_data = json.loads(data)
                                    if isinstance(json_data, dict) and 'content' in json_data:
                                        yield json_data['content']
                                    else:
                                        yield data
                                except json.JSONDecodeError:
                                    # 如果不是 JSON，直接返回原始数据
                                    yield data

        except Exception as e:
            print(f"MCP流式工具调用失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"MCP流式工具调用失败: {str(e)}")

    def call_tool_stream_sync(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        同步版本的流式工具调用，累积所有流式内容并返回完整结果

        Args:
            tool_name: 工具名称（包含服务器前缀）
            arguments: 工具参数

        Returns:
            str: 累积的完整内容
        """
        async def _accumulate_stream():
            accumulated_content = ""
            async for chunk in self._call_mcp_tool_stream(tool_name, arguments):
                accumulated_content += chunk
            return accumulated_content

        try:
            # 检查是否已经在事件循环中
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用 asyncio.create_task
            import asyncio
            task = asyncio.create_task(_accumulate_stream())
            # 在当前事件循环中运行任务
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        except RuntimeError:
            # 没有运行的事件循环，可以直接使用 asyncio.run
            return asyncio.run(_accumulate_stream())
        except Exception as e:
            # 如果上述方法都失败，使用线程池执行器
            import concurrent.futures
            import threading
            
            def run_in_thread():
                # 在新线程中创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(_accumulate_stream())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()

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
                                    on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None,
                                    use_streaming: bool = True) -> List[Dict[str, Any]]:
        """
        执行工具调用（带验证，默认使用流式调用）

        Args:
            tool_calls: 工具调用列表
            on_tool_result: 工具结果回调函数
            use_streaming: 是否使用流式调用，默认为 True

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
                result = self.execute_single_tool(tool_call, use_streaming=use_streaming)
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
                arguments = function_info.get("arguments", {})
                
                if not tool_name:
                    result = {
                        "tool_call_id": tool_call.get("id", ""),
                        "is_error": True,
                        "content": "工具名称不能为空"
                    }
                    results.append(result)
                    if on_tool_result:
                        on_tool_result(result)
                    continue
                
                # 使用流式方法调用工具
                content = self.call_tool_stream_sync(tool_name, arguments)
                
                result = {
                    "tool_call_id": tool_call.get("id", ""),
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
                    "is_error": True,
                    "content": f"工具执行失败: {str(e)}"
                }
                results.append(result)
                if on_tool_result:
                    on_tool_result(result)
        
        return results

    def execute_single_tool_stream(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
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
            arguments = function_info.get("arguments", {})
            
            if not tool_name:
                return {
                    "tool_call_id": tool_call.get("id", ""),
                    "is_error": True,
                    "content": "工具名称不能为空"
                }
            
            # 使用流式方法调用工具
            content = self.call_tool_stream_sync(tool_name, arguments)
            
            return {
                "tool_call_id": tool_call.get("id", ""),
                "is_error": False,
                "content": content
            }
            
        except Exception as e:
            return {
                "tool_call_id": tool_call.get("id", ""),
                "is_error": True,
                "content": f"工具执行失败: {str(e)}"
            }
