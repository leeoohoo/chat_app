"""
聊天API - 对外提供流式聊天接口
"""
import json
import logging
import queue
import threading
import time
from typing import Dict, Any, Optional, Generator, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.ai_server import AiServer
from ..services.ai_request_handler import AiModelConfig, Message, CallbackType
from ..services.mcp_tool_execute import create_example_mcp_executor, McpToolExecute
from ..models import db
from ..models.message import MessageCreate

logger = logging.getLogger(__name__)

router = APIRouter()


class ModelConfig(BaseModel):
    """模型配置"""
    model_config = {"protected_namespaces": ()}
    
    model_name: str = Field(default="gpt-3.5-turbo", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=1000, gt=0, description="最大token数")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default="https://api.openai.com/v1", description="API基础URL")


class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: str = Field(description="会话ID")
    content: str = Field(description="消息内容")
    ai_model_config: Optional[ModelConfig] = Field(default=None, description="模型配置")


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(description="角色")
    content: str = Field(description="内容")


class DirectChatRequest(BaseModel):
    """直接聊天请求"""
    session_id: str = Field(description="会话ID")
    messages: list[ChatMessage] = Field(description="消息列表")
    ai_model_config: Optional[ModelConfig] = Field(default=None, description="模型配置")


# 全局AI服务器实例（在实际应用中应该通过依赖注入）
ai_server: Optional[AiServer] = None

# 全局AI服务器实例管理器 - 按session_id管理多个会话
_session_ai_servers: Dict[str, AiServer] = {}

def set_session_ai_server(session_id: str, server: AiServer) -> None:
    """设置指定会话的AI服务器实例"""
    global _session_ai_servers
    _session_ai_servers[session_id] = server
    logger.info(f"🛑 [DEBUG] 设置会话 {session_id} 的AI服务器实例")

def get_session_ai_server(session_id: str) -> Optional[AiServer]:
    """获取指定会话的AI服务器实例"""
    global _session_ai_servers
    server = _session_ai_servers.get(session_id)
    logger.info(f"🛑 [DEBUG] 获取会话 {session_id} 的AI服务器实例: {server is not None}")
    return server

def remove_session_ai_server(session_id: str) -> None:
    """移除指定会话的AI服务器实例"""
    global _session_ai_servers
    if session_id in _session_ai_servers:
        del _session_ai_servers[session_id]
        logger.info(f"🛑 [DEBUG] 移除会话 {session_id} 的AI服务器实例")

def get_active_sessions() -> List[str]:
    """获取所有活跃会话ID列表"""
    global _session_ai_servers
    return list(_session_ai_servers.keys())


def load_mcp_configs_sync() -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """从数据库加载MCP配置（同步版本）"""
    try:
        # 获取所有启用的MCP配置
        configs = db.fetchall_sync('SELECT * FROM mcp_configs WHERE enabled = 1')
        
        http_servers = {}
        stdio_servers = {}
        
        for config in configs:
            server_name = config['name']
            command = config['command']
            server_type = config.get('type', 'stdio')  # 默认为stdio
            
            # 解析args和env
            try:
                args = json.loads(config.get('args', '[]')) if config.get('args') else []
            except json.JSONDecodeError:
                # 如果不是JSON格式，尝试按逗号分割
                args = config.get('args', '').split(',') if config.get('args') else []
            
            try:
                env = json.loads(config.get('env', '{}')) if config.get('env') else {}
            except json.JSONDecodeError:
                # 如果不是JSON格式，尝试解析为字典字符串
                env = {}
            
            # 根据type字段判断协议类型
            if server_type == 'http':
                # HTTP协议
                http_servers[server_name] = {
                    'url': command,
                    'args': args,
                    'env': env
                }
            else:
                # stdio协议 - 解析 command 字段中的 `脚本地址--别名` 格式
                actual_command = command
                alias = server_name  # 默认使用服务名作为别名
                
                # 检查是否包含 --别名 格式
                if '--' in command:
                    parts = command.split('--', 1)  # 只分割第一个 --
                    actual_command = parts[0].strip()
                    alias = parts[1].strip()
                
                stdio_servers[server_name] = {
                    'command': actual_command,
                    'alias': alias,
                    'args': args,
                    'env': env
                }
        
        logger.info(f"✅ 加载MCP配置完成: HTTP服务器 {len(http_servers)} 个, stdio服务器 {len(stdio_servers)} 个")
        return http_servers, stdio_servers
        
    except Exception as e:
        logger.error(f"❌ 加载MCP配置失败: {e}")
        return {}, {}


async def load_mcp_configs() -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """从数据库加载MCP配置（异步版本，保持兼容性）"""
    try:
        # 获取所有启用的MCP配置
        db.connection.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
        configs = await db.fetchall('SELECT * FROM mcp_configs WHERE enabled = 1')
        
        http_servers = {}
        stdio_servers = {}
        
        for config in configs:
            server_name = config['name']
            command = config['command']
            server_type = config.get('type', 'stdio')  # 默认为stdio
            
            # 解析args和env
            try:
                args = json.loads(config.get('args', '[]')) if config.get('args') else []
            except json.JSONDecodeError:
                # 如果不是JSON格式，尝试按逗号分割
                args = config.get('args', '').split(',') if config.get('args') else []
            
            try:
                env = json.loads(config.get('env', '{}')) if config.get('env') else {}
            except json.JSONDecodeError:
                # 如果不是JSON格式，尝试解析为字典字符串
                env = {}
            
            # 根据type字段判断协议类型
            if server_type == 'http':
                # HTTP协议
                http_servers[server_name] = {
                    'url': command,
                    'args': args,
                    'env': env
                }
            else:
                # stdio协议 - 解析 command 字段中的 `脚本地址--别名` 格式
                actual_command = command
                alias = server_name  # 默认使用服务名作为别名
                
                # 检查是否包含 --别名 格式
                if '--' in command:
                    parts = command.split('--', 1)  # 只分割第一个 --
                    actual_command = parts[0].strip()
                    alias = parts[1].strip()
                
                stdio_servers[server_name] = {
                    'command': actual_command,
                    'alias': alias,
                    'args': args,
                    'env': env
                }
        
        logger.info(f"✅ 加载MCP配置完成: HTTP服务器 {len(http_servers)} 个, stdio服务器 {len(stdio_servers)} 个")
        return http_servers, stdio_servers
        
    except Exception as e:
        logger.error(f"❌ 加载MCP配置失败: {e}")
        return {}, {}


def get_ai_server() -> AiServer:
    """获取AI服务器实例"""
    global ai_server
    if ai_server is None:
        # 创建MCP工具执行器（暂时使用示例配置，实际使用时会动态加载）
        mcp_executor = create_example_mcp_executor()
        
        # 创建AI服务器（直接使用 models 模块，不需要额外的 database_service）
        ai_server = AiServer(
            database_service=None,  # 不再使用独立的 database_service
            mcp_tool_execute=mcp_executor
        )
    
    return ai_server


def get_ai_server_with_mcp_configs_sync() -> AiServer:
    """获取带有动态MCP配置的AI服务器实例（同步版本）"""
    try:
        # 加载MCP配置
        http_servers, stdio_servers = load_mcp_configs_sync()
        
        # 创建支持stdio协议的MCP工具执行器
        mcp_executor = McpToolExecute(
            mcp_servers=http_servers,
            stdio_mcp_servers=stdio_servers
        )
        
        # 初始化工具执行器（同步版本）
        mcp_executor.init_sync()
        
        # 记录工具构建结果
        tools_count = len(mcp_executor.get_tools())
        logger.info(f"🔧 MCP工具执行器初始化完成，共加载 {tools_count} 个工具")
        
        # 创建AI服务器
        server = AiServer(
            database_service=None,
            mcp_tool_execute=mcp_executor
        )
        
        return server
        
    except Exception as e:
        logger.error(f"❌ 创建AI服务器失败: {e}")
        # 回退到示例配置
        return get_ai_server()


async def get_ai_server_with_mcp_configs() -> AiServer:
    """获取带有动态MCP配置的AI服务器实例（异步版本，保持兼容性）"""
    try:
        # 加载MCP配置
        http_servers, stdio_servers = await load_mcp_configs()
        
        # 不再需要 MockDatabaseService，直接使用 models 模块
        
        # 创建支持stdio协议的MCP工具执行器
        mcp_executor = McpToolExecute(
            mcp_servers=http_servers,
            stdio_mcp_servers=stdio_servers
        )
        
        # 初始化工具执行器（这会调用build_tools()）
        await mcp_executor.init()
        
        # 记录工具构建结果
        tools_count = len(mcp_executor.get_tools())
        logger.info(f"🔧 MCP工具执行器初始化完成，共加载 {tools_count} 个工具")
        
        # 创建AI服务器（不再需要 database_service）
        server = AiServer(
            database_service=None,
            mcp_tool_execute=mcp_executor
        )
        
        return server
        
    except Exception as e:
        logger.error(f"❌ 创建AI服务器失败: {e}")
        # 回退到示例配置
        return get_ai_server()


def create_stream_response(
    session_id: str,
    content: str = None,
    messages: list[Dict[str, Any]] = None,
    model_config: Optional[Dict[str, Any]] = None
) -> Generator[str, None, None]:
    """
    创建流式响应（同步版本）
    
    Args:
        session_id: 会话ID
        content: 消息内容（用于send_message）
        messages: 消息列表（用于send_message_direct）
        model_config: 模型配置
        
    Yields:
        SSE格式的数据
    """
    try:
        # 获取AI服务器实例（同步版本）
        server = get_ai_server_with_mcp_configs_sync()
        
        # 设置为指定会话的AI服务器实例
        set_session_ai_server(session_id, server)
        
        # 创建线程安全的事件队列
        event_queue = queue.Queue()
        
        # 定义回调函数
        def callback(callback_type: str, data: Any):
            try:
                # 将事件放入队列
                event_queue.put((callback_type, data))
            except Exception as e:
                logger.error(f"Error in callback: {e}")
        
        # 创建一个标志来控制AI处理线程
        ai_completed = threading.Event()
        ai_error = None
        
        # 启动AI处理线程
        def ai_worker():
            nonlocal ai_error
            try:
                if content is not None:
                    # 使用send_message_sync
                    server.send_message_sync(
                        session_id=session_id,
                        content=content,
                        model_config=model_config,
                        callback=callback
                    )
                else:
                    # 使用send_message_direct_sync
                    server.send_message_direct_sync(
                        session_id=session_id,
                        messages=messages,
                        model_config=model_config,
                        callback=callback
                    )
            except Exception as e:
                ai_error = e
                logger.error(f"Error in AI worker: {e}")
            finally:
                ai_completed.set()
        
        # 启动AI处理线程
        ai_thread = threading.Thread(target=ai_worker, daemon=True)
        ai_thread.start()
        
        # 处理事件流
        completed = False
        last_heartbeat = time.time()
        heartbeat_interval = 30  # 30秒心跳间隔
        
        while not completed:
            try:
                # 检查是否有新事件
                try:
                    callback_type, data = event_queue.get(timeout=1.0)
                    
                    # 映射CallbackType到前端期望的格式
                    if callback_type == CallbackType.ON_CHUNK:
                        event_data = {
                            "type": "chunk",
                            "content": data.get("content", ""),
                            "accumulated": data.get("accumulated", "")
                        }
                    elif callback_type == CallbackType.ON_TOOL_CALL:
                        event_data = {
                            "type": "tool_call",
                            "data": data
                        }
                    elif callback_type == CallbackType.ON_TOOL_RESULT:
                        event_data = {
                            "type": "tool_result", 
                            "data": data
                        }
                    elif callback_type == CallbackType.ON_TOOL_STREAM_CHUNK:
                        event_data = {
                            "type": "tool_stream_chunk",
                            "data": data
                        }
                    elif callback_type == CallbackType.ON_COMPLETE:
                        # 确保Message对象正确序列化
                        serialized_data = data.copy() if isinstance(data, dict) else {}
                        if "message" in serialized_data and hasattr(serialized_data["message"], "to_dict"):
                            serialized_data["message"] = serialized_data["message"].to_dict()
                        
                        event_data = {
                            "type": "complete",
                            "data": serialized_data
                        }
                        logger.info(f"🎯 Sending complete event to frontend: {event_data['type']}")
                    elif callback_type == CallbackType.ON_ERROR:
                        event_data = {
                            "type": "error",
                            "data": data
                        }
                    else:
                        event_data = {
                            "type": str(callback_type),
                            "data": data
                        }
                    
                    # 发送SSE数据
                    yield f"data: {json.dumps(event_data, ensure_ascii=False, default=str)}\n\n"
                    
                    # 检查是否完成
                    if callback_type in [CallbackType.ON_COMPLETE, "complete"]:
                        # 检查这是否是最终的完成事件（必须有final标志）
                        is_final = False
                        if isinstance(data, dict) and data.get("final") is True:
                            is_final = True
                            logger.info(f"🎯 Received FINAL complete event, sending done signal")
                        else:
                            logger.info(f"🎯 Received intermediate complete event (no final flag), continuing...")
                        
                        if is_final:
                            completed = True
                            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                            break
                    elif callback_type in [CallbackType.ON_ERROR, "error"]:
                        logger.info(f"🎯 Received error event, marking as completed")
                        completed = True
                        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                        break
                        
                except queue.Empty:
                    # 没有新事件，检查AI线程是否完成
                    if ai_completed.is_set():
                        # AI线程完成，处理剩余事件
                        logger.info(f"🎯 AI thread completed, processing remaining events")
                        
                        # 检查是否有错误
                        if ai_error:
                            error_data = {
                                "type": "error",
                                "data": {"error": str(ai_error)}
                            }
                            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                            break
                        
                        # 处理剩余的事件
                        remaining_events = []
                        while True:
                            try:
                                remaining_events.append(event_queue.get_nowait())
                            except queue.Empty:
                                break
                        
                        if remaining_events:
                            logger.info(f"🎯 Processing {len(remaining_events)} remaining events")
                            for callback_type, data in remaining_events:
                                # 映射CallbackType到前端期望的格式
                                if callback_type == CallbackType.ON_CHUNK:
                                    event_data = {
                                        "type": "chunk",
                                        "content": data.get("content", ""),
                                        "accumulated": data.get("accumulated", "")
                                    }
                                elif callback_type == CallbackType.ON_TOOL_CALL:
                                    event_data = {
                                        "type": "tool_call",
                                        "data": data
                                    }
                                elif callback_type == CallbackType.ON_TOOL_RESULT:
                                    event_data = {
                                        "type": "tool_result", 
                                        "data": data
                                    }
                                elif callback_type == CallbackType.ON_TOOL_STREAM_CHUNK:
                                    event_data = {
                                        "type": "tool_stream_chunk",
                                        "data": data
                                    }
                                elif callback_type == CallbackType.ON_COMPLETE:
                                    # 确保Message对象正确序列化
                                    serialized_data = data.copy() if isinstance(data, dict) else {}
                                    if "message" in serialized_data and hasattr(serialized_data["message"], "to_dict"):
                                        serialized_data["message"] = serialized_data["message"].to_dict()
                                    
                                    event_data = {
                                        "type": "complete",
                                        "data": serialized_data
                                    }
                                    logger.info(f"🎯 Sending complete event to frontend: {event_data['type']}")
                                elif callback_type == CallbackType.ON_ERROR:
                                    event_data = {
                                        "type": "error",
                                        "data": data
                                    }
                                else:
                                    event_data = {
                                        "type": str(callback_type),
                                        "data": data
                                    }
                                
                                yield f"data: {json.dumps(event_data, ensure_ascii=False, default=str)}\n\n"
                                
                                # 检查是否完成
                                if callback_type in [CallbackType.ON_COMPLETE, "complete"]:
                                    # 检查这是否是最终的完成事件
                                    is_final = False
                                    if isinstance(data, dict) and data.get("final") is True:
                                        is_final = True
                                        logger.info(f"🎯 Received FINAL complete event, sending done signal")
                                    
                                    if is_final:
                                        completed = True
                                        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                                        break
                                elif callback_type in [CallbackType.ON_ERROR, "error"]:
                                    logger.info(f"🎯 Received error event, marking as completed")
                                    completed = True
                                    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                                    break
                        
                        # 如果没有收到完成事件，发送done信号
                        if not completed:
                            logger.info("🎯 AI thread completed but no final complete event received, sending done signal")
                            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                            completed = True
                    else:
                        # 发送心跳（如果需要）
                        current_time = time.time()
                        if current_time - last_heartbeat > heartbeat_interval:
                            yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"
                            last_heartbeat = current_time
                
            except Exception as e:
                logger.error(f"Error in stream processing: {e}")
                error_data = {
                    "type": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                break
        
        # 等待AI线程完成
        if ai_thread.is_alive():
            ai_thread.join(timeout=5.0)
    
    except Exception as e:
        logger.error(f"Error in create_stream_response: {e}")
        
        error_data = {
            "type": "error",
            "data": {"error": str(e)}
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
    
    finally:
        # 清理会话AI服务器实例
        try:
            remove_session_ai_server(session_id)
            logger.info(f"🧹 Session {session_id} AI server instance cleaned up")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup session AI server during cleanup: {cleanup_error}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口
    
    接收用户消息并返回AI的流式响应
    """
    try:
        # 转换模型配置
        model_config_dict = None
        if request.ai_model_config:
            model_config_dict = {
                "model_name": request.ai_model_config.model_name,
                "temperature": request.ai_model_config.temperature,
                "max_tokens": request.ai_model_config.max_tokens,
                "api_key": request.ai_model_config.api_key,
                "base_url": request.ai_model_config.base_url
            }
        
        # 创建流式响应
        return StreamingResponse(
            create_stream_response(
                session_id=request.session_id,
                content=request.content,
                model_config=model_config_dict
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
    
    except Exception as e:
        logger.error(f"Error in chat_stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream/direct")
async def chat_stream_direct(request: DirectChatRequest):
    """
    直接流式聊天接口
    
    接收消息列表并返回AI的流式响应（不保存用户消息）
    """
    try:
        # 转换模型配置
        model_config_dict = None
        if request.ai_model_config:
            model_config_dict = {
                "model_name": request.ai_model_config.model_name,
                "temperature": request.ai_model_config.temperature,
                "max_tokens": request.ai_model_config.max_tokens,
                "api_key": request.ai_model_config.api_key,
                "base_url": request.ai_model_config.base_url
            }
        
        # 转换消息格式
        messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in request.messages
        ]
        
        # 创建流式响应
        return StreamingResponse(
            create_stream_response(
                session_id=request.session_id,
                messages=messages,
                model_config=model_config_dict
            ),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
    
    except Exception as e:
        logger.error(f"Error in chat_stream_direct: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def get_available_tools():
    """获取可用工具列表"""
    try:
        server = get_ai_server_with_mcp_configs_sync()
        tools = server.get_available_tools()
        return {"tools": tools}
    
    except Exception as e:
        logger.error(f"Error getting available tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/servers")
async def get_servers_info():
    """获取MCP服务器信息"""
    try:
        server = get_ai_server_with_mcp_configs_sync()
        servers = server.get_servers_info()
        return {"servers": servers}
    
    except Exception as e:
        logger.error(f"Error getting servers info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/abort")
async def abort_chat(request: Request):
    """中止当前聊天请求"""
    try:
        # 获取session_id（从请求体或查询参数）
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        session_id = body.get("session_id") or request.query_params.get("session_id")
        
        # 中止AI服务器请求
        server = get_ai_server()
        server.abort_request()
        
        # 注意：由于我们已经移除了stream_manager，这里只需要中止AI服务器请求
        logger.info(f"🛑 Chat abort request for session {session_id}")
        
        return {"message": "Chat request aborted"}
    
    except Exception as e:
        logger.error(f"Error aborting chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))