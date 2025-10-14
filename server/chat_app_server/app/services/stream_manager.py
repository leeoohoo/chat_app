# 流式会话管理器
# 管理正在进行的流式输出，支持按会话ID中断

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from fastapi import Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self):
        # 存储正在进行的流式会话
        # key: sessionId, value: { response, task, start_time, metadata }
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register_stream(self, session_id: str, response: Response, task: asyncio.Task, metadata: Dict[str, Any] = None):
        """
        注册一个新的流式会话
        
        Args:
            session_id: 会话ID
            response: FastAPI响应对象
            task: 异步任务对象
            metadata: 额外的元数据
        """
        async with self._lock:
            logger.info(f"📡 StreamManager: 注册流式会话 {session_id}")
            
            if metadata is None:
                metadata = {}
            
            stream_info = {
                'response': response,
                'task': task,
                'start_time': time.time(),
                'metadata': metadata
            }
            
            self.active_streams[session_id] = stream_info
            
            logger.info(f"📡 StreamManager: 当前活跃流式会话数量: {len(self.active_streams)}")

    async def unregister_stream(self, session_id: str):
        """
        注销流式会话
        
        Args:
            session_id: 会话ID
        """
        async with self._lock:
            if session_id in self.active_streams:
                logger.info(f"📡 StreamManager: 注销流式会话 {session_id}")
                del self.active_streams[session_id]
                logger.info(f"📡 StreamManager: 当前活跃流式会话数量: {len(self.active_streams)}")

    async def abort_stream(self, session_id: str) -> bool:
        """
        中断指定会话的流式输出
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功中断
        """
        async with self._lock:
            stream_info = self.active_streams.get(session_id)
            
            if not stream_info:
                logger.warning(f"⚠️ StreamManager: 会话 {session_id} 不存在或已结束")
                return False

            logger.info(f"🛑 StreamManager: 强制中断流式会话 {session_id}")
            
            try:
                # 取消异步任务
                task = stream_info.get('task')
                if task and not task.done():
                    task.cancel()
                    logger.info(f"🛑 StreamManager: 任务已取消 {session_id}")
                
                # 立即清理会话
                await self.unregister_stream(session_id)
                
                return True
            except Exception as error:
                logger.error(f"❌ StreamManager: 中断会话 {session_id} 时出错: {error}")
                # 即使出错也要清理会话
                await self.unregister_stream(session_id)
                return False

    def get_active_streams(self) -> List[Dict[str, Any]]:
        """
        获取所有活跃的流式会话
        
        Returns:
            List[Dict]: 活跃会话列表
        """
        streams = []
        current_time = time.time()
        
        for session_id, stream_info in self.active_streams.items():
            streams.append({
                'session_id': session_id,
                'start_time': stream_info['start_time'],
                'duration': current_time - stream_info['start_time'],
                'metadata': stream_info['metadata']
            })
        
        return streams

    def is_stream_active(self, session_id: str) -> bool:
        """
        检查指定会话是否正在流式输出
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否正在流式输出
        """
        return session_id in self.active_streams

    async def cleanup(self):
        """清理所有流式会话（服务器关闭时使用）"""
        logger.info(f"🧹 StreamManager: 清理所有流式会话，共 {len(self.active_streams)} 个")
        
        for session_id, stream_info in list(self.active_streams.items()):
            try:
                task = stream_info.get('task')
                if task and not task.done():
                    task.cancel()
            except Exception as error:
                logger.error(f"❌ StreamManager: 清理会话 {session_id} 时出错: {error}")
        
        self.active_streams.clear()
        logger.info("🧹 StreamManager: 清理完成")

# 创建全局实例
stream_manager = StreamManager()