"""
MCP工具执行器 - Python实现
对应TypeScript中的McpToolExecute类
"""
import asyncio
import logging
import os
import uuid
from typing import Dict, Any, List, Optional, Callable, Union, AsyncGenerator
import json
from dataclasses import dataclass
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """工具类型枚举"""
    FUNCTION = "function"
    MCP = "mcp"


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    tool_type: ToolType = ToolType.FUNCTION
    supports_streaming: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class McpServer:
    """MCP服务器信息"""
    name: str
    description: str
    version: str
    tools: List[ToolInfo]
    metadata: Optional[Dict[str, Any]] = None


class McpToolExecute:
    """
    MCP工具执行器
    负责执行MCP工具调用，处理流式和非流式响应
    """
    
    def __init__(self, mcp_servers: Dict[str, Dict[str, Any]] = None, stdio_mcp_servers: Dict[str, Dict[str, Any]] = None, role: str = ""):
        self.mcp_servers = mcp_servers or {}  # HTTP 协议的 MCP 服务器
        self.stdio_mcp_servers = stdio_mcp_servers or {}  # stdio 协议的 MCP 服务器
        self.role = role
        
        # 设置全局的 config_dir 为程序当前目录/mcp_config
        current_dir = os.getcwd()
        self.config_dir = os.path.join(current_dir, "mcp_config")
        
        # 确保 mcp_config 目录存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            logger.info(f"✅ 创建 MCP 配置目录: {self.config_dir}")
        else:
            logger.info(f"📁 使用现有 MCP 配置目录: {self.config_dir}")
        
        # 原有的属性
        self.servers: Dict[str, McpServer] = {}
        self.tools: Dict[str, ToolInfo] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        
        # 新增的属性用于支持 stdio 协议
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}  # 存储工具元数据
        self.openai_tools: List[Dict[str, Any]] = []  # OpenAI 格式的工具列表
        
        # 添加客户端缓存
        self._stdio_clients: Dict[str, Any] = {}  # 缓存 stdio 客户端 {cache_key: client}
        self._client_locks: Dict[str, asyncio.Lock] = {}   # 客户端锁，防止并发创建 {cache_key: asyncio.Lock}
        self._cleanup_lock = asyncio.Lock()  # 清理锁
        
    def register_server(self, server: McpServer) -> None:
        """注册MCP服务器"""
        self.servers[server.name] = server
        
        # 注册服务器中的工具
        for tool in server.tools:
            self.tools[tool.name] = tool
            
        logger.info(f"Registered MCP server: {server.name} with {len(server.tools)} tools")
    
    def register_tool_handler(self, tool_name: str, handler: Callable) -> None:
        """注册工具处理器"""
        self.tool_handlers[tool_name] = handler
        logger.info(f"Registered handler for tool: {tool_name}")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表（OpenAI格式）"""
        tools = []
        
        for tool_name, tool_info in self.tools.items():
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info.description,
                    "parameters": tool_info.input_schema
                }
            }
            tools.append(tool_def)
            
        return tools
    
    def get_tool_info(self, tool_name: str) -> Optional[ToolInfo]:
        """获取工具信息"""
        return self.tools.get(tool_name)
    
    def supports_streaming(self, tool_name: str) -> bool:
        """检查工具是否支持流式输出"""
        tool_info = self.get_tool_info(tool_name)
        return tool_info.supports_streaming if tool_info else False
    
    def execute_tool_sync(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: str
    ) -> Any:
        """
        执行工具（非流式，同步版本）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            tool_call_id: 工具调用ID
            
        Returns:
            工具执行结果
        """
        try:
            # 检查工具是否存在
            if tool_name not in self.tools:
                raise ValueError(f"Tool '{tool_name}' not found")
            
            # 检查是否有处理器
            if tool_name not in self.tool_handlers:
                raise ValueError(f"No handler registered for tool '{tool_name}'")
            
            handler = self.tool_handlers[tool_name]
            
            # 执行工具
            logger.info(f"Executing tool: {tool_name} with call_id: {tool_call_id}")
            
            # 如果handler是异步的，我们需要同步调用它
            if asyncio.iscoroutinefunction(handler):
                # 对于异步handler，我们简单返回一个模拟结果
                logger.warning(f"Tool {tool_name} has async handler, returning mock result")
                return f"Tool {tool_name} executed with arguments: {arguments}"
            else:
                result = handler(arguments)
                return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: str
    ) -> Any:
        """
        执行工具（非流式）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            tool_call_id: 工具调用ID
            
        Returns:
            工具执行结果
        """
        try:
            # 检查工具是否存在
            if tool_name not in self.tools:
                raise ValueError(f"Tool '{tool_name}' not found")
            
            # 检查是否有处理器
            if tool_name not in self.tool_handlers:
                raise ValueError(f"No handler registered for tool '{tool_name}'")
            
            handler = self.tool_handlers[tool_name]
            
            # 执行工具
            logger.info(f"Executing tool: {tool_name} with call_id: {tool_call_id}")
            result = await handler(arguments)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise
    
    def execute_stream_sync(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: str,
        on_chunk: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> Any:
        """
        执行工具（流式，同步版本）
        """
        try:
            # 对于同步版本，我们直接执行工具并模拟流式输出
            result = self.execute_tool_sync(tool_name, arguments, tool_call_id)
            
            # 模拟流式输出
            if on_chunk:
                on_chunk(str(result))
            
            if on_complete:
                on_complete()
                
            return result
            
        except Exception as e:
            if on_error:
                on_error(e)
            raise

    async def execute_stream(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: str,
        on_chunk: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> Any:
        """
        执行工具（流式）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            tool_call_id: 工具调用ID
            on_chunk: 流式数据回调
            on_complete: 完成回调
            on_error: 错误回调
            
        Returns:
            工具执行结果
        """
        try:
            # 检查工具是否存在
            if tool_name not in self.tools:
                raise ValueError(f"Tool '{tool_name}' not found")
            
            # 检查是否支持流式
            if not self.supports_streaming(tool_name):
                # 不支持流式，使用普通执行
                result = await self.execute_tool(tool_name, arguments, tool_call_id)
                
                # 模拟流式输出
                if on_chunk:
                    result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
                    on_chunk(result_str)
                
                if on_complete:
                    on_complete(result)
                    
                return result
            
            # 检查是否有处理器
            if tool_name not in self.tool_handlers:
                raise ValueError(f"No handler registered for tool '{tool_name}'")
            
            handler = self.tool_handlers[tool_name]
            
            # 执行流式工具
            logger.info(f"Executing streaming tool: {tool_name} with call_id: {tool_call_id}")
            
            # 假设处理器支持流式回调
            result = await handler(
                arguments,
                on_chunk=on_chunk,
                on_complete=on_complete,
                on_error=on_error
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing streaming tool {tool_name}: {e}")
            if on_error:
                on_error(e)
            raise
    
    async def call_mcp_tool_stream(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: str,
        callback: Optional[Callable] = None
    ) -> Any:
        """
        调用MCP工具（流式）- 兼容原TypeScript接口
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            tool_call_id: 工具调用ID
            callback: 回调函数
            
        Returns:
            工具执行结果
        """
        result_chunks = []
        final_result = None
        
        def on_chunk(chunk: str):
            result_chunks.append(chunk)
            if callback:
                callback("tool_stream_chunk", {
                    "tool_call_id": tool_call_id,
                    "content": chunk
                })
        
        def on_complete(result: Any):
            nonlocal final_result
            final_result = result
            if callback:
                callback("tool_result", {
                    "tool_call_id": tool_call_id,
                    "result": result
                })
        
        def on_error(error: Exception):
            if callback:
                callback("error", {
                    "tool_call_id": tool_call_id,
                    "error": str(error)
                })
        
        try:
            result = await self.execute_stream(
                tool_name=tool_name,
                arguments=arguments,
                tool_call_id=tool_call_id,
                on_chunk=on_chunk,
                on_complete=on_complete,
                on_error=on_error
            )
            
            return result if final_result is None else final_result
            
        except Exception as e:
            on_error(e)
            raise
    
    def get_servers_info(self) -> List[Dict[str, Any]]:
        """获取所有服务器信息"""
        servers_info = []
        
        for server_name, server in self.servers.items():
            server_info = {
                "name": server.name,
                "description": server.description,
                "version": server.version,
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "supports_streaming": tool.supports_streaming,
                        "tool_type": tool.tool_type.value
                    }
                    for tool in server.tools
                ],
                "metadata": server.metadata
            }
            servers_info.append(server_info)
            
        return servers_info
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具的JSON Schema"""
        tool_info = self.get_tool_info(tool_name)
        if not tool_info:
            return None
            
        return {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_info.description,
                "parameters": tool_info.input_schema
            }
        }

    async def init(self):
        """初始化，构建工具列表"""
        await self.build_tools()
    
    def init_sync(self):
        """初始化，构建工具列表（同步版本）"""
        import asyncio
        
        # 对于同步版本，我们需要运行异步的build_tools方法
        self.openai_tools = []
        self.tool_metadata = {}
        
        logger.info(f"🔧 同步初始化MCP工具执行器，HTTP服务器数量: {len(self.mcp_servers)}, stdio服务器数量: {len(self.stdio_mcp_servers)}")
        
        # 运行异步的build_tools方法
        try:
            # 创建新的事件循环或使用现有的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已有运行中的循环，创建新的线程来运行
                    import threading
                    import concurrent.futures
                    
                    def run_build_tools():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(self.build_tools())
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_build_tools)
                        future.result(timeout=30)  # 30秒超时
                else:
                    # 如果循环未运行，直接运行
                    loop.run_until_complete(self.build_tools())
            except RuntimeError:
                # 没有事件循环，创建新的
                asyncio.run(self.build_tools())
                
            logger.info(f"🔧 同步初始化完成，工具数量: {len(self.openai_tools)}")
            
        except Exception as e:
            logger.error(f"❌ 同步初始化工具时发生错误: {e}")
            # 即使失败也要记录服务器信息
            for server_name in self.mcp_servers:
                logger.info(f"🔧 注册HTTP MCP服务器: {server_name}")
            
            for server_name in self.stdio_mcp_servers:
                logger.info(f"🔧 注册stdio MCP服务器: {server_name}")
            
            logger.info(f"🔧 同步初始化完成（有错误），工具数量: {len(self.openai_tools)}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口，清理所有资源"""
        await self.cleanup_stdio_clients()

    async def close(self):
        """手动关闭，清理所有资源"""
        await self.cleanup_stdio_clients()

    def __del__(self):
        """析构函数，确保资源被清理"""
        if hasattr(self, '_stdio_clients') and self._stdio_clients:
            logger.warning(f"⚠️ McpToolExecute 实例被销毁但仍有 {len(self._stdio_clients)} 个未清理的stdio客户端")

    def _get_client_cache_key(self, command: str, alias: str, config_dir: str) -> str:
        """生成客户端缓存键"""
        return f"{command}:{alias}:{config_dir}"

    async def _get_or_create_stdio_client(self, command: str, alias: str, config_dir: str):
        """获取或创建 stdio 客户端（带缓存）"""
        cache_key = self._get_client_cache_key(command, alias, config_dir)
        
        # 检查是否已有客户端
        if cache_key in self._stdio_clients:
            client = self._stdio_clients[cache_key]
            # 简化检查：只要客户端不为空就返回
            if client is not None:
                logger.debug(f"🔄 复用已缓存的stdio客户端: {cache_key}")
                return client
            else:
                # 客户端为空，从缓存中移除
                logger.debug(f"🧹 移除空的stdio客户端: {cache_key}")
                await self._remove_stdio_client(cache_key)

        # 获取或创建锁
        if cache_key not in self._client_locks:
            self._client_locks[cache_key] = asyncio.Lock()
        
        # 使用锁确保只有一个协程创建客户端
        async with self._client_locks[cache_key]:
            # 双重检查，防止在等待锁的过程中其他协程已经创建了客户端
            if cache_key in self._stdio_clients:
                client = self._stdio_clients[cache_key]
                if hasattr(client, '_session') and not getattr(client, '_closed', False):
                    logger.debug(f"🔄 复用刚创建的stdio客户端: {cache_key}")
                    return client
            
            # 创建新客户端
            logger.info(f"🆕 创建新的stdio客户端: {cache_key}")
            from mcp_framework.client.simple import SimpleClient
            logger.info(f"🆕 参数: command={command}, alias={alias}, config_dir={config_dir}")
            # 增加超时时间：启动超时 10 秒，响应超时 60 秒
            client = SimpleClient(
                command, 
                alias=alias, 
                config_dir=config_dir,
                startup_timeout=10.0,
                response_timeout=60.0
            )
            await client.__aenter__()  # 初始化客户端
            
            # 缓存客户端
            self._stdio_clients[cache_key] = client
            logger.info(f"✅ stdio客户端已缓存: {cache_key}")
            
            return client

    async def _remove_stdio_client(self, cache_key: str):
        """移除指定的 stdio 客户端"""
        async with self._cleanup_lock:
            if cache_key in self._stdio_clients:
                client = self._stdio_clients[cache_key]
                try:
                    # 清理客户端资源
                    if hasattr(client, '__aexit__'):
                        await client.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"⚠️ 清理stdio客户端时出现警告 {cache_key}: {e}")
                
                # 从缓存中移除
                del self._stdio_clients[cache_key]
                logger.debug(f"🧹 已移除stdio客户端: {cache_key}")

    async def cleanup_stdio_clients(self):
        """清理所有 stdio 客户端"""
        async with self._cleanup_lock:
            logger.info(f"🧹 开始清理所有stdio客户端，共 {len(self._stdio_clients)} 个")
            
            for cache_key in list(self._stdio_clients.keys()):
                await self._remove_stdio_client(cache_key)
            
            # 清理锁
            self._client_locks.clear()
            logger.info(f"✅ 所有stdio客户端已清理完成")

    def find_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """查找工具信息"""
        return self.tool_metadata.get(tool_name)
    
    async def _fetch_tools(self, server_url: str) -> Optional[Dict[str, Any]]:
        """从HTTP MCP服务器获取工具列表"""
        try:
            request = {
                'jsonrpc': '2.0',
                'id': f"req_{uuid.uuid4().hex[:16]}",
                'method': 'tools/list',
                'params': {}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(server_url, json=request, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"HTTP错误 {response.status} 从 {server_url}")
                        return None
                    
                    data = await response.json()
                    if 'error' in data:
                        logger.error(f"MCP错误: {data['error']}")
                        return None
                    
                    return data.get('result', {})
        except Exception as e:
            logger.error(f"获取工具列表失败 {server_url}: {e}")
            return None
    
    def _convert_to_openai_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """将MCP工具格式转换为OpenAI工具格式"""
        return {
            "type": "function",
            "function": {
                "name": tool['name'],
                "description": tool.get('description', ''),
                "parameters": tool.get('input_schema', tool.get('inputSchema', tool.get('parameters', {})))
            }
        }
    
    async def _call_tool(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用HTTP MCP服务器的工具"""
        try:
            request = {
                'jsonrpc': '2.0',
                'id': f"req_{uuid.uuid4().hex[:16]}",
                'method': 'tools/call',
                'params': {
                    'name': tool_name,
                    'arguments': arguments or {}
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(server_url, json=request, timeout=30) as response:
                    if response.status != 200:
                        return f"❌ HTTP错误 {response.status}"
                    
                    data = await response.json()
                    if 'error' in data:
                        return f"❌ MCP错误: {data['error'].get('message', '未知错误')}"
                    
                    result = data.get('result', {})
                    if isinstance(result, dict):
                        # 处理MCP标准响应格式
                        content = result.get('content', [])
                        if content and isinstance(content, list):
                            return '\n'.join([item.get('text', str(item)) for item in content])
                        else:
                            return str(result)
                    else:
                        return str(result)
        except Exception as e:
            logger.error(f"调用HTTP工具失败 {tool_name}: {e}")
            return f"❌ 调用工具失败: {str(e)}"

    async def call_stdio_tool_stream(self, server_name: str, command: str, alias: str, tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """使用 stdio 协议调用工具（流式版本，带客户端缓存）"""
        client = None
        
        try:
            logger.info(f"🔧 开始stdio工具调用: {tool_name} on {server_name} (alias: {alias})")
            
            # 获取或创建缓存的客户端
            client = await self._get_or_create_stdio_client(command, alias, self.config_dir)
            
            # 使用缓存的客户端进行流式调用
            logger.debug(f"🔧 使用缓存客户端调用工具: {tool_name}")
            async for chunk in client.call_stream(tool_name, **arguments):
                yield chunk
                    
        except Exception as e:
            logger.error(f"❌ stdio工具调用失败 {tool_name}: {e}")
            
            # 如果是客户端相关错误，尝试移除缓存的客户端
            if client:
                cache_key = self._get_client_cache_key(command, alias, self.config_dir)
                logger.warning(f"⚠️ 移除可能失效的stdio客户端: {cache_key}")
                await self._remove_stdio_client(cache_key)
            
            error_msg = f"Error calling stdio tool {tool_name}: {str(e)}"
            yield error_msg

    async def _call_tool_stream(self, server_url: str, tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """调用HTTP MCP服务器的工具（流式版本）"""
        try:
            request = {
                'jsonrpc': '2.0',
                'id': f"req_{uuid.uuid4().hex[:16]}",
                'method': 'tools/call',
                'params': {
                    'name': tool_name,
                    'arguments': arguments or {}
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(server_url, json=request, timeout=30) as response:
                    if response.status != 200:
                        yield f"❌ HTTP错误 {response.status}"
                        return
                    
                    data = await response.json()
                    if 'error' in data:
                        yield f"❌ MCP错误: {data['error'].get('message', '未知错误')}"
                        return
                    
                    result = data.get('result', {})
                    if isinstance(result, dict):
                        # 处理MCP标准响应格式
                        content = result.get('content', [])
                        if content and isinstance(content, list):
                            for item in content:
                                yield item.get('text', str(item))
                        else:
                            yield str(result)
                    else:
                        yield str(result)
        except Exception as e:
            logger.error(f"调用HTTP工具失败 {tool_name}: {e}")
            yield f"❌ 调用工具失败: {str(e)}"

    async def call_stdio_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用 stdio 协议的工具（非流式）"""
        result_parts = []
        async for chunk in self.call_stdio_tool_stream(tool_name, arguments):
            result_parts.append(chunk)
        return ''.join(result_parts)

    async def build_tools(self):
        """构建工具列表"""
        try:
            self.openai_tools = []
            self.tool_metadata = {}

            logger.info(f"🔧 开始构建工具列表，配置的HTTP MCP服务器数量: {len(self.mcp_servers)}, stdio MCP服务器数量: {len(self.stdio_mcp_servers)}")

            # 处理 HTTP 协议的 MCP 服务器
            for server_name, mcp_server in self.mcp_servers.items():
                try:
                    server_url = mcp_server['url']
                    logger.info(f"🔧 正在从HTTP MCP服务器获取工具: {server_name} ({server_url})")

                    # 调用MCP服务获取tools
                    request = {
                        'jsonrpc': '2.0',
                        'id': f"req_{uuid.uuid4().hex[:16]}",
                        'method': 'tools/list',
                        'params': {}
                    }
                    
                    # 如果设置了role，添加到请求参数中
                    if self.role:
                        request['params']['role'] = self.role

                    async with aiohttp.ClientSession() as session:
                        async with session.post(server_url, json=request, timeout=30) as response:
                            if response.status != 200:
                                logger.warning(
                                    f"❌ Failed to get tools from {server_name}: HTTP {response.status}")
                                continue

                            data = await response.json()
                            if 'error' in data:
                                logger.warning(
                                    f"❌ MCP tools/list failed for {server_name}: {data['error']['message']}")
                                continue

                            result = data.get('result', {})
                            server_tools = result.get('tools', []) if isinstance(result, dict) else []
                            logger.info(f"✅ 从HTTP服务器 {server_name} 获取到 {len(server_tools)} 个工具")

                            # 转换为OpenAI工具格式
                            for tool in server_tools:
                                prefixed_name = f"{server_name}_{tool['name']}"

                                openai_tool = {
                                    'type': 'function',
                                    'function': {
                                        'name': prefixed_name,
                                        'description': tool.get('description', ''),
                                        'parameters': tool.get('inputSchema', tool.get('parameters', {}))
                                    }
                                }

                                # 存储元数据
                                self.tool_metadata[prefixed_name] = {
                                    'original_name': tool['name'],
                                    'server_name': server_name,
                                    'server_url': server_url,
                                    'protocol': 'http'
                                }

                                self.openai_tools.append(openai_tool)
                                logger.info(f"  - 添加HTTP工具: {prefixed_name} ({tool.get('description', '')})")

                except Exception as e:
                    logger.error(f"❌ Failed to get tools from HTTP MCP server {server_name}: {e}")
                    continue

            # 处理 stdio 协议的 MCP 服务器
            for server_name, stdio_server in self.stdio_mcp_servers.items():
                try:
                    command = stdio_server['command']
                    alias = stdio_server.get('alias', server_name)  # 使用配置中的 alias，如果没有则使用 server_name
                    logger.info(f"🔧 正在从stdio MCP服务器获取工具: {server_name} ({command}) alias: {alias}")

                    # 使用缓存的 SimpleClient 获取工具列表
                    from mcp_framework.client.simple import SimpleClient
                    
                    # 获取或创建缓存的客户端
                    client = await self._get_or_create_stdio_client(command, alias, self.config_dir)
                    
                    try:
                        # 获取工具列表
                        tool_names = await client.tools()
                        
                        if tool_names:
                            logger.info(f"✅ 从stdio服务器 {server_name} 获取到 {len(tool_names)} 个工具")

                            # 转换为OpenAI工具格式
                            for tool_name in tool_names:
                                # 获取工具详细信息
                                tool_info = await client.tool_info(tool_name)
                                
                                prefixed_name = f"{server_name}_{tool_name}"

                                openai_tool = {
                                    'type': 'function',
                                    'function': {
                                        'name': prefixed_name,
                                        'description': tool_info.description if tool_info else '',
                                        'parameters': tool_info.input_schema if tool_info and hasattr(tool_info, 'input_schema') else {}
                                    }
                                }

                                # 存储元数据
                                self.tool_metadata[prefixed_name] = {
                                    'original_name': tool_name,
                                    'server_name': server_name,
                                    'command': command,
                                    'alias': alias,
                                    'protocol': 'stdio'
                                }

                                self.openai_tools.append(openai_tool)
                                logger.info(f"  - 添加stdio工具: {prefixed_name} ({tool_info.description if tool_info else ''})")
                        else:
                            logger.warning(f"❌ 从stdio服务器 {server_name} 获取工具列表失败: 无工具返回")
                    
                    except Exception as client_error:
                        # 如果客户端出现问题，从缓存中移除
                        cache_key = self._get_client_cache_key(command, alias, self.config_dir)
                        await self._remove_stdio_client(cache_key)
                        logger.error(f"❌ 使用缓存客户端获取工具失败，已从缓存移除: {client_error}")
                        raise client_error
                        
                except Exception as e:
                    logger.error(f"❌ Failed to get tools from stdio MCP server {server_name}: {e}")
                    continue

            logger.info(f"🎯 工具构建完成，共加载 {len(self.openai_tools)} 个工具")
        except Exception as e:
            logger.error(f"❌ 构建工具列表时发生错误: {e}")
            raise

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        return self.openai_tools

    async def execute_stream_generator(self, tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """执行工具（流式生成器），支持 HTTP 和 stdio 协议"""
        logger.info(f"🔧 [MCP_STREAM] Starting streaming tool execution: {tool_name}")
        logger.info(f"🔧 [MCP_STREAM] Tool arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        
        chunk_count = 0
        total_length = 0
        
        # 检查是否为内置工具
        if tool_name in self.tool_handlers:
            logger.info(f"🔧 [MCP_STREAM] Using built-in tool handler for: {tool_name}")
            handler = self.tool_handlers[tool_name]
            if asyncio.iscoroutinefunction(handler):
                async for chunk in handler(arguments):
                    chunk_count += 1
                    total_length += len(chunk)
                    logger.debug(f"🔧 [MCP_STREAM] Built-in chunk #{chunk_count}: {len(chunk)} chars")
                    yield chunk
            else:
                result = handler(arguments)
                if hasattr(result, '__aiter__'):
                    async for chunk in result:
                        chunk_count += 1
                        total_length += len(chunk)
                        logger.debug(f"🔧 [MCP_STREAM] Built-in chunk #{chunk_count}: {len(chunk)} chars")
                        yield chunk
                else:
                    chunk = str(result)
                    chunk_count += 1
                    total_length += len(chunk)
                    logger.debug(f"🔧 [MCP_STREAM] Built-in single chunk: {len(chunk)} chars")
                    yield chunk
            
            logger.info(f"🔧 [MCP_STREAM] Built-in tool completed - {chunk_count} chunks, {total_length} total chars")
            return

        # 查找工具信息
        tool_info = self.find_tool_info(tool_name)
        if not tool_info:
            error_msg = f"❌ 工具 '{tool_name}' 未找到"
            logger.error(f"🔧 [MCP_STREAM] {error_msg}")
            yield error_msg
            return

        protocol = tool_info.get('protocol')
        logger.info(f"🔧 [MCP_STREAM] Using protocol: {protocol}")
        
        if protocol == 'stdio':
            # 使用 stdio 协议调用
            server_name = tool_info.get('server_name')
            command = tool_info.get('command')
            alias = tool_info.get('alias')
            logger.info(f"🔧 [MCP_STREAM] Stdio config - server: {server_name}, command: {command}, alias: {alias}")
            
            async for chunk in self.call_stdio_tool_stream(server_name, command, alias, tool_name, arguments):
                chunk_count += 1
                total_length += len(chunk)
                logger.debug(f"🔧 [MCP_STREAM] Stdio chunk #{chunk_count}: {len(chunk)} chars")
                yield chunk
            
            logger.info(f"🔧 [MCP_STREAM] Stdio tool completed - {chunk_count} chunks, {total_length} total chars")
            
        elif protocol == 'http':
            # 使用 HTTP 协议调用
            server_config = tool_info.get('server_config', {})
            url = server_config.get('url')
            if not url:
                error_msg = f"❌ 工具 '{tool_name}' 缺少 URL 配置"
                logger.error(f"🔧 [MCP_STREAM] {error_msg}")
                yield error_msg
                return
            
            logger.info(f"🔧 [MCP_STREAM] HTTP URL: {url}")
            
            try:
                async for chunk in self._call_tool_stream(url, tool_name, arguments):
                    chunk_count += 1
                    total_length += len(chunk)
                    logger.debug(f"🔧 [MCP_STREAM] HTTP chunk #{chunk_count}: {len(chunk)} chars")
                    yield chunk
                
                logger.info(f"🔧 [MCP_STREAM] HTTP tool completed - {chunk_count} chunks, {total_length} total chars")
                
            except Exception as e:
                error_msg = f"❌ 调用工具失败: {str(e)}"
                logger.error(f"🔧 [MCP_STREAM] HTTP tool failed {tool_name}: {e}")
                yield error_msg
        else:
            error_msg = f"❌ 不支持的协议类型: {protocol}"
            logger.error(f"🔧 [MCP_STREAM] {error_msg}")
            yield error_msg

    def execute_sync(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具（非流式，同步版本）"""
        logger.info(f"🔧 [MCP_EXECUTE] Starting sync tool execution: {tool_name}")
        logger.info(f"🔧 [MCP_EXECUTE] Tool arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        
        # 检查是否为内置工具
        if tool_name in self.tool_handlers:
            logger.info(f"🔧 [MCP_EXECUTE] Using built-in tool handler for: {tool_name}")
            handler = self.tool_handlers[tool_name]
            
            # 对于同步版本，我们简化处理
            if asyncio.iscoroutinefunction(handler):
                # 异步handler，返回模拟结果
                result = f"Tool {tool_name} executed with arguments: {json.dumps(arguments, ensure_ascii=False)}"
                logger.info(f"🔧 [MCP_EXECUTE] Built-in async tool mock result length: {len(result)} chars")
                return result
            else:
                result = handler(arguments)
                final_result = str(result)
                logger.info(f"🔧 [MCP_EXECUTE] Built-in tool result length: {len(final_result)} chars")
                return final_result

        # 查找工具信息
        tool_info = self.find_tool_info(tool_name)
        if not tool_info:
            error_msg = f"❌ 工具 '{tool_name}' 未找到"
            logger.error(f"🔧 [MCP_EXECUTE] {error_msg}")
            return error_msg

        protocol = tool_info.get('protocol')
        
        if protocol == 'stdio':
            # 对于stdio协议，返回模拟结果
            logger.info(f"🔧 [MCP_EXECUTE] Using stdio protocol for tool: {tool_name} (sync mode)")
            result = f"Stdio tool {tool_name} executed with arguments: {json.dumps(arguments, ensure_ascii=False)}"
            logger.info(f"🔧 [MCP_EXECUTE] Stdio tool mock result length: {len(result)} chars")
            return result
        elif protocol == 'http':
            # 对于HTTP协议，返回模拟结果
            logger.info(f"🔧 [MCP_EXECUTE] Using HTTP protocol for tool: {tool_name} (sync mode)")
            result = f"HTTP tool {tool_name} executed with arguments: {json.dumps(arguments, ensure_ascii=False)}"
            logger.info(f"🔧 [MCP_EXECUTE] HTTP tool mock result length: {len(result)} chars")
            return result
        else:
            error_msg = f"❌ 不支持的协议类型: {protocol}"
            logger.error(f"🔧 [MCP_EXECUTE] {error_msg}")
            return error_msg

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具（非流式），支持 HTTP 和 stdio 协议"""
        logger.info(f"🔧 [MCP_EXECUTE] Starting tool execution: {tool_name}")
        logger.info(f"🔧 [MCP_EXECUTE] Tool arguments: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        
        # 检查是否为内置工具
        if tool_name in self.tool_handlers:
            logger.info(f"🔧 [MCP_EXECUTE] Using built-in tool handler for: {tool_name}")
            handler = self.tool_handlers[tool_name]
            if asyncio.iscoroutinefunction(handler):
                result_parts = []
                async for chunk in handler(arguments):
                    result_parts.append(chunk)
                result = ''.join(result_parts)
                logger.info(f"🔧 [MCP_EXECUTE] Built-in tool result length: {len(result)} chars")
                logger.debug(f"🔧 [MCP_EXECUTE] Built-in tool result: {result[:500]}{'...' if len(result) > 500 else ''}")
                return result
            else:
                result = handler(arguments)
                if hasattr(result, '__aiter__'):
                    result_parts = []
                    async for chunk in result:
                        result_parts.append(chunk)
                    final_result = ''.join(result_parts)
                    logger.info(f"🔧 [MCP_EXECUTE] Built-in tool result length: {len(final_result)} chars")
                    logger.debug(f"🔧 [MCP_EXECUTE] Built-in tool result: {final_result[:500]}{'...' if len(final_result) > 500 else ''}")
                    return final_result
                else:
                    final_result = str(result)
                    logger.info(f"🔧 [MCP_EXECUTE] Built-in tool result length: {len(final_result)} chars")
                    logger.debug(f"🔧 [MCP_EXECUTE] Built-in tool result: {final_result[:500]}{'...' if len(final_result) > 500 else ''}")
                    return final_result

        # 查找工具信息
        tool_info = self.find_tool_info(tool_name)
        if not tool_info:
            error_msg = f"❌ 工具 '{tool_name}' 未找到"
            logger.error(f"🔧 [MCP_EXECUTE] {error_msg}")
            return error_msg

        protocol = tool_info.get('protocol')
        
        if protocol == 'stdio':
            # 使用 stdio 协议调用
            logger.info(f"🔧 [MCP_EXECUTE] Using stdio protocol for tool: {tool_name}")
            tool_info = self.find_tool_info(tool_name)
            server_name = tool_info.get('server_name')
            command = tool_info.get('command')
            alias = tool_info.get('alias')
            original_name = tool_info.get('original_name', tool_name)
            
            logger.info(f"🔧 [MCP_EXECUTE] Stdio tool config - server: {server_name}, command: {command}, alias: {alias}")
            
            result_parts = []
            async for chunk in self.call_stdio_tool_stream(server_name, command, alias, original_name, arguments):
                result_parts.append(chunk)
            
            result = ''.join(result_parts)
            logger.info(f"🔧 [MCP_EXECUTE] Stdio tool result length: {len(result)} chars")
            logger.debug(f"🔧 [MCP_EXECUTE] Stdio tool result: {result[:500]}{'...' if len(result) > 500 else ''}")
            return result
        elif protocol == 'http':
            # 使用 HTTP 协议调用
            logger.info(f"🔧 [MCP_EXECUTE] Using HTTP protocol for tool: {tool_name}")
            server_config = tool_info.get('server_config', {})
            url = server_config.get('url')
            if not url:
                error_msg = f"❌ 工具 '{tool_name}' 缺少 URL 配置"
                logger.error(f"🔧 [MCP_EXECUTE] {error_msg}")
                return error_msg
            
            logger.info(f"🔧 [MCP_EXECUTE] HTTP tool URL: {url}")
            
            try:
                result = await self._call_tool(url, tool_name, arguments)
                logger.info(f"🔧 [MCP_EXECUTE] HTTP tool result length: {len(result)} chars")
                logger.debug(f"🔧 [MCP_EXECUTE] HTTP tool result: {result[:500]}{'...' if len(result) > 500 else ''}")
                return result
            except Exception as e:
                error_msg = f"❌ 调用工具失败: {str(e)}"
                logger.error(f"🔧 [MCP_EXECUTE] HTTP tool failed {tool_name}: {e}")
                return error_msg
        else:
            error_msg = f"❌ 不支持的协议类型: {protocol}"
            logger.error(f"🔧 [MCP_EXECUTE] {error_msg}")
            return error_msg


# 示例工具注册
def create_example_mcp_executor() -> McpToolExecute:
    """创建示例MCP执行器"""
    executor = McpToolExecute()
    
    # 示例工具
    example_tools = [
        ToolInfo(
            name="echo",
            description="Echo the input text",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo"
                    }
                },
                "required": ["text"]
            },
            supports_streaming=False
        ),
        ToolInfo(
            name="stream_echo",
            description="Echo the input text with streaming",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to echo with streaming"
                    }
                },
                "required": ["text"]
            },
            supports_streaming=True
        )
    ]
    
    # 注册示例服务器
    example_server = McpServer(
        name="example",
        description="Example MCP server",
        version="1.0.0",
        tools=example_tools
    )
    
    executor.register_server(example_server)
    
    # 注册工具处理器
    async def echo_handler(arguments: Dict[str, Any]) -> str:
        return arguments.get("text", "")
    
    async def stream_echo_handler(
        arguments: Dict[str, Any],
        on_chunk: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> str:
        text = arguments.get("text", "")
        
        # 模拟流式输出
        for char in text:
            if on_chunk:
                on_chunk(char)
            await asyncio.sleep(0.01)  # 模拟延迟
        
        if on_complete:
            on_complete(text)
            
        return text
    
    executor.register_tool_handler("echo", echo_handler)
    executor.register_tool_handler("stream_echo", stream_echo_handler)
    
    return executor