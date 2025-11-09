"""
Agent 封装类
提供简单易用的 Agent 接口，封装所有复杂的配置和调用逻辑
同时内聚 MCP 服务器初始化逻辑，支持根据 user_id 加载配置。
"""

import json
import logging
import os
import queue
import threading
from datetime import datetime
import time
from typing import Dict, List, Any, Optional, Callable
from openai import OpenAI

from .message_manager import MessageManager
from .ai_request_handler import AiRequestHandler
from .tool_result_processor import ToolResultProcessor
from .mcp_tool_execute import McpToolExecute
from .ai_client import AiClient

# 直接使用项目内的配置模型，按需加载 MCP 配置
try:
    from app.models.config import McpConfigCreate, McpConfigProfileActivate
except Exception:
    McpConfigCreate = None
    McpConfigProfileActivate = None

# 智能体/模型/系统上下文配置，用于按 agent_id 封装模型配置
try:
    from app.models.config import AgentCreate, AiModelConfigCreate, SystemContextCreate
except Exception:
    AgentCreate = None
    AiModelConfigCreate = None
    SystemContextCreate = None

logger = logging.getLogger(__name__)


class AgentConfig:
    """Agent 配置类"""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model_name: str = "gpt-4",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        mcp_servers: Optional[List[Dict[str, Any]]] = None,
        stdio_mcp_servers: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
    ):
        """
        初始化 Agent 配置

        Args:
            api_key: OpenAI API 密钥
            base_url: API 基础 URL（可选）
            model_name: 模型名称
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大 token 数
            mcp_servers: HTTP MCP 服务器列表
            stdio_mcp_servers: STDIO MCP 服务器列表
            user_id: 用户ID（用于按用户加载 MCP 配置）
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.mcp_servers = mcp_servers or []
        self.stdio_mcp_servers = stdio_mcp_servers or []
        self.user_id = user_id


class Agent:
    """
    Agent 封装类
    提供简单的接口来执行带工具调用的对话
    """

    def __init__(self, config: AgentConfig):
        """
        初始化 Agent

        Args:
            config: Agent 配置对象
        """
        self.config = config

        # 初始化 OpenAI 客户端
        client_kwargs = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url
        self.openai_client = OpenAI(**client_kwargs)

        # 初始化 MCP 工具执行器（支持在此处根据 user_id 组装配置）
        mcp_servers, stdio_mcp_servers = self._resolve_mcp_servers(config)

        self.mcp_tool_execute = McpToolExecute(
            mcp_servers=mcp_servers,
            stdio_mcp_servers=stdio_mcp_servers,
        )
        self.mcp_tool_execute.init()

        # 初始化各个组件
        self.message_manager = MessageManager()
        self.ai_request_handler = AiRequestHandler(
            self.openai_client, self.message_manager
        )
        self.tool_result_processor = ToolResultProcessor(
            self.message_manager, self.ai_request_handler
        )
        self.ai_client = AiClient(
            self.ai_request_handler,
            self.mcp_tool_execute,
            self.tool_result_processor,
            self.message_manager,
        )

        print(
            f"[AGENT] 初始化完成 - 模型: {config.model_name}, 可用工具数: {len(self.mcp_tool_execute.get_available_tools())}"
        )

    def _resolve_mcp_servers(self, config: AgentConfig) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        解析 MCP 服务器配置：
        - 若传入了 mcp_servers/stdio_mcp_servers，则直接使用
        - 否则尝试根据 user_id 加载；若无法加载，则返回空列表
        """
        # 已提供则直接用
        if config.mcp_servers or config.stdio_mcp_servers:
            return config.mcp_servers, config.stdio_mcp_servers

        # 未提供，尝试按 user_id 加载
        if McpConfigCreate is None:
            logger.warning("McpConfigCreate 未可用，跳过自动加载 MCP 配置")
            return [], []

        http_servers, stdio_servers = self._load_mcp_configs_for_user(config.user_id)

        # 转换为本 Agent 需要的结构
        mcp_servers = [{"name": name, "url": cfg["url"]} for name, cfg in http_servers.items()]
        stdio_mcp_servers = [
            {
                "name": name,
                "command": cfg["command"],
                "args": cfg.get("args"),
                "env": cfg.get("env"),
                "cwd": cfg.get("cwd"),
            }
            for name, cfg in stdio_servers.items()
        ]

        return mcp_servers, stdio_mcp_servers

    def _load_mcp_configs_for_user(self, user_id: Optional[str]) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """按用户加载 MCP 配置，返回 HTTP/STDIO 服务器字典。"""
        try:
            configs = _asyncio_run(McpConfigCreate.get_all(user_id=user_id))
            configs = [c for c in configs if c.get('enabled')]

            http_servers: Dict[str, Dict[str, Any]] = {}
            stdio_servers: Dict[str, Dict[str, Any]] = {}

            for config in configs:
                server_name = config['name']
                server_alias = f"{server_name}_{config['id'][:8]}"
                command = config['command']
                server_type = config.get('type', 'stdio')

                try:
                    args = json.loads(config.get('args', '[]')) if isinstance(config.get('args'), str) else (config.get('args') or [])
                except json.JSONDecodeError:
                    args = config.get('args', []) or []

                try:
                    env = json.loads(config.get('env', '{}')) if isinstance(config.get('env'), str) else (config.get('env') or {})
                except json.JSONDecodeError:
                    env = config.get('env', {}) or {}

                if server_type == 'http':
                    http_servers[server_alias] = {
                        'url': command,
                        'args': args,
                        'env': env
                    }
                else:
                    cwd = config.get('cwd')
                    # 覆盖为激活的 Profile
                    active_profile = None
                    try:
                        if McpConfigProfileActivate:
                            active_profile = _asyncio_run(McpConfigProfileActivate.get_active(config['id']))
                    except Exception:
                        active_profile = None
                    if active_profile:
                        prof_args = active_profile.get('args') or []
                        prof_env = active_profile.get('env') or {}
                        prof_cwd = active_profile.get('cwd')
                        if prof_args:
                            args = prof_args
                        if prof_env:
                            env = prof_env
                        if prof_cwd:
                            cwd = prof_cwd

                    stdio_servers[server_alias] = {
                        'command': command,
                        'args': args,
                        'env': env,
                        'cwd': cwd
                    }

            try:
                logger.info(f"✅ Agent 加载 MCP 配置完成: HTTP {len(http_servers)} 个, STDIO {len(stdio_servers)} 个 (user_id={user_id})")
            except Exception:
                pass
            return http_servers, stdio_servers

        except Exception as e:
            logger.error(f"❌ Agent 加载 MCP 配置失败: {e}")
            return {}, {}

    def run(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_tools: bool = True,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_tools_start: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        on_tools_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_tools_end: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        运行 Agent，处理消息并返回结果

        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}, ...]
            session_id: 会话 ID（可选，如果不提供则自动生成）
            tools: 自定义工具列表（可选，如果不提供则使用 MCP 工具）
            use_tools: 是否使用工具
            on_chunk: 流式响应回调
            on_tools_start: 工具开始调用回调
            on_tools_stream: 工具流式内容回调
            on_tools_end: 工具结束回调
            model_name: 模型名称（可选，覆盖配置）
            temperature: 温度参数（可选，覆盖配置）
            max_tokens: 最大 token 数（可选，覆盖配置）

        Returns:
            执行结果
        """
        try:
            # 生成会话 ID
            if not session_id:
                session_id = f"agent_session_{int(time.time() * 1000)}"

            print(
                f"[AGENT] 开始运行 - 会话ID: {session_id}, 消息数: {len(messages)}"
            )

            # 准备消息列表
            prepared_messages = self._prepare_messages(messages)

            # 使用参数或配置中的值
            actual_model = model_name or self.config.model_name
            actual_temperature = (
                temperature if temperature is not None else self.config.temperature
            )
            actual_max_tokens = max_tokens or self.config.max_tokens

            # 确定使用的工具
            actual_tools = None
            if use_tools:
                if tools is not None:
                    actual_tools = tools
                else:
                    actual_tools = self.mcp_tool_execute.get_available_tools()

            print(
                f"[AGENT] 配置 - 模型: {actual_model}, 温度: {actual_temperature}, 工具数: {len(actual_tools) if actual_tools else 0}"
            )

            # 如果没有工具，直接调用 AI
            if not actual_tools:
                return self._run_without_tools(
                    messages=prepared_messages,
                    session_id=session_id,
                    model=actual_model,
                    temperature=actual_temperature,
                    max_tokens=actual_max_tokens,
                    on_chunk=on_chunk,
                )

            # 使用工具执行
            result = self.ai_client.process_request(
                messages=prepared_messages,
                session_id=session_id,
                model=actual_model,
                temperature=actual_temperature,
                max_tokens=actual_max_tokens,
                on_chunk=on_chunk,
                on_tools_start=on_tools_start,
                on_tools_stream=on_tools_stream,
                on_tools_end=on_tools_end,
            )

            print(
                f"[AGENT] 运行完成 - 会话ID: {session_id}, 成功: {result.get('success', False)}"
            )

            return result

        except Exception as e:
            error_message = f"Agent 运行失败: {str(e)}"
            print(f"[AGENT] 错误: {error_message}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": error_message,
            }

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        简化的聊天接口

        Args:
            user_message: 用户消息
            session_id: 会话 ID（可选）
            conversation_history: 对话历史（可选）
            **kwargs: 其他参数，传递给 run 方法

        Returns:
            执行结果
        """
        # 构建消息列表
        messages = conversation_history or []

        # 添加用户消息
        messages.append({"role": "user", "content": user_message})

        return self.run(messages=messages, session_id=session_id, **kwargs)

    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        准备消息列表，添加系统提示词

        Args:
            messages: 原始消息列表

        Returns:
            处理后的消息列表
        """
        prepared: List[Dict[str, Any]] = []

        # 添加系统提示词（如果配置了）
        if self.config.system_prompt:
            prepared.append({"role": "system", "content": self.config.system_prompt})

        # 添加其他消息
        prepared.extend(messages)

        return prepared

    def _run_without_tools(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        on_chunk: Optional[Callable[[str], None]],
    ) -> Dict[str, Any]:
        """
        不使用工具的简单执行

        Args:
            messages: 消息列表
            session_id: 会话 ID
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            on_chunk: 流式回调

        Returns:
            执行结果
        """
        try:
            print(f"[AGENT] 无工具模式运行 - 会话ID: {session_id}")

            response = self.ai_request_handler.handle_request(
                messages=messages,
                tools=None,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                session_id=session_id,
                on_chunk=on_chunk,
            )

            if response.get("success"):
                return {
                    "success": True,
                    "final_response": response,
                    "iterations": 1,
                    "has_tool_calls": False,
                }
            else:
                return {
                    "success": False,
                    "error": response.get("error", "AI 请求失败"),
                    "final_response": None,
                }

        except Exception as e:
            error_message = f"无工具执行失败: {str(e)}"
            print(f"[AGENT] 错误: {error_message}")
            return {"success": False, "error": error_message, "final_response": None}

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表

        Returns:
            工具列表
        """
        return self.mcp_tool_execute.get_available_tools()

    def get_conversation_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Args:
            session_id: 会话 ID
            limit: 消息数量限制

        Returns:
            消息列表
        """
        return self.message_manager.get_session_messages(session_id, limit)


def create_agent(
    api_key: str,
    base_url: Optional[str] = None,
    model_name: str = "gpt-4",
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    mcp_servers: Optional[List[Dict[str, Any]]] = None,
    stdio_mcp_servers: Optional[List[Dict[str, Any]]] = None,
    user_id: Optional[str] = None,
) -> Agent:
    """
    创建 Agent 的便捷函数

    Args:
        api_key: OpenAI API 密钥
        base_url: API 基础 URL（可选）
        model_name: 模型名称
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大 token 数
        mcp_servers: HTTP MCP 服务器列表
        stdio_mcp_servers: STDIO MCP 服务器列表

    Returns:
        Agent 实例
    """
    config = AgentConfig(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        mcp_servers=mcp_servers,
        stdio_mcp_servers=stdio_mcp_servers,
        user_id=user_id,
    )

    return Agent(config)


def _asyncio_run(coro):
    """在同步上下文中运行异步协程。"""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        import asyncio
        return asyncio.run(coro)


def build_sse_stream(
    session_id: str,
    content: str,
    model_config: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> "Generator[str, None, None]":
    """
    在 Agent 模块内封装 SSE 流式响应构建，减少路由层样板代码。

    事件类型：start/chunk/tools_start/tools_stream/tools_end/heartbeat/complete/error
    """
    try:
        api_key = (model_config or {}).get("api_key") or os.getenv("OPENAI_API_KEY") or ""
        base_url = (model_config or {}).get("base_url")

        agent = create_agent(
            api_key=api_key,
            base_url=base_url,
            model_name=(model_config or {}).get("model_name", "gpt-4"),
            system_prompt=(model_config or {}).get("system_prompt"),
            temperature=(model_config or {}).get("temperature", 0.7),
            max_tokens=(model_config or {}).get("max_tokens"),
            user_id=user_id,
        )

        event_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=1000)
        queue_lock = threading.Lock()

        def on_chunk(chunk: str):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("chunk", chunk), block=False)
            except Exception as e:
                logger.error(f"Error in chunk callback: {e}")

        def on_tools_start(tool_calls: List[Dict[str, Any]]):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("tools_start", {"tool_calls": tool_calls}), block=False)
            except Exception as e:
                logger.error(f"Error in tools_start callback: {e}")

        def on_tools_stream(result: Dict[str, Any]):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("tools_stream", result), block=False)
            except Exception as e:
                logger.error(f"Error in tools_stream callback: {e}")

        def on_tools_end(tool_results: List[Dict[str, Any]]):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("tools_end", {"tool_results": tool_results}), block=False)
            except Exception as e:
                logger.error(f"Error in tools_end callback: {e}")

        ai_completed = threading.Event()
        ai_error: Optional[Exception] = None
        ai_result: Optional[Dict[str, Any]] = None

        def ai_worker():
            nonlocal ai_error, ai_result
            try:
                model = (model_config or {}).get("model_name", "gpt-4")
                temperature = (model_config or {}).get("temperature", 0.7)
                max_tokens = (model_config or {}).get("max_tokens", 4000)
                use_tools = (model_config or {}).get("use_tools", True)

                ai_result = agent.chat(
                    user_message=content,
                    session_id=session_id,
                    model_name=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_tools=use_tools,
                    on_chunk=on_chunk,
                    on_tools_start=on_tools_start,
                    on_tools_stream=on_tools_stream,
                    on_tools_end=on_tools_end,
                )
            except Exception as e:
                ai_error = e
                logger.error(f"Error in AI worker: {e}", exc_info=True)
            finally:
                ai_completed.set()
                try:
                    with queue_lock:
                        event_queue.put(("ai_completed", None), block=False)
                except Exception:
                    pass

        # 启动后台线程
        t = threading.Thread(target=ai_worker, daemon=True)
        t.start()

        # start 事件
        start_event = {"type": "start", "session_id": session_id, "timestamp": datetime.now().isoformat()}
        yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"

        completed = False
        last_heartbeat = time.time()
        heartbeat_interval = 30

        while not completed:
            try:
                try:
                    event_type, data = event_queue.get(timeout=2.0)

                    if event_type == "chunk":
                        event_data = {"type": "chunk", "content": data, "timestamp": datetime.now().isoformat()}
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    elif event_type == "tools_start":
                        event_data = {"type": "tools_start", "data": data, "timestamp": datetime.now().isoformat()}
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    elif event_type == "tools_stream":
                        event_data = {"type": "tools_stream", "data": data, "timestamp": datetime.now().isoformat()}
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    elif event_type == "tools_end":
                        event_data = {"type": "tools_end", "data": data, "timestamp": datetime.now().isoformat()}
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    elif event_type == "ai_completed":
                        completed = True
                except queue.Empty:
                    if ai_completed.is_set():
                        completed = True
                    else:
                        now = time.time()
                        if now - last_heartbeat > heartbeat_interval:
                            hb = {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                            yield f"data: {json.dumps(hb, ensure_ascii=False)}\n\n"
                            last_heartbeat = now
            except Exception as e:
                logger.error(f"Error in stream loop: {e}", exc_info=True)
                err = {"type": "error", "error": str(e), "timestamp": datetime.now().isoformat()}
                yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
                break

        # 结束阶段
        if ai_error:
            final_event = {"type": "error", "error": str(ai_error), "timestamp": datetime.now().isoformat()}
        else:
            final_event = {"type": "complete", "result": ai_result, "timestamp": datetime.now().isoformat()}

        yield f"data: {json.dumps(final_event, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"Error creating stream response: {e}", exc_info=True)
        err_event = {"type": "error", "error": str(e), "timestamp": datetime.now().isoformat()}
        yield f"data: {json.dumps(err_event, ensure_ascii=False)}\n\n"


def load_model_config_for_agent(agent_id: str) -> Dict[str, Any]:
    """
    根据 agent_id 加载模型配置和系统提示，返回供 Agent 使用的 model_config 字典。

    返回示例：
    {
        "model_name": str,
        "api_key": Optional[str],
        "base_url": Optional[str],
        "temperature": float,
        "max_tokens": Optional[int],
        "system_prompt": Optional[str],
    }
    """
    if AgentCreate is None or AiModelConfigCreate is None:
        raise RuntimeError("模型/智能体配置模块不可用，无法按 agent_id 加载配置")

    agent = _asyncio_run(AgentCreate.get_by_id(agent_id))
    if not agent or not agent.get("enabled", True):
        raise ValueError("智能体不存在或未启用")

    ai_model_id = agent.get("ai_model_config_id")
    if not ai_model_id:
        raise ValueError("智能体缺少模型配置")

    model_cfg = _asyncio_run(AiModelConfigCreate.get_by_id(ai_model_id))
    if not model_cfg or not model_cfg.get("enabled", True):
        raise ValueError("模型配置不可用或未启用")

    # 系统提示
    system_prompt: Optional[str] = None
    system_context_id = agent.get("system_context_id")
    if system_context_id and SystemContextCreate is not None:
        sc = _asyncio_run(SystemContextCreate.get_by_id(system_context_id))
        if sc:
            is_active = sc.get("is_active")
            if is_active is None:
                is_active = sc.get("isActive", True)
            if is_active:
                system_prompt = sc.get("content")

    return {
        "model_name": model_cfg.get("model"),
        "api_key": model_cfg.get("api_key"),
        "base_url": model_cfg.get("base_url"),
        "temperature": 0.7,
        "max_tokens": 4000,
        "system_prompt": system_prompt,
    }


def build_sse_stream_from_agent_id(
    session_id: str,
    content: str,
    agent_id: str,
    user_id: Optional[str] = None,
) -> "Generator[str, None, None]":
    """
    根据 agent_id 封装 SSE 流构建，便于多处复用。
    """
    model_config = load_model_config_for_agent(agent_id)
    return build_sse_stream(
        session_id=session_id,
        content=content,
        model_config=model_config,
        user_id=user_id,
    )