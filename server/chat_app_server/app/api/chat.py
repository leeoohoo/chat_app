# 聊天相关API路由

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.models.message import ChatStopRequest
from app.services.proxy import handle_chat_proxy, handle_health_check

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    return await handle_chat_proxy(request, body)


@router.get("/proxy/health")
async def proxy_health():
    return handle_health_check()


@router.post("/chat/stop")
async def stop_chat(request: Request):
    """停止当前聊天"""
    logger.info("🛑 [DEBUG] 收到停止聊天请求")
    
    # 从请求体中获取session_id
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        if not session_id:
            logger.warning("🛑 [DEBUG] 请求中缺少session_id")
            return {
                "success": False,
                "message": "session_id is required"
            }
        
        logger.info(f"🛑 [DEBUG] 开始处理停止请求，会话ID: {session_id}")
        
        # 直接中止AI服务器请求
        try:
            logger.info(f"🛑 [DEBUG] 正在获取会话 {session_id} 的ai_server实例")
            from .chat_api import get_session_ai_server
            ai_server = get_session_ai_server(session_id)
            
            if ai_server is None:
                logger.warning(f"🛑 [DEBUG] 会话 {session_id} 的ai_server为None，无法停止请求")
                return {
                    "success": False,
                    "message": f"会话 {session_id} 的AI服务器实例未找到"
                }
            
            logger.info(f"🛑 [DEBUG] 找到会话 {session_id} 的ai_server实例，正在调用abort_request")
            result = await ai_server.abort_request()
            
            logger.info(f"🛑 [DEBUG] 会话 {session_id} 的abort_request调用完成，结果: {result}")
            
            return {
                "success": True,
                "message": f"会话 {session_id} 的AI请求已停止"
            }
            
        except Exception as ai_error:
            import traceback
            error_details = f"中止AI服务器请求时出错: {str(ai_error)}\nTraceback: {traceback.format_exc()}"
            logger.error(f"⚠️ [DEBUG] {error_details}")
            return {
                "success": False,
                "message": f"停止请求失败: {str(ai_error)}"
            }
        
    except Exception as error:
        import traceback
        error_details = f"处理停止请求失败: {str(error)}\nTraceback: {traceback.format_exc()}"
        logger.error(f'🛑 [DEBUG] {error_details}')
        raise HTTPException(status_code=500, detail=str(error))


@router.get("/chat/active-streams")
async def get_active_streams():
    """获取活跃的流会话 - 简化版本"""
    return {
        "success": True,
        "active_streams": [],
        "message": "使用简化的停止机制，不再跟踪活跃流"
    }


@router.get("/chat/stream-status/{session_id}")
async def get_stream_status(session_id: str):
    """获取特定会话的流状态 - 简化版本"""
    return {
        "success": True,
        "session_id": session_id,
        "status": "unknown",
        "message": "使用简化的停止机制，不再跟踪流状态"
    }