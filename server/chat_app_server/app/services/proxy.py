# AI 请求代理模块
# 使用 OpenAI Python SDK 处理请求

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import openai
from openai import AsyncOpenAI
from app.services.stream_manager import stream_manager

logger = logging.getLogger(__name__)

async def handle_chat_proxy(request: Request, body: Dict[str, Any]) -> Response:
    """
    通用 AI API 代理处理器
    使用 OpenAI SDK 处理请求，支持多种 AI 服务提供商
    支持两种模式:
    1. OpenAI客户端模式: 使用Authorization头部和x-target-url头部
    2. 自定义头部模式: 使用x-base-url和x-api-key头部
    """
    try:
        messages = body.get('messages', [])
        model = body.get('model', 'gpt-3.5-turbo')
        stream = body.get('stream', True)
        session_id = body.get('session_id', str(uuid.uuid4()))
        
        logger.info(f'🤖 通用AI代理请求: {request.method}')
        logger.info(f'Headers: Authorization={bool(request.headers.get("authorization"))}, '
                   f'x-target-url={bool(request.headers.get("x-target-url"))}, '
                   f'x-base-url={bool(request.headers.get("x-base-url"))}, '
                   f'x-api-key={bool(request.headers.get("x-api-key"))}')

        base_url, api_key = None, None

        # 模式1: OpenAI客户端模式 (优先)
        if request.headers.get('authorization') and request.headers.get('x-target-url'):
            base_url = request.headers.get('x-target-url')
            api_key = request.headers.get('authorization').replace('Bearer ', '')
            logger.info('🔧 使用OpenAI客户端模式')
        # 模式2: 自定义头部模式
        elif request.headers.get('x-base-url') and request.headers.get('x-api-key'):
            base_url = request.headers.get('x-base-url')
            api_key = request.headers.get('x-api-key')
            logger.info('🔧 使用自定义头部模式')
        # 模式3: 直接从Authorization头部提取，使用默认目标URL
        elif request.headers.get('authorization'):
            base_url = 'https://api.openai.com/v1'  # 默认OpenAI API
            api_key = request.headers.get('authorization').replace('Bearer ', '')
            logger.info(f'🔧 使用默认目标URL模式: {base_url}')
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    'error': '缺少必需的认证信息。请提供以下任一组合:\n'
                           '1. Authorization + x-target-url 头部\n'
                           '2. x-base-url + x-api-key 头部\n'
                           '3. 仅 Authorization 头部（使用默认目标）',
                    'code': 'MISSING_AUTH_INFO'
                }
            )

        logger.info(f'🚀 使用OpenAI SDK请求: {base_url}')
        
        # 创建 OpenAI 客户端
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # 检查是否是流式请求
        is_stream_request = body.get('stream', False)
        
        if is_stream_request:
            logger.info(f"📡 处理流式请求，会话ID: {session_id}")
            
            # 创建流式响应
            async def stream_generator():
                try:
                    # 创建流式请求
                    # 过滤掉session_id和stream参数，然后显式设置stream=True
                    filtered_body = {k: v for k, v in body.items() if k not in ['session_id', 'stream']}
                    stream_response = await client.chat.completions.create(
                        **filtered_body,
                        stream=True
                    )
                    
                    async for chunk in stream_response:
                        # 检查是否被中断
                        if not stream_manager.is_stream_active(session_id):
                            logger.info(f"🛑 流式请求被中断，会话ID: {session_id}")
                            break
                        
                        data = f"data: {json.dumps(chunk.model_dump())}\n\n"
                        yield data
                    
                    # 发送完成信号
                    if stream_manager.is_stream_active(session_id):
                        yield "data: [DONE]\n\n"
                        logger.info(f"✅ 流式请求处理完成，会话ID: {session_id}")
                    
                except asyncio.CancelledError:
                    logger.info(f"🛑 流式请求被用户中断，会话ID: {session_id}")
                    raise
                except Exception as error:
                    logger.error(f"❌ 流式请求处理失败，会话ID: {session_id}: {error}")
                    if stream_manager.is_stream_active(session_id):
                        yield f"data: {json.dumps({'error': str(error)})}\n\n"
                finally:
                    # 确保会话被清理
                    await stream_manager.unregister_stream(session_id)
            
            # 创建流式响应
            response = StreamingResponse(
                stream_generator(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "X-Session-Id": session_id
                }
            )
            
            # 注册到流式会话管理器
            task = asyncio.current_task()
            await stream_manager.register_stream(
                session_id, 
                response, 
                task,
                {
                    'model': body.get('model'),
                    'messageCount': len(body.get('messages', [])),
                    'userAgent': request.headers.get('user-agent')
                }
            )
            
            return response
            
        else:
            logger.info('📡 处理非流式请求')
            
            try:
                # 使用 OpenAI SDK 发送非流式请求
                # 过滤掉session_id和stream参数，然后显式设置stream=False
                filtered_body = {k: v for k, v in body.items() if k not in ['session_id', 'stream']}
                response = await client.chat.completions.create(
                    **filtered_body,
                    stream=False
                )

                logger.info('✅ AI代理请求成功，返回JSON数据')
                return Response(
                    content=response.model_dump_json(),
                    media_type="application/json"
                )
                
            except Exception as error:
                logger.error(f'❌ API 错误响应: {error}')
                
                # 处理 OpenAI SDK 错误
                if hasattr(error, 'status_code'):
                    raise HTTPException(
                        status_code=error.status_code,
                        detail={
                            'error': str(error),
                            'code': getattr(error, 'code', 'API_ERROR'),
                            'type': getattr(error, 'type', 'unknown')
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail={
                            'error': '请求处理失败',
                            'code': 'INTERNAL_ERROR',
                            'details': str(error)
                        }
                    )
    
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f'❌ AI代理请求失败: {error}')
        
        # 区分不同类型的错误
        if 'ENOTFOUND' in str(error) or 'ECONNREFUSED' in str(error):
            raise HTTPException(
                status_code=503,
                detail={
                    'error': '无法连接到目标API服务',
                    'code': 'CONNECTION_ERROR',
                    'details': str(error)
                }
            )
        
        if 'timeout' in str(error).lower():
            raise HTTPException(
                status_code=408,
                detail={
                    'error': '请求超时',
                    'code': 'TIMEOUT_ERROR',
                    'details': str(error)
                }
            )
        
        if 'Invalid URL' in str(error):
            raise HTTPException(
                status_code=400,
                detail={
                    'error': '无效的目标URL',
                    'code': 'INVALID_URL',
                    'details': str(error)
                }
            )
        
        # 通用错误处理
        raise HTTPException(
            status_code=500,
            detail={
                'error': '代理服务器内部错误',
                'code': 'INTERNAL_ERROR',
                'details': str(error)
            }
        )

def handle_health_check() -> Dict[str, Any]:
    """健康检查处理器"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "proxy": {
            "type": "通用AI API代理",
            "description": "支持转发任意AI API请求，兼容OpenAI客户端",
            "supported_modes": [
                {
                    "name": "OpenAI客户端模式",
                    "description": "直接兼容OpenAI Python客户端",
                    "usage": {
                        "baseURL": "http://localhost:3001/api/chat/completions",
                        "headers": {
                            "x-target-url": "实际的AI API端点URL"
                        },
                        "example": """
# Python示例
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key='your-api-key',
    base_url='http://localhost:3001/api/chat',
    default_headers={
        'x-target-url': 'https://api.openai.com/v1'
    }
)"""
                    }
                },
                {
                    "name": "自定义头部模式",
                    "description": "使用自定义头部进行配置",
                    "usage": {
                        "endpoint": "/api/chat/completions",
                        "method": "POST",
                        "required_headers": {
                            "x-base-url": "目标API的完整URL",
                            "x-api-key": "API密钥"
                        }
                    }
                },
                {
                    "name": "默认目标模式",
                    "description": "仅提供Authorization头部，使用默认目标URL",
                    "usage": {
                        "endpoint": "/api/chat/completions",
                        "method": "POST",
                        "required_headers": {
                            "Authorization": "Bearer your-api-key"
                        },
                        "note": "使用默认的 OpenAI API"
                    }
                }
            ]
        }
    }