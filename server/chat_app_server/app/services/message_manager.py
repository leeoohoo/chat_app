"""
消息管理器 - Python实现
对应TypeScript中的MessageManager类
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime

from .ai_request_handler import Message

logger = logging.getLogger(__name__)


class MessageManager:
    """
    统一的消息保存管理器
    负责管理所有消息的保存逻辑，避免重复保存
    """
    
    def __init__(self, database_service):
        self.database_service = database_service
        self.pending_saves: Set[str] = set()  # 跟踪正在保存的消息ID
        self.saved_messages: Dict[str, Message] = {}  # 缓存已保存的消息
        
    async def save_user_message(self, data: Dict[str, Any]) -> Message:
        """保存用户消息"""
        message_key = f"{data.get('session_id', '')}-{data.get('role', '')}-{data.get('content', '')}-{data.get('created_at', datetime.now()).timestamp()}"
        
        # 检查是否正在保存或已保存
        if message_key in self.pending_saves:
            # 等待正在进行的保存完成
            while message_key in self.pending_saves:
                await asyncio.sleep(0.01)
            saved = self.saved_messages.get(message_key)
            if saved:
                return saved
        
        self.pending_saves.add(message_key)
        
        try:
            # 添加调试日志
            tool_calls_in_data = data.get('tool_calls', [])
            metadata_tool_calls = data.get('metadata', {}).get('tool_calls', [])
            logger.info(f"🔧 [DEBUG] MessageManager saving assistant message:")
            logger.info(f"🔧 [DEBUG] - tool_calls field: {len(tool_calls_in_data)} items")
            logger.info(f"🔧 [DEBUG] - metadata.tool_calls: {len(metadata_tool_calls)} items")
            
            saved_message = await self.database_service.create_message(data)
            
            # 检查 saved_message 是否为 None
            if saved_message is None:
                logger.error("🔧 [ERROR] Database service returned None for create_message")
                raise ValueError("Database service returned None for create_message")
            
            # 添加调试日志检查返回的数据
            saved_tool_calls = saved_message.get('tool_calls', [])
            saved_metadata = saved_message.get('metadata')
            if saved_metadata is None:
                saved_metadata = {}
            saved_metadata_tool_calls = saved_metadata.get('tool_calls', [])
            logger.info(f"🔧 [DEBUG] Database returned:")
            logger.info(f"🔧 [DEBUG] - tool_calls field: {len(saved_tool_calls) if saved_tool_calls else 0} items")
            logger.info(f"🔧 [DEBUG] - metadata: {saved_metadata}")
            logger.info(f"🔧 [DEBUG] - metadata.tool_calls: {len(saved_metadata_tool_calls) if saved_metadata_tool_calls else 0} items")
            
            # 转换为Message对象
            message = Message(
                id=saved_message.get('id'),
                session_id=saved_message.get('session_id'),
                role=saved_message.get('role'),
                content=saved_message.get('content'),
                status=saved_message.get('status', 'completed'),
                created_at=saved_message.get('created_at'),
                metadata=saved_message.get('metadata'),
                tool_calls=saved_message.get('tool_calls')
            )
            
            self.saved_messages[message_key] = message
            return message
            
        except Exception as e:
            logger.error(f"Error saving user message: {e}")
            raise
        finally:
            self.pending_saves.discard(message_key)

    def save_user_message_sync(self, data: Dict[str, Any]) -> Message:
        """保存用户消息（同步版本）"""
        message_key = f"{data.get('session_id', '')}-{data.get('role', '')}-{data.get('content', '')}-{data.get('created_at', datetime.now()).timestamp()}"
        
        # 检查是否已保存
        if message_key in self.saved_messages:
            return self.saved_messages[message_key]
        
        try:
            # 添加调试日志
            tool_calls_in_data = data.get('tool_calls', [])
            metadata_tool_calls = data.get('metadata', {}).get('tool_calls', [])
            logger.info(f"🔧 [DEBUG] MessageManager saving user message:")
            logger.info(f"🔧 [DEBUG] - tool_calls field: {len(tool_calls_in_data)} items")
            logger.info(f"🔧 [DEBUG] - metadata.tool_calls: {len(metadata_tool_calls)} items")
            
            # 同步调用数据库服务
            saved_message = self.database_service.create_message_sync(data)
            
            # 检查 saved_message 是否为 None
            if saved_message is None:
                logger.error("🔧 [ERROR] Database service returned None for create_message_sync")
                raise ValueError("Database service returned None for create_message_sync")
            
            # 添加调试日志检查返回的数据
            saved_tool_calls = saved_message.get('tool_calls', [])
            saved_metadata = saved_message.get('metadata')
            if saved_metadata is None:
                saved_metadata = {}
            saved_metadata_tool_calls = saved_metadata.get('tool_calls', [])
            logger.info(f"🔧 [DEBUG] Database returned:")
            logger.info(f"🔧 [DEBUG] - tool_calls field: {len(saved_tool_calls) if saved_tool_calls else 0} items")
            logger.info(f"🔧 [DEBUG] - metadata: {saved_metadata}")
            logger.info(f"🔧 [DEBUG] - metadata.tool_calls: {len(saved_metadata_tool_calls) if saved_metadata_tool_calls else 0} items")
            
            # 转换为Message对象
            message = Message(
                id=saved_message.get('id'),
                session_id=saved_message.get('session_id'),
                role=saved_message.get('role'),
                content=saved_message.get('content'),
                status=saved_message.get('status', 'completed'),
                created_at=saved_message.get('created_at'),
                metadata=saved_message.get('metadata'),
                tool_calls=saved_message.get('tool_calls')
            )
            
            self.saved_messages[message_key] = message
            return message
            
        except Exception as e:
            logger.error(f"Error saving user message (sync): {e}")
            raise

    async def save_assistant_message(self, data: Dict[str, Any]) -> Message:
        """保存助手消息"""
        tool_calls_str = str(data.get('metadata', {}).get('tool_calls', []))
        message_key = f"{data.get('session_id', '')}-{data.get('role', '')}-{tool_calls_str}-{data.get('created_at', datetime.now()).timestamp()}"
        
        # 检查是否正在保存或已保存
        if message_key in self.pending_saves:
            # 等待正在进行的保存完成
            while message_key in self.pending_saves:
                await asyncio.sleep(0.01)
            saved = self.saved_messages.get(message_key)
            if saved:
                return saved
        
        self.pending_saves.add(message_key)
        
        try:
            saved_message = await self.database_service.create_message(data)
            
            # 检查 saved_message 是否为 None
            if saved_message is None:
                logger.error("🔧 [ERROR] Database service returned None for create_message in save_assistant_message")
                raise ValueError("Database service returned None for create_message")
            
            # 转换为Message对象
            message = Message(
                id=saved_message.get('id'),
                session_id=saved_message.get('session_id'),
                role=saved_message.get('role'),
                content=saved_message.get('content'),
                status=saved_message.get('status', 'completed'),
                created_at=saved_message.get('created_at'),
                metadata=saved_message.get('metadata'),
                tool_calls=saved_message.get('tool_calls')
            )
            
            self.saved_messages[message_key] = message
            return message
            
        except Exception as e:
            logger.error(f"Error saving assistant message: {e}")
            raise
        finally:
            self.pending_saves.discard(message_key)

    def save_assistant_message_sync(self, data: Dict[str, Any]) -> Message:
        """保存助手消息（同步版本）"""
        tool_calls_str = str(data.get('metadata', {}).get('tool_calls', []))
        message_key = f"{data.get('session_id', '')}-{data.get('role', '')}-{tool_calls_str}-{data.get('created_at', datetime.now()).timestamp()}"
        
        # 检查是否已保存
        if message_key in self.saved_messages:
            return self.saved_messages[message_key]
        
        try:
            # 同步调用数据库服务
            saved_message = self.database_service.create_message_sync(data)
            
            # 检查 saved_message 是否为 None
            if saved_message is None:
                logger.error("🔧 [ERROR] Database service returned None for create_message_sync in save_assistant_message_sync")
                raise ValueError("Database service returned None for create_message_sync")
            
            # 转换为Message对象
            message = Message(
                id=saved_message.get('id'),
                session_id=saved_message.get('session_id'),
                role=saved_message.get('role'),
                content=saved_message.get('content'),
                status=saved_message.get('status', 'completed'),
                created_at=saved_message.get('created_at'),
                metadata=saved_message.get('metadata'),
                tool_calls=saved_message.get('tool_calls')
            )
            
            self.saved_messages[message_key] = message
            return message
            
        except Exception as e:
            logger.error(f"Error saving assistant message (sync): {e}")
            raise

    async def save_tool_message(self, data: Dict[str, Any]) -> Message:
        """保存工具消息"""
        tool_call_id = data.get('metadata', {}).get('tool_call_id', '')
        message_key = f"{data.get('session_id', '')}-{data.get('role', '')}-{tool_call_id}-{data.get('created_at', datetime.now()).timestamp()}"
        
        # 检查是否正在保存或已保存
        if message_key in self.pending_saves:
            # 等待正在进行的保存完成
            while message_key in self.pending_saves:
                await asyncio.sleep(0.01)
            saved = self.saved_messages.get(message_key)
            if saved:
                return saved
        
        self.pending_saves.add(message_key)
        
        try:
            saved_message = await self.database_service.create_message(data)
            
            # 检查 saved_message 是否为 None
            if saved_message is None:
                logger.error("🔧 [ERROR] Database service returned None for create_message in save_tool_message")
                raise ValueError("Database service returned None for create_message")
            
            # 转换为Message对象
            message = Message(
                id=saved_message.get('id'),
                session_id=saved_message.get('session_id'),
                role=saved_message.get('role'),
                content=saved_message.get('content'),
                status=saved_message.get('status', 'completed'),
                created_at=saved_message.get('created_at'),
                metadata=saved_message.get('metadata'),
                tool_calls=saved_message.get('tool_calls')
            )
            
            self.saved_messages[message_key] = message
            return message
            
        except Exception as e:
            logger.error(f"Error saving tool message: {e}")
            raise
        finally:
            self.pending_saves.discard(message_key)

    async def save_message(self, data: Dict[str, Any]) -> Message:
        """通用保存消息方法"""
        role = data.get('role', '')
        
        if role == 'user':
            return await self.save_user_message(data)
        elif role == 'assistant':
            return await self.save_assistant_message(data)
        elif role == 'tool':
            return await self.save_tool_message(data)
        else:
            # 默认处理
            return await self.save_user_message(data)

    def clear_cache(self) -> None:
        """清除缓存"""
        self.saved_messages.clear()
        logger.info("Message cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        return {
            "pending_count": len(self.pending_saves),
            "cached_count": len(self.saved_messages)
        }