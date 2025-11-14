"""
对话摘要器
负责生成用户与助手对话的摘要，并可选择性保存摘要元数据
"""
import time
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
        对当前会话消息进行摘要，重点保留继续对话所需的关键数据和上下文。
        """
        try:
            # 仅保留 user/assistant 的对话供摘要
            conversation_messages_raw = [
                m for m in api_messages if m.get("role") in ("user", "assistant")
            ]
            conversation_messages: List[Dict[str, Any]] = []
            for m in conversation_messages_raw:
                conversation_messages.append({
                    "role": m.get("role"),
                    "content": m.get("content", "")
                })

            # 将所有对话合并为单一文本
            merged_dialog_text_lines: List[str] = []
            for m in conversation_messages:
                role = m.get("role", "user")
                content = str(m.get("content", ""))
                merged_dialog_text_lines.append(f"[{role}] {content}")
            merged_dialog_text = "\n\n".join(merged_dialog_text_lines).strip()

            system_message = {
                "role": "system",
                "content": (
                        "你是一个专业的对话摘要器。你的任务是为AI助手生成对话摘要，"
                        "这个摘要将作为后续对话的上下文，因此必须保留所有关键信息。\n\n"
                        "以下是当前会话的完整对话内容：\n\n"
                        + merged_dialog_text
                )
            }

            instruction = {
                "role": "user",
                "content": (
                    "请对上述对话生成一个结构化摘要，**重点保留继续对话所需的关键数据**。"
                    "摘要应包含以下部分：\n\n"

                    "## 🎯 用户初始需求（核心目标）\n"
                    "- **用户最初想要解决什么问题？**\n"
                    "- **用户的根本目标和期望结果是什么？**\n"
                    "- **用户提出需求的背景和动机**\n"
                    "- **需求的优先级和重要程度**\n\n"

                    "## 📋 当前任务与子目标\n"
                    "- 为实现初始需求，当前正在处理的具体任务\n"
                    "- 任务的分解和阶段性目标\n"
                    "- 与初始需求的关联关系\n\n"

                    "## 🔧 关键数据与参数\n"
                    "- 具体的配置参数、代码片段、文件路径\n"
                    "- 重要的数值、设置、约束条件\n"
                    "- 已确定的技术方案和架构决策\n"
                    "- 用户提供的具体要求和限制\n\n"

                    "## ✅ 当前进展状态\n"
                    "- 已完成的步骤和阶段性成果\n"
                    "- 已验证的方案和已排除的选项\n"
                    "- 遇到的问题及其解决方案\n"
                    "- **距离初始需求还有多远？**\n\n"

                    "## 📝 待办事项与下一步\n"
                    "- 明确的下一步行动计划\n"
                    "- 需要进一步确认的细节\n"
                    "- 潜在的风险点和注意事项\n"
                    "- **如何推进以达成用户的初始需求？**\n\n"

                    "## 🌍 重要上下文\n"
                    "- 用户的技术背景和偏好\n"
                    "- 项目环境和限制条件\n"
                    "- 相关的工具、框架、版本信息\n"
                    "- 用户的工作场景和使用习惯\n\n"

                    "**特别要求：**\n"
                    "1. **用户初始需求是整个摘要的核心**，必须清晰准确地表达\n"
                    "2. 所有后续内容都应该围绕如何满足这个初始需求来组织\n"
                    "3. 保留所有具体的技术细节，如代码、配置、参数等\n"
                    "4. 确保摘要信息足够详细，能让AI助手立即理解用户真正想要什么\n"
                    "5. 使用中文输出，格式清晰，重点信息用**粗体**标注\n"
                    "6. 如果用户需求在对话中有变化或细化，要明确记录这些变化\n\n"

                    "**核心原则：让AI助手能够快速回答用户到底想要什么？现在进展如何？下一步怎么做？**"
                )
            }

            summary_messages: List[Dict[str, Any]] = [system_message, instruction]

            resp = self.ai_request_handler.handle_request(
                messages=summary_messages,
                tools=None,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                session_id=None,
                on_chunk=on_chunk
            )

            if not resp.get("success"):
                print(f"[SUMMARIZER] 摘要请求失败: {resp.get('error')}")
                return None

            choice = resp.get("choices", [{}])[0]
            msg = choice.get("message", {})
            summary_text = msg.get("content")

            # 保存摘要消息
            try:
                if summary_text and hasattr(self.message_manager, "save_assistant_message"):
                    self.message_manager.save_assistant_message(
                        session_id=session_id,
                        content=summary_text,
                        summary=summary_text,
                        reasoning=None,
                        metadata={
                            "type": "conversation_summary",
                            "message_count": len(conversation_messages),
                            "summary_timestamp": int(time.time()),
                            "focus": "user_initial_requirements"  # 标记重点关注用户初始需求
                        }
                    )
            except Exception as se:
                print(f"[SUMMARIZER] 保存摘要消息失败: {se}")

            return summary_text
        except Exception as e:
            print(f"[SUMMARIZER] 生成摘要异常: {e}")
            return None
