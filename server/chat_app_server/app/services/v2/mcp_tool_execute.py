"""
MCP工具执行器（mcp-python / fastmcp）
使用 fastmcp.Client 统一支持 HTTP 与 STDIO 两种连接方式。

功能：
- 构建工具列表（名称添加服务器前缀，避免冲突）
- 执行单个或多个工具调用（一次性返回结果），可选结果回调
- 保留原有方法名以兼容调用方（execute_tools_stream 等）
"""

import json
import asyncio
import os
import shlex
from typing import Dict, List, Any, Optional, Callable

from fastmcp import Client


def to_text(result: Any) -> str:
    """提取 fastmcp 返回对象中的文本内容，兼容不同版本。"""
    text_attr = getattr(result, "text", None)
    if callable(text_attr):
        try:
            return text_attr()
        except Exception:
            pass

    content = getattr(result, "content", None)
    if content:
        first = content[0] if content else None
        if isinstance(first, dict):
            if first.get("type") == "text":
                return first.get("text", "")
        else:
            t = getattr(first, "type", None)
            if t == "text":
                return getattr(first, "text", "") or getattr(first, "value", "")

    value = getattr(result, "value", None)
    if isinstance(value, str):
        return value

    return str(result)


def _run(coro):
    """在当前或新的事件循环中运行协程并返回结果。"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class McpToolExecute:
    """基于 fastmcp.Client 的 MCP 工具执行器"""

    def __init__(self,
                 mcp_servers: Optional[List[Dict[str, Any]]] = None,
                 stdio_mcp_servers: Optional[List[Dict[str, Any]]] = None,
                 config_dir: Optional[str] = None):
        """
        Args:
            mcp_servers: HTTP MCP服务器列表，如 [{"name": "server", "url": "http://127.0.0.1:8000/mcp"}]
            stdio_mcp_servers: STDIO MCP服务器列表，如 [{"name": "server", "command": "python", "args": ["-m", "..."], "cwd": "...", "env": {...}}]
            config_dir: 预留参数（不使用）
        """
        self.mcp_servers = mcp_servers or []
        self.stdio_mcp_servers = stdio_mcp_servers or []
        self.config_dir = config_dir

        self.tools: List[Dict[str, Any]] = []
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _make_stdio_server_config(stdio_server: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        规范化并构造 fastmcp.Client 可接受的 STDIO 配置。

        支持：
        - args: 字符串（用 shlex.split）或列表，自动过滤空项
        - cwd: 可选，未提供则不设置（继承当前工作目录）
        - env: 可选，仅当为非空 dict 时传递

        Returns:
            一个包含 mcpServers 的配置字典；若 name/command 缺失则返回 None。
        """
        server_name = stdio_server.get("name")
        command = stdio_server.get("command")
        if not server_name or not command:
            return None

        raw_args = stdio_server.get("args", None)
        if isinstance(raw_args, str):
            args = shlex.split(raw_args) if raw_args.strip() else []
        elif isinstance(raw_args, list):
            args = [str(a).strip() for a in raw_args if str(a).strip()]
        else:
            args = []

        cwd = stdio_server.get("cwd")
        env = stdio_server.get("env", {})

        server_entry: Dict[str, Any] = {
            "transport": "stdio",
            "command": command,
        }
        if args:
            server_entry["args"] = args
        if cwd:
            server_entry["cwd"] = cwd
        if isinstance(env, dict) and env:
            server_entry["env"] = env

        return {
            "mcpServers": {
                server_name: server_entry
            }
        }

    def init(self):
        """初始化并构建工具列表"""
        self.build_tools()

    def build_tools(self):
        """构建工具列表，支持 HTTP 与 STDIO。"""
        try:
            self.tools = []
            self.tool_metadata = {}

            # HTTP 服务器：直接传入 /mcp 端点 URL
            for mcp_server in self.mcp_servers:
                server_name = mcp_server.get("name")
                server_url = mcp_server.get("url")
                if not server_name or not server_url:
                    continue

                async def _list_http():
                    async with Client(server_url) as client:
                        return await client.list_tools()

                tools_list = _run(_list_http())
                for tool in tools_list:
                    tool_name = getattr(tool, "name", None)
                    if not tool_name:
                        continue

                    prefixed = f"{server_name}_{tool_name}"
                    self.tool_metadata[prefixed] = {
                        "original_name": tool_name,
                        "server_name": server_name,
                        "server_url": server_url,
                        "server_type": "http",
                        "tool_info": tool,
                    }

                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": prefixed,
                            "description": getattr(tool, "description", "") or "",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            },
                        },
                    }
                    self.tools.append(openai_tool)

            # STDIO 服务器：通过配置启动进程
            for stdio_server in self.stdio_mcp_servers:
                server_name = stdio_server.get("name")
                config = self._make_stdio_server_config(stdio_server)
                if not config:
                    continue

                async def _list_stdio():
                    async with Client(config) as client:
                        return await client.list_tools()

                tools_list = _run(_list_stdio())
                for tool in tools_list:
                    tool_name = getattr(tool, "name", None)
                    if not tool_name:
                        continue

                    prefixed = f"{server_name}_{tool_name}"
                    self.tool_metadata[prefixed] = {
                        "original_name": tool_name,
                        "server_name": server_name,
                        "server_type": "stdio",
                        "server_config": config,
                        "tool_info": tool,
                    }

                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": prefixed,
                            "description": getattr(tool, "description", "") or "",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            },
                        },
                    }
                    self.tools.append(openai_tool)

        except Exception:
            import traceback
            traceback.print_exc()
            self.tools = []

    def find_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """根据前缀名称查找工具元数据。"""
        return self.tool_metadata.get(tool_name)

    async def _call_mcp_tool_once(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """一次性调用 MCP 工具并返回文本结果。"""
        if arguments is not None and not isinstance(arguments, dict):
            raise TypeError(f"arguments 必须是字典类型，当前类型: {type(arguments)}")
        arguments = arguments or {}

        info = self.find_tool_info(tool_name)
        if not info:
            raise Exception(f"工具未找到: {tool_name}")

        original = info["original_name"]
        if info.get("server_type") == "stdio":
            config = info["server_config"]
            async with Client(config) as client:
                result = await client.call_tool(original, arguments)
                return to_text(result)
        else:
            server_url = info["server_url"]
            async with Client(server_url) as client:
                result = await client.call_tool(original, arguments)
                return to_text(result)

    def _accumulate_stream_result(self,
                                  tool_name: str,
                                  arguments: Dict[str, Any],
                                  on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
                                  tool_call_id: str = "") -> str:
        """
        兼容旧接口名称：内部直接一次性调用并返回。
        若提供 on_tool_stream，则在完成后回调一次完整结果。
        """
        async def _once():
            text = await self._call_mcp_tool_once(tool_name, arguments)
            if on_tool_stream:
                try:
                    print(f"[MCP_TOOL] on_tool_stream 调用: {tool_name} (tool_call_id={tool_call_id}) 成功, 内容长度={len(str(text))}")
                except Exception:
                    pass
                try:
                    on_tool_stream({
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "success": True,
                        "is_error": False,
                        "content": text,
                        "is_stream": False,
                    })
                except Exception as e:
                    try:
                        print(f"[MCP_TOOL] on_tool_stream 回调错误: {e}")
                    except Exception:
                        pass
            return text
        return _run(_once())

    def execute_tools(self,
                      tool_calls: List[Dict[str, Any]],
                      on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """执行多个工具调用（保留方法名以兼容，内部一次性返回）。"""
        return self.execute_tools_stream(tool_calls, on_tool_result)

    def execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个工具调用（保留方法名以兼容，内部一次性返回）。"""
        return self.execute_single_tool_stream(tool_call)

    def execute_tools_stream(self,
                             tool_calls: List[Dict[str, Any]],
                             on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """执行多个工具调用（内部一次性返回结果）。"""
        results: List[Dict[str, Any]] = []
        for tool_call in tool_calls:
            try:
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name")
                arguments_str = function_info.get("arguments", "{}")

                if not tool_name:
                    result = {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": "unknown",
                        "success": False,
                        "is_error": True,
                        "content": "工具名称不能为空",
                    }
                    results.append(result)
                    if on_tool_result:
                        on_tool_result(result)
                    continue

                try:
                    if isinstance(arguments_str, str):
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    elif isinstance(arguments_str, dict):
                        arguments = arguments_str
                    else:
                        arguments = {}
                except json.JSONDecodeError as e:
                    result = {
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "success": False,
                        "is_error": True,
                        "content": f"参数解析失败: {str(e)}",
                    }
                    results.append(result)
                    if on_tool_result:
                        on_tool_result(result)
                    continue

                def _call():
                    async def _inner():
                        return await self._call_mcp_tool_once(tool_name, arguments)
                    return _run(_inner())

                text = _call()
                final = {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_name,
                    "success": True,
                    "is_error": False,
                    "content": text,
                }
                results.append(final)
                if on_tool_result:
                    on_tool_result(final)

            except Exception as e:
                err = {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "success": False,
                    "is_error": True,
                    "content": f"工具执行失败: {str(e)}",
                }
                results.append(err)
                if on_tool_result:
                    on_tool_result(err)
        return results

    def execute_single_tool_stream(self,
                                   tool_call: Dict[str, Any],
                                   on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """执行单个工具调用（保留名称以兼容，内部一次性返回）。"""
        try:
            function_info = tool_call.get("function", {})
            tool_name = function_info.get("name")
            arguments_str = function_info.get("arguments", "{}")
            tool_call_id = tool_call.get("id", "")

            if not tool_name:
                result = {
                    "tool_call_id": tool_call_id,
                    "name": "unknown",
                    "success": False,
                    "is_error": True,
                    "content": "工具名称不能为空",
                }
                if on_tool_stream:
                    on_tool_stream(result)
                return result

            try:
                if isinstance(arguments_str, str):
                    arguments = json.loads(arguments_str) if arguments_str else {}
                elif isinstance(arguments_str, dict):
                    arguments = arguments_str
                else:
                    arguments = {}
            except json.JSONDecodeError as e:
                result = {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "success": False,
                    "is_error": True,
                    "content": f"参数解析失败: {str(e)}",
                }
                if on_tool_stream:
                    on_tool_stream(result)
                return result

            final_text = self._accumulate_stream_result(tool_name, arguments, on_tool_stream, tool_call_id)
            result = {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "success": True,
                "is_error": False,
                "content": final_text,
            }
            if on_tool_stream:
                try:
                    print(f"[MCP_TOOL] on_tool_stream 完成: {tool_name} (tool_call_id={tool_call_id}) 成功, 内容长度={len(str(final_text))}")
                except Exception:
                    pass
            return result

        except Exception as e:
            error_result = {
                "tool_call_id": tool_call.get("id", ""),
                "name": tool_call.get("function", {}).get("name", "unknown"),
                "success": False,
                "is_error": True,
                "content": f"工具执行失败: {str(e)}",
            }
            if on_tool_stream:
                try:
                    print(f"[MCP_TOOL] on_tool_stream 错误: {error_result.get('name')} (tool_call_id={error_result.get('tool_call_id')}) 错误信息={error_result.get('content')}")
                except Exception:
                    pass
                try:
                    on_tool_stream(error_result)
                except Exception as e:
                    try:
                        print(f"[MCP_TOOL] on_tool_stream 回调错误: {e}")
                    except Exception:
                        pass
            return error_result

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表（OpenAI 工具格式）。"""
        return self.tools

    def get_tools(self) -> List[Dict[str, Any]]:
        """与前端保持一致的方法名。"""
        return self.tools

    def validate_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具调用结构。"""
        try:
            function_info = tool_call.get("function", {})
            if not function_info.get("name"):
                raise ValueError("工具名称缺失")
            return {"is_valid": True, "error_message": None}
        except Exception as e:
            return {"is_valid": False, "error_message": f"验证失败: {str(e)}"}

    def execute_tools_with_validation(self,
                                      tool_calls: List[Dict[str, Any]],
                                      on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """带验证的工具调用执行。"""
        results: List[Dict[str, Any]] = []
        for tool_call in tool_calls:
            validation = self.validate_tool_call(tool_call)
            if not validation.get("is_valid"):
                err = {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "success": False,
                    "is_error": True,
                    "content": validation.get("error_message"),
                }
                results.append(err)
                if on_tool_stream:
                    try:
                        print(f"[MCP_TOOL] on_tool_stream 验证失败: {err.get('name')} (tool_call_id={err.get('tool_call_id')}) 错误信息={err.get('content')}")
                    except Exception:
                        pass
                    try:
                        on_tool_stream(err)
                    except Exception as e:
                        try:
                            print(f"[MCP_TOOL] on_tool_stream 回调错误: {e}")
                        except Exception:
                            pass
                continue

            try:
                result = self.execute_single_tool_stream(tool_call, on_tool_stream)
                results.append(result)
            except Exception as e:
                err = {
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_call.get("function", {}).get("name", "unknown"),
                    "success": False,
                    "is_error": True,
                    "content": f"工具执行失败: {str(e)}",
                }
                results.append(err)
                if on_tool_stream:
                    try:
                        print(f"[MCP_TOOL] on_tool_stream 执行失败: {err.get('name')} (tool_call_id={err.get('tool_call_id')}) 错误信息={err.get('content')}")
                    except Exception:
                        pass
                    try:
                        on_tool_stream(err)
                    except Exception as e:
                        try:
                            print(f"[MCP_TOOL] on_tool_stream 回调错误: {e}")
                        except Exception:
                            pass
        return results

    def get_tool_execution_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """统计工具执行情况。"""
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        error = total - success
        return {
            "total_count": total,
            "success_count": success,
            "error_count": error,
            "success_rate": success / total if total > 0 else 0,
        }