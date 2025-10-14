"""
工具结果处理器 - Python实现
对应TypeScript中的ToolResultProcessor类
"""
import logging
from typing import Dict, Any, Callable, Optional, List, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from .ai_client import AiClient
from .ai_request_handler import Message

logger = logging.getLogger(__name__)


class ToolResultProcessor:
    """
    工具结果处理器
    负责处理工具执行结果，包括内容摘要和最终内容生成
    """
    
    def __init__(self, ai_client: 'AiClient'):
        self.ai_client = ai_client
        self.max_content_length = 5000  # 最大内容长度
        
    def process_tool_result_sync(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        callback: Optional[Callable] = None
    ) -> str:
        """
        处理工具执行结果（同步版本）
        
        Args:
            tool_call_id: 工具调用ID
            tool_name: 工具名称
            result: 工具执行结果
            callback: 回调函数，用于流式输出
            
        Returns:
            处理后的结果字符串
        """
        try:
            # 将结果转换为字符串
            if isinstance(result, dict) or isinstance(result, list):
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result_str = str(result)
            
            # 检查内容长度
            if len(result_str) <= self.max_content_length:
                return result_str
            
            # 内容过长，直接截断（同步版本不生成摘要）
            logger.info(f"Tool result too long ({len(result_str)} chars), truncating")
            
            truncated = self._truncate_content(result_str)
            
            return truncated
            
        except Exception as e:
            logger.error(f"Error processing tool result: {e}")
            return f"Error processing tool result: {str(e)}"

    async def process_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any,
        callback: Optional[Callable] = None
    ) -> str:
        """
        处理工具执行结果
        
        Args:
            tool_call_id: 工具调用ID
            tool_name: 工具名称
            result: 工具执行结果
            callback: 回调函数，用于流式输出
            
        Returns:
            处理后的结果字符串
        """
        try:
            # 将结果转换为字符串
            if isinstance(result, dict) or isinstance(result, list):
                result_str = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result_str = str(result)
            
            # 检查内容长度
            if len(result_str) <= self.max_content_length:
                return result_str
            
            # 内容过长，需要生成摘要
            logger.info(f"Tool result too long ({len(result_str)} chars), generating summary")
            
            summary = await self._generate_summary(
                tool_name=tool_name,
                content=result_str,
                callback=callback
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error processing tool result: {e}")
            return f"Error processing tool result: {str(e)}"
    
    async def _generate_summary(
        self,
        tool_name: str,
        content: str,
        callback: Optional[Callable] = None
    ) -> str:
        """
        生成内容摘要
        
        Args:
            tool_name: 工具名称
            content: 原始内容
            callback: 回调函数
            
        Returns:
            摘要内容
        """
        try:
            # 构建摘要提示
            prompt = self._build_summary_prompt(tool_name, content)
            
            # 使用AI生成摘要
            summary_parts = []
            
            def summary_callback(callback_type: str, data: Any):
                if callback_type == "chunk" and data:
                    chunk_content = data.get("content", "")
                    if chunk_content:
                        summary_parts.append(chunk_content)
                        
                        # 如果有回调函数，发送摘要块
                        if callback:
                            callback("summary_chunk", {
                                "content": chunk_content
                            })
                
                # 传递其他回调
                if callback and callback_type != "chunk":
                    callback(callback_type, data)
            
            # 调用AI客户端生成摘要
            await self.ai_client.start(
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                callback=summary_callback
            )
            
            # 组合摘要内容
            summary = "".join(summary_parts).strip()
            
            if not summary:
                # 如果摘要生成失败，返回截断的原始内容
                summary = content[:self.max_content_length] + "...\n\n[Content truncated due to length]"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # 返回截断的原始内容
            return content[:self.max_content_length] + "...\n\n[Summary generation failed]"
    
    def _build_summary_prompt(self, tool_name: str, content: str) -> str:
        """
        构建摘要提示
        
        Args:
            tool_name: 工具名称
            content: 原始内容
            
        Returns:
            摘要提示字符串
        """
        return f"""Please provide a concise summary of the following {tool_name} tool execution result. 
Focus on the key information and main outcomes. Keep the summary under {self.max_content_length // 2} characters.

Tool: {tool_name}
Result:
{content[:self.max_content_length * 2]}

Summary:"""
    
    def _truncate_content(self, content: str, max_length: int = None) -> str:
        """
        截断内容
        
        Args:
            content: 原始内容
            max_length: 最大长度
            
        Returns:
            截断后的内容
        """
        if max_length is None:
            max_length = self.max_content_length
            
        if len(content) <= max_length:
            return content
            
        return content[:max_length] + "...\n\n[Content truncated due to length]"
    
    def set_max_content_length(self, length: int) -> None:
        """设置最大内容长度"""
        self.max_content_length = max(1000, length)  # 最小1000字符
        logger.info(f"Max content length set to {self.max_content_length}")
    
    def get_content_stats(self, content: str) -> Dict[str, Any]:
        """获取内容统计信息"""
        return {
            "length": len(content),
            "lines": content.count('\n') + 1,
            "needs_summary": len(content) > self.max_content_length,
            "max_length": self.max_content_length
        }