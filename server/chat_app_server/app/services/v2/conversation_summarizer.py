"""
对话摘要器
负责生成用户与助手对话的摘要，并可选择性保存摘要元数据
"""
from typing import List, Dict, Any, Optional, Callable


class ConversationSummarizer:
    """对话摘要器"""

    def __init__(self, ai_request_handler, message_manager):
        """
        初始化摘要器

        Args:
            ai_request_handler: AI请求处理器实例
            message_manager: 消息管理器实例
        """
        self.ai_request_handler = ai_request_handler
        self.message_manager = message_manager

    def summarize(self,
                  api_messages: List[Dict[str, Any]],
                  session_id: str,
                  model: str,
                  temperature: float,
                  max_tokens: Optional[int],
                  on_chunk: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        对当前会话消息进行摘要，仅基于用户与助手消息。

        Args:
            api_messages: 已格式化用于API的消息列表
            session_id: 会话ID
            model: 使用的模型
            temperature: 摘要生成的温度
            max_tokens: 摘要的最大token数

        Returns:
            摘要文本；失败返回None
        """
        try:
            # 仅保留 user/assistant 的对话供摘要，并移除任何工具相关字段，避免模型继续触发工具
            conversation_messages_raw = [
                m for m in api_messages if m.get("role") in ("user", "assistant")
            ]
            conversation_messages: List[Dict[str, Any]] = []
            for m in conversation_messages_raw:
                conversation_messages.append({
                    "role": m.get("role"),
                    "content": m.get("content", "")
                })

            # 将所有对话合并为单一文本，作为新的 system 提示
            merged_dialog_text_lines: List[str] = []
            for m in conversation_messages:
                role = m.get("role", "user")
                content = str(m.get("content", ""))
                # 为避免工具调用痕迹影响模型行为，这里不包含任何 tool_calls 等字段
                merged_dialog_text_lines.append(f"[{role}] {content}")
            merged_dialog_text = "\n\n".join(merged_dialog_text_lines).strip()

            system_message = {
                "role": "system",
                "content": (
                    "以下是当前会话的完整对话内容（按时间顺序，含角色标注）：\n\n"
                    + merged_dialog_text
                )
            }

            # 用户消息仅用于说明任务：请对这些对话做总结
            instruction = {
                "role": "user",
                "content": (
                    "请你对上述对话进行中文总结，简明扼要，包含关键事实、已作出的决定、重要参数/约束、"
                    "尚未解决的问题与下一步建议。输出纯文本摘要。"
                )
            }

            summary_messages: List[Dict[str, Any]] = [system_message, instruction]

            resp = self.ai_request_handler.handle_request(
                messages=summary_messages,
                tools=None,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                # 避免在处理器内自动写库，改为由本方法写入，避免重复
                session_id=None,
                # 支持将摘要内容按流式片段传给前端
                on_chunk=on_chunk
            )

            if not resp.get("success"):
                print(f"[SUMMARIZER] 摘要请求失败: {resp.get('error')}")
                return None

            choice = resp.get("choices", [{}])[0]
            msg = choice.get("message", {})
            summary_text = msg.get("content")

            # 将摘要作为一条助手消息保存，content 与 summary 同步填入，便于展示和检索
            try:
                if summary_text and hasattr(self.message_manager, "save_assistant_message"):
                    self.message_manager.save_assistant_message(
                        session_id=session_id,
                        content=summary_text,
                        summary=summary_text,
                        reasoning=None,
                        metadata={"type": "conversation_summary"}
                    )
            except Exception as se:
                print(f"[SUMMARIZER] 保存摘要消息失败: {se}")

            return summary_text
        except Exception as e:
            print(f"[SUMMARIZER] 生成摘要异常: {e}")
            return None