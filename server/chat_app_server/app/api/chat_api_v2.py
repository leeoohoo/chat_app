#!/usr/bin/env python3
"""
Chat API v2 - 使用 v2 版本的服务
专门为 v2 版本的 AiServer 设计的路由
"""

import asyncio
import json
import logging
import os
import queue
import threading
import time
from typing import Dict, Any, Optional, Generator, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.v2.ai_server import AiServer
from ..services.v2.mcp_tool_execute import McpToolExecute
from ..models.database_factory import get_database
from ..models.message import MessageCreate
from ..models.config import McpConfigCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2")


# ===== 数据模型 =====

class ModelConfigV2(BaseModel):
    """v2 版本的模型配置"""
    model_config = {"protected_namespaces": ()}
    
    model_name: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=4000, gt=0, description="最大token数")
    use_tools: bool = Field(default=True, description="是否使用工具")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")


class ChatRequestV2(BaseModel):
    """v2 版本的聊天请求"""
    session_id: str = Field(description="会话ID")
    content: str = Field(description="消息内容")
    ai_model_config: Optional[ModelConfigV2] = Field(default=None, description="模型配置")
    user_id: Optional[str] = Field(default=None, description="用户ID，用于按用户加载MCP配置")


class ChatMessageV2(BaseModel):
    """v2 版本的聊天消息"""
    role: str = Field(description="角色")
    content: str = Field(description="内容")


class DirectChatRequestV2(BaseModel):
    """v2 版本的直接聊天请求"""
    session_id: str = Field(description="会话ID")
    messages: List[ChatMessageV2] = Field(description="消息列表")
    ai_model_config: Optional[ModelConfigV2] = Field(default=None, description="模型配置")


# ===== 全局变量 =====

# 全局 AI 服务器实例
ai_server: Optional[AiServer] = None

# 会话级别的 AI 服务器实例
_session_ai_servers: Dict[str, AiServer] = {}


# ===== 服务器管理函数 =====

def set_session_ai_server(session_id: str, server: AiServer) -> None:
    """设置会话级别的AI服务器"""
    global _session_ai_servers
    _session_ai_servers[session_id] = server


def get_session_ai_server(session_id: str) -> Optional[AiServer]:
    """获取会话级别的AI服务器"""
    global _session_ai_servers
    return _session_ai_servers.get(session_id)


def remove_session_ai_server(session_id: str) -> None:
    """移除会话级别的AI服务器"""
    global _session_ai_servers
    if session_id in _session_ai_servers:
        del _session_ai_servers[session_id]


def get_active_sessions() -> List[str]:
    """获取活跃会话列表"""
    global _session_ai_servers
    return list(_session_ai_servers.keys())


# ===== MCP 配置加载 =====

def load_mcp_configs_sync(user_id: Optional[str] = None) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """同步加载MCP配置（支持按用户过滤）"""
    try:
        # 使用模型的统一方法按需加载配置（异步方法在此同步调用）
        configs = asyncio.run(McpConfigCreate.get_all(user_id=user_id))

        # 仅保留启用的配置
        configs = [c for c in configs if c.get('enabled')]
        
        http_servers = {}
        stdio_servers = {}
        
        for config in configs:
            server_name = config['name']
            command = config['command']
            server_type = config.get('type', 'stdio')
            
            # 解析args和env
            try:
                args = json.loads(config.get('args', '[]')) if isinstance(config.get('args'), str) else (config.get('args') or [])
            except json.JSONDecodeError:
                args = config.get('args', []) or []
            
            try:
                env = json.loads(config.get('env', '{}')) if isinstance(config.get('env'), str) else (config.get('env') or {})
            except json.JSONDecodeError:
                env = config.get('env', {}) or {}
            
            if server_type == 'http':
                http_servers[server_name] = {
                    'url': command,
                    'args': args,
                    'env': env
                }
            else:
                actual_command = command
                alias = server_name
                
                if '--' in command:
                    parts = command.split('--', 1)
                    actual_command = parts[0].strip()
                    alias = parts[1].strip()
                
                stdio_servers[server_name] = {
                    'command': actual_command,
                    'alias': alias,
                    'args': args,
                    'env': env
                }
        
        logger.info(f"✅ v2 加载MCP配置完成: HTTP服务器 {len(http_servers)} 个, stdio服务器 {len(stdio_servers)} 个")
        return http_servers, stdio_servers
        
    except Exception as e:
        logger.error(f"❌ v2 加载MCP配置失败: {e}")
        return {}, {}


# ===== AI 服务器创建函数 =====

def get_ai_server_v2() -> AiServer:
    """获取 v2 版本的 AI 服务器实例"""
    global ai_server
    
    if ai_server is None:
        # 获取 OpenAI API 密钥
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY 环境变量未设置")
        
        # 加载 MCP 配置
        http_servers, stdio_servers = load_mcp_configs_sync()
        
        # 将 HTTP 配置转换为 mcp_servers 格式
        mcp_servers = []
        for name, config in http_servers.items():
            mcp_servers.append({
                "name": name,
                "url": config["url"]
            })
        
        # 将 stdio 配置转换为 stdio_mcp_servers 格式
        stdio_mcp_servers = []
        for name, config in stdio_servers.items():
            stdio_mcp_servers.append({
                "name": name,
                "command": config["command"],
                "alias": config["alias"],
                "args": config.get("args", []),
                "env": config.get("env", {})
            })
        
        # 设置配置目录
        config_dir = os.path.expanduser("~/.mcp_framework/configs")
        
        # 创建 MCP 执行器
        mcp_tool_execute = McpToolExecute(
            mcp_servers=mcp_servers,
            stdio_mcp_servers=stdio_mcp_servers,
            config_dir=config_dir
        )
        mcp_tool_execute.init()  # 初始化工具列表
        
        # 创建 v2 AI 服务器
        ai_server = AiServer(
            openai_api_key=openai_api_key,
            mcp_tool_execute=mcp_tool_execute,
            default_model="gpt-4",
            default_temperature=0.7
        )
        
        logger.info("✅ v2 AI 服务器实例创建成功")
    
    return ai_server


def get_ai_server_with_mcp_configs_v2(api_key: Optional[str] = None, base_url: Optional[str] = None, user_id: Optional[str] = None) -> AiServer:
    """获取带有 MCP 配置的 v2 AI 服务器实例"""
    # 加载 MCP 配置
    http_servers, stdio_servers = load_mcp_configs_sync(user_id=user_id)
    
    # 获取 API 密钥 - 优先使用传入的参数，其次使用环境变量
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    # 如果仍然没有API密钥，使用默认值（某些模型可能不需要）
    if not api_key:
        logger.warning("未提供API密钥，将使用空字符串作为默认值")
        api_key = ""
    
    # 创建带配置的 MCP 执行器
    # 将 HTTP 配置转换为 mcp_servers 格式
    mcp_servers = []
    for name, config in http_servers.items():
        mcp_servers.append({
            "name": name,
            "url": config["url"]
        })
    
    # 将 stdio 配置转换为 stdio_mcp_servers 格式
    stdio_mcp_servers = []
    for name, config in stdio_servers.items():
        stdio_mcp_servers.append({
            "name": name,
            "command": config["command"],
            "alias": config["alias"],
            "args": config.get("args", []),
            "env": config.get("env", {})
        })
    
    # 设置配置目录
    config_dir = os.path.expanduser("~/.mcp_framework/configs")
    
    mcp_tool_execute = McpToolExecute(
        mcp_servers=mcp_servers,
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir=config_dir
    )
    mcp_tool_execute.init()  # 初始化工具列表
    
    # 创建 v2 AI 服务器
    server = AiServer(
        openai_api_key=api_key,
        mcp_tool_execute=mcp_tool_execute,
        default_model="gpt-4",
        default_temperature=0.7,
        base_url=base_url
    )
    
    logger.info("✅ v2 带MCP配置的AI服务器实例创建成功")
    return server


# ===== 流式响应处理 =====

def create_stream_response_v2(
    session_id: str,
    content: str,
    model_config: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> Generator[str, None, None]:
    """
    创建 v2 版本的流式响应
    
    Args:
        session_id: 会话ID
        content: 消息内容
        model_config: 模型配置
        
    Yields:
        SSE格式的数据
    """
    try:
        # 从模型配置中提取API密钥和基础URL
        api_key = None
        base_url = None
        if model_config:
            if "api_key" in model_config:
                api_key = model_config["api_key"]
            if "base_url" in model_config:
                base_url = model_config["base_url"]
        
        # 获取AI服务器实例
        server = get_ai_server_with_mcp_configs_v2(api_key=api_key, base_url=base_url, user_id=user_id)
        
        # 设置为指定会话的AI服务器实例
        set_session_ai_server(session_id, server)
        
        # 创建线程安全的事件队列
        event_queue = queue.Queue(maxsize=1000)  # 设置队列大小限制
        
        # 创建线程锁确保线程安全
        queue_lock = threading.Lock()
        
        # 定义回调函数
        def on_chunk(chunk: str):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("chunk", chunk), block=False)
                        logger.debug(f"Added chunk to queue: {chunk[:50]}...")
                    else:
                        logger.warning("Event queue is full, dropping chunk")
            except Exception as e:
                logger.error(f"Error in chunk callback: {e}")
        
        def on_tools_start(tool_calls: List[Dict[str, Any]]):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("tools_start", {"tool_calls": tool_calls}), block=False)
                        logger.debug(f"Added tools start to queue: {len(tool_calls)} tools")
                    else:
                        logger.warning("Event queue is full, dropping tools start")
            except Exception as e:
                logger.error(f"Error in tools_start callback: {e}")
        
        def on_tools_stream(result: Dict[str, Any]):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("tools_stream", result), block=False)
                        logger.debug(f"Added tools stream to queue: {result}")
                    else:
                        logger.warning("Event queue is full, dropping tools stream")
            except Exception as e:
                logger.error(f"Error in tools_stream callback: {e}")
        
        def on_tools_end(tool_results: List[Dict[str, Any]]):
            try:
                with queue_lock:
                    if not event_queue.full():
                        event_queue.put(("tools_end", {"tool_results": tool_results}), block=False)
                        logger.debug(f"Added tools end to queue: {len(tool_results)} results")
                    else:
                        logger.warning("Event queue is full, dropping tools end")
            except Exception as e:
                logger.error(f"Error in tools_end callback: {e}")
        
        # 创建一个标志来控制AI处理线程
        ai_completed = threading.Event()
        ai_error = None
        ai_result = None
        
        # 启动AI处理线程
        def ai_worker():
            nonlocal ai_error, ai_result
            try:
                logger.info(f"Starting AI worker for session {session_id}")
                
                # 解析模型配置
                model = model_config.get("model_name", "gpt-4") if model_config else "gpt-4"
                temperature = model_config.get("temperature", 0.7) if model_config else 0.7
                max_tokens = model_config.get("max_tokens", 4000) if model_config else 4000
                use_tools = model_config.get("use_tools", True) if model_config else True
                
                logger.info(f"AI worker config: model={model}, temp={temperature}, tokens={max_tokens}, tools={use_tools}")
                
                # 调用 v2 版本的 chat 方法
                ai_result = server.chat(
                    session_id=session_id,
                    user_message=content,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_tools=use_tools,
                    on_chunk=on_chunk,
                    on_tools_start=on_tools_start,
                    on_tools_stream=on_tools_stream,
                    on_tools_end=on_tools_end
                )
                
                logger.info(f"AI worker completed successfully for session {session_id}")
                
            except Exception as e:
                ai_error = e
                logger.error(f"Error in AI worker: {e}", exc_info=True)
            finally:
                # 确保完成标志被设置
                ai_completed.set()
                # 添加完成信号到队列
                try:
                    with queue_lock:
                        event_queue.put(("ai_completed", None), block=False)
                except:
                    pass
        
        # 启动AI处理线程
        ai_thread = threading.Thread(target=ai_worker, daemon=True)
        ai_thread.start()
        
        # 发送开始事件
        start_event = {
            "type": "start",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
        
        # 处理事件流
        completed = False
        last_heartbeat = time.time()
        heartbeat_interval = 30  # 30秒心跳间隔
        
        while not completed:
            try:
                # 检查是否有新事件
                try:
                    event_type, data = event_queue.get(timeout=2.0)  # 增加超时时间
                    
                    if event_type == "chunk":
                        event_data = {
                            "type": "chunk",
                            "content": data,
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                        
                    elif event_type == "tools_start":
                        event_data = {
                            "type": "tools_start",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                        
                    elif event_type == "tools_stream":
                        event_data = {
                            "type": "tools_stream",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                        
                    elif event_type == "tools_end":
                        event_data = {
                            "type": "tools_end",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                        
                    elif event_type == "ai_completed":
                        # AI处理完成信号
                        completed = True
                        
                except queue.Empty:
                    # 检查AI线程是否完成
                    if ai_completed.is_set():
                        completed = True
                    else:
                        # 发送心跳
                        current_time = time.time()
                        if current_time - last_heartbeat > heartbeat_interval:
                            heartbeat_event = {
                                "type": "heartbeat",
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(heartbeat_event, ensure_ascii=False)}\n\n"
                            last_heartbeat = current_time
                
            except Exception as e:
                logger.error(f"Error in stream processing: {e}", exc_info=True)
                error_event = {
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                break
        
        # 等待AI线程完成（最多等待5秒）
        if ai_thread.is_alive():
            ai_thread.join(timeout=5.0)
        
        # 发送最终结果
        if ai_error:
            final_event = {
                "type": "error",
                "error": str(ai_error),
                "timestamp": datetime.now().isoformat()
            }
        else:
            final_event = {
                "type": "complete",
                "result": ai_result,
                "timestamp": datetime.now().isoformat()
            }
        
        yield f"data: {json.dumps(final_event, ensure_ascii=False)}\n\n"
        
        # 发送结束标记
        yield f"data: [DONE]\n\n"
        
        logger.info(f"Stream response completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error in create_stream_response_v2: {e}", exc_info=True)
        error_event = {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        yield f"data: [DONE]\n\n"


# ===== API 端点 =====

@router.post("/chat/stream")
def chat_stream_v2(request: ChatRequestV2):
    """v2 版本的流式聊天端点"""
    try:
        logger.info(f"📨 v2 收到流式聊天请求: session_id={request.session_id}")
        
        # 转换模型配置
        model_config = None
        if request.ai_model_config:
            model_config = {
                "model_name": request.ai_model_config.model_name,
                "temperature": request.ai_model_config.temperature,
                "max_tokens": request.ai_model_config.max_tokens,
                "use_tools": request.ai_model_config.use_tools,
                "api_key": request.ai_model_config.api_key,
                "base_url": request.ai_model_config.base_url
            }
        
        # 创建流式响应
        return StreamingResponse(
            create_stream_response_v2(
                session_id=request.session_id,
                content=request.content,
                model_config=model_config,
                user_id=request.user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ v2 流式聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
def chat_v2(request: ChatRequestV2):
    """v2 版本的普通聊天端点"""
    try:
        logger.info(f"📨 v2 收到聊天请求: session_id={request.session_id}")
        
        # 获取AI服务器实例
        server = get_ai_server_with_mcp_configs_v2()
        
        # 提取模型配置
        model = request.ai_model_config.model_name if request.ai_model_config else "gpt-4"
        temperature = request.ai_model_config.temperature if request.ai_model_config else 0.7
        max_tokens = request.ai_model_config.max_tokens if request.ai_model_config else 4000
        use_tools = request.ai_model_config.use_tools if request.ai_model_config else True
        
        # 调用 v2 版本的 chat 方法
        result = server.chat(
            session_id=request.session_id,
            user_message=request.content,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            use_tools=use_tools
        )
        
        logger.info(f"✅ v2 聊天处理完成: session_id={request.session_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ v2 聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
def get_available_tools_v2():
    """v2 版本的获取可用工具端点"""
    try:
        server = get_ai_server_with_mcp_configs_v2()
        tools = server.get_available_tools()
        
        return {
            "success": True,
            "tools": tools,
            "count": len(tools)
        }
        
    except Exception as e:
        logger.error(f"❌ v2 获取工具列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def get_server_status_v2():
    """v2 版本的获取服务器状态端点"""
    try:
        server = get_ai_server_with_mcp_configs_v2()
        status = server.get_server_status()
        
        # 添加 v2 特有信息
        status["version"] = "v2"
        status["active_sessions"] = get_active_sessions()
        status["session_count"] = len(get_active_sessions())
        
        return status
        
    except Exception as e:
        logger.error(f"❌ v2 获取服务器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/reset")
def reset_session_v2(session_id: str):
    """v2 版本的重置会话端点"""
    try:
        server = get_ai_server_with_mcp_configs_v2()
        result = server.reset_session(session_id)
        
        # 移除会话级别的服务器实例
        remove_session_ai_server(session_id)
        
        logger.info(f"✅ v2 会话重置完成: session_id={session_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ v2 会话重置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/config")
def get_session_config_v2(session_id: str):
    """v2 版本的获取会话配置端点"""
    try:
        server = get_session_ai_server(session_id)
        if not server:
            server = get_ai_server_with_mcp_configs_v2()
        
        # 获取会话配置
        config = {
            "model": server.get_session_config(session_id, "model", server.default_model),
            "temperature": server.get_session_config(session_id, "temperature", server.default_temperature),
            "session_id": session_id
        }
        
        return {
            "success": True,
            "config": config
        }
        
    except Exception as e:
        logger.error(f"❌ v2 获取会话配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/config")
def update_session_config_v2(session_id: str, config: Dict[str, Any]):
    """v2 版本的更新会话配置端点"""
    try:
        server = get_session_ai_server(session_id)
        if not server:
            server = get_ai_server_with_mcp_configs_v2()
            set_session_ai_server(session_id, server)
        
        # 更新会话配置
        server.update_session_config(session_id, config)
        
        logger.info(f"✅ v2 会话配置更新完成: session_id={session_id}")
        return {
            "success": True,
            "message": "会话配置更新成功"
        }
        
    except Exception as e:
        logger.error(f"❌ v2 会话配置更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))