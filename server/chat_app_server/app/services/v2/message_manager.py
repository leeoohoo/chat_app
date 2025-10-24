"""
消息管理器
负责处理聊天消息的保存、检索和管理
"""
import time
from typing import Dict, List, Any, Optional

# 导入数据库模型
from ...models.message import MessageCreate


class MessageManager:
    """消息管理器"""
    
    def __init__(self):
        """
        初始化消息管理器
        
        注意：现在直接使用 models 模块中的数据库操作方法
        """
        
        # 缓存最近保存的消息
        self.recent_messages = {}
        
        # 待保存的消息队列
        self.pending_saves = []
        
        # 统计信息
        self.stats = {
            "messages_saved": 0,
            "messages_retrieved": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def save_user_message(self, session_id: str, content: str, message_id: str = None) -> Dict[str, Any]:
        """
        保存用户消息
        
        Args:
            session_id: 会话ID
            content: 消息内容
            message_id: 消息ID（可选）
            
        Returns:
            保存的消息信息
        """
        try:
            # 创建消息数据
            message_data = MessageCreate(
                id=message_id,
                sessionId=session_id,
                role="user",
                content=content
            )
            
            # 使用同步方法保存到数据库
            saved_message = MessageCreate.create_sync(message_data)
            
            # 缓存消息
            if saved_message:
                self._cache_message(saved_message)
                self.stats["messages_saved"] += 1
            
            return {
                "success": True,
                "message": saved_message,
                "message_id": saved_message.get("id") if saved_message else None
            }
            
        except Exception as e:
            error_message = f"保存用户消息失败: {str(e)}"
            print(f"Error in save_user_message: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def save_assistant_message(self, 
                             session_id: str, 
                             content: str, 
                             message_id: str = None,
                             summary: str = None,
                             reasoning: str = None,
                             metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        保存助手消息
        
        Args:
            session_id: 会话ID
            content: 消息内容
            message_id: 消息ID（可选）
            summary: 消息摘要
            reasoning: 推理过程
            metadata: 元数据
            
        Returns:
            保存的消息信息
        """
        try:
            # 创建消息数据
            message_data = MessageCreate(
                id=message_id,
                sessionId=session_id,
                role="assistant",
                content=content,
                summary=summary,
                reasoning=reasoning,
                metadata=metadata
            )
            
            # 使用同步方法保存到数据库
            saved_message = MessageCreate.create_sync(message_data)
            
            # 缓存消息
            if saved_message:
                self._cache_message(saved_message)
                self.stats["messages_saved"] += 1
            
            return {
                "success": True,
                "message": saved_message,
                "message_id": saved_message.get("id") if saved_message else None
            }
            
        except Exception as e:
            error_message = f"保存助手消息失败: {str(e)}"
            print(f"Error in save_assistant_message: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def save_tool_message(self, 
                         session_id: str, 
                         content: str, 
                         tool_call_id: str,
                         message_id: str = None,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        保存工具消息
        
        Args:
            session_id: 会话ID
            content: 消息内容
            tool_call_id: 工具调用ID
            message_id: 消息ID（可选）
            metadata: 元数据
            
        Returns:
            保存的消息信息
        """
        try:
            # 创建消息数据
            message_data = MessageCreate(
                id=message_id,
                sessionId=session_id,
                role="tool",
                content=content,
                tool_call_id=tool_call_id,
                metadata=metadata
            )
            
            # 使用同步方法保存到数据库
            saved_message = MessageCreate.create_sync(message_data)
            
            # 缓存消息
            if saved_message:
                self._cache_message(saved_message)
                self.stats["messages_saved"] += 1
            
            return {
                "success": True,
                "message": saved_message,
                "message_id": saved_message.get("id") if saved_message else None
            }
            
        except Exception as e:
            error_message = f"保存工具消息失败: {str(e)}"
            print(f"Error in save_tool_message: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def get_session_messages(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取会话消息
        
        Args:
            session_id: 会话ID
            limit: 消息数量限制
            
        Returns:
            消息列表
        """
        try:
            # 使用同步方法从数据库获取消息
            messages = MessageCreate.get_by_session_sync(session_id, limit)
            
            self.stats["messages_retrieved"] += len(messages)
            
            return messages
            
        except Exception as e:
            error_message = f"获取会话消息失败: {str(e)}"
            print(f"Error in get_session_messages: {error_message}")
            return []
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            消息信息
        """
        try:
            # 先检查缓存
            if message_id in self.recent_messages:
                self.stats["cache_hits"] += 1
                return self.recent_messages[message_id]
            
            # 从数据库获取
            message = MessageCreate.get_by_id_sync(message_id)
            
            if message:
                self._cache_message(message)
                self.stats["cache_misses"] += 1
                self.stats["messages_retrieved"] += 1
            
            return message
            
        except Exception as e:
            error_message = f"获取消息失败: {str(e)}"
            print(f"Error in get_message_by_id: {error_message}")
            return None
    
    def process_pending_saves(self) -> Dict[str, Any]:
        """
        处理待保存的消息
        
        Returns:
            处理结果
        """
        try:
            if not self.pending_saves:
                return {
                    "success": True,
                    "processed_count": 0,
                    "message": "没有待保存的消息"
                }
            
            processed_count = 0
            errors = []
            
            # 处理所有待保存的消息
            for message_data in self.pending_saves:
                try:
                    saved_message = MessageCreate.create_sync(message_data)
                    if saved_message:
                        self._cache_message(saved_message)
                        processed_count += 1
                        self.stats["messages_saved"] += 1
                except Exception as e:
                    errors.append(f"保存消息失败: {str(e)}")
            
            # 清空待保存队列
            self.pending_saves.clear()
            
            return {
                "success": len(errors) == 0,
                "processed_count": processed_count,
                "errors": errors
            }
            
        except Exception as e:
            error_message = f"处理待保存消息失败: {str(e)}"
            print(f"Error in process_pending_saves: {error_message}")
            return {
                "success": False,
                "error": error_message
            }
    
    def _cache_message(self, message: Dict[str, Any]) -> None:
        """
        缓存消息
        
        Args:
            message: 消息数据
        """
        if message and "id" in message:
            # 限制缓存大小
            if len(self.recent_messages) >= 100:
                # 移除最旧的消息
                oldest_key = next(iter(self.recent_messages))
                del self.recent_messages[oldest_key]
            
            self.recent_messages[message["id"]] = message
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.recent_messages.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "stats": self.stats.copy(),
            "cache_size": len(self.recent_messages),
            "pending_saves": len(self.pending_saves)
        }