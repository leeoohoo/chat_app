# 消息相关API路由

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import json

from app.models.message import MessageCreate, row_to_dict

logger = logging.getLogger(__name__)
router = APIRouter()


def format_message(message_row) -> Dict[str, Any]:
    """格式化消息数据"""
    if not message_row:
        return None
    
    message_dict = row_to_dict(message_row)
    # 解析JSON字段
    if message_dict.get('tool_calls'):
        message_dict['tool_calls'] = json.loads(message_dict['tool_calls'])
    if message_dict.get('metadata'):
        message_dict['metadata'] = json.loads(message_dict['metadata'])
    
    return message_dict


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, limit: Optional[int] = Query(None, ge=1, le=1000)):
    """获取会话的消息列表"""
    try:
        messages = await MessageCreate.get_by_session(session_id, limit=limit)
        logger.info(f"获取会话 {session_id} 的 {len(messages)} 条消息")
        return messages
        
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话消息失败")

@router.post("/sessions/{session_id}/messages")
async def create_message(session_id: str, message: MessageCreate):
    """创建新消息"""
    try:
        # 确保session_id一致
        message.session_id = session_id
        
        new_message = await MessageCreate.create(message)
        logger.info(f"创建消息成功: {new_message['id']}")
        return new_message
        
    except Exception as e:
        logger.error(f"创建消息失败: {e}")
        raise HTTPException(status_code=500, detail="创建消息失败")