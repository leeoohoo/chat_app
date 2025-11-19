"""
Agent 工具执行器
直接接收 callable_agent_ids 构建 OpenAI SDK 工具列表，
并支持按工具调用对应的子智能体（单一入参：questions）。
"""

import json
from typing import Dict, List, Any, Optional, Callable

from app.models.config import AgentCreate
# 延迟导入以避免循环依赖，在执行时再导入需要的方法


def _json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


class AgentToolExecute:
    """
    基于主智能体的可调用智能体列表，构建工具并执行调用。

    - 工具名称："agent_<agent_id>"（确保唯一）
    - 工具描述：使用子智能体的 name + description
    - 工具参数：仅一个字符串参数 "questions"
    """

    def __init__(
        self,
        callable_agent_ids: Any,
        user_id: Optional[str] = None,
    ):
        """
        callable_agent_ids 可为 List[str] 或 JSON 字符串。
        """
        self.callable_agent_ids = self._normalize_ids(callable_agent_ids)
        self.user_id = user_id
        self.tools: List[Dict[str, Any]] = []
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}

    def init(self):
        self.build_tools()

    def build_tools(self):
        """构建可调用的 Agent 工具列表。"""
        self.tools = []
        self.tool_metadata = {}

        for aid in self.callable_agent_ids or []:
            try:
                agent = _run_async(AgentCreate.get_by_id(aid))
                if not agent or not agent.get("enabled", True):
                    continue

                name = agent.get("name") or f"agent_{aid[:8]}"
                desc = agent.get("description") or ""
                tool_name = f"agent_{aid}"

                # 元数据映射
                self.tool_metadata[tool_name] = {
                    "agent_id": aid,
                    "name": name,
                    "description": desc,
                    "type": "agent",
                }

                # OpenAI 工具规范
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Agent: {name} - {desc}".strip(),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "questions": {
                                    "type": "string",
                                    "description": "问题字符串（传给子智能体）",
                                }
                            },
                            "required": ["questions"],
                        },
                    },
                }
                self.tools.append(openai_tool)
            except Exception:
                continue

    def get_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    def find_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        return self.tool_metadata.get(tool_name)

    def execute_single_tool_stream(
        self,
        tool_call: Dict[str, Any],
        on_tool_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        执行单个子智能体调用：将 quitions 作为用户消息传入对应子智能体。
        返回统一结构：{ tool_call_id, name, success, is_error, content }
        """
        try:
            function_info = tool_call.get("function", {})
            tool_name = function_info.get("name")
            arguments_str = function_info.get("arguments", "{}")
            tool_call_id = tool_call.get("id", "")

            if not tool_name:
                result = {
                    "tool_call_id": tool_call_id,
                    "name": "unknown",
                    "success": False,
                    "is_error": True,
                    "content": "工具名称不能为空",
                }
                if on_tool_stream:
                    on_tool_stream(result)
                return result

            info = self.find_tool_info(tool_name)
            if not info:
                result = {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "success": False,
                    "is_error": True,
                    "content": f"未找到对应子智能体: {tool_name}",
                }
                if on_tool_stream:
                    on_tool_stream(result)
                return result

            try:
                if isinstance(arguments_str, str):
                    arguments = json.loads(arguments_str) if arguments_str else {}
                elif isinstance(arguments_str, dict):
                    arguments = arguments_str
                else:
                    arguments = {}
            except json.JSONDecodeError as e:
                result = {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "success": False,
                    "is_error": True,
                    "content": f"参数解析失败: {str(e)}",
                }
                if on_tool_stream:
                    on_tool_stream(result)
                return result

            question = arguments.get("questions") or ""
            target_agent_id = info["agent_id"]

            # 加载子智能体的模型配置并创建 Agent（延迟导入）
            from app.services.v2.agent import load_model_config_for_agent, create_agent
            model_cfg = load_model_config_for_agent(target_agent_id)
            agent = create_agent(
                api_key=model_cfg.get("api_key"),
                base_url=model_cfg.get("base_url"),
                model_name=model_cfg.get("model_name", "gpt-4"),
                system_prompt=model_cfg.get("system_prompt"),
                temperature=model_cfg.get("temperature", 0.7),
                max_tokens=model_cfg.get("max_tokens"),
                user_id=self.user_id,
            )

            # 执行聊天（允许子智能体使用其工具）
            result_obj = agent.chat(
                user_message=question,
                session_id=f"agent_call_{target_agent_id}",
                use_tools=True,
            )

            content_text = _json_dumps(result_obj)
            final = {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "success": True,
                "is_error": False,
                "content": content_text,
            }
            if on_tool_stream:
                on_tool_stream(final)
            return final

        except Exception as e:
            error_result = {
                "tool_call_id": tool_call.get("id", ""),
                "name": tool_call.get("function", {}).get("name", "unknown"),
                "success": False,
                "is_error": True,
                "content": f"子智能体执行失败: {str(e)}",
            }
            if on_tool_stream:
                on_tool_stream(error_result)
            return error_result

    def execute_tools_stream(
        self,
        tool_calls: List[Dict[str, Any]],
        on_tool_result: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for tc in tool_calls:
            res = self.execute_single_tool_stream(tc, on_tool_result)
            results.append(res)
        return results

    def execute_agents_stream(
        self,
        tool_calls: List[Dict[str, Any]],
        on_agent_start: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        on_agent_stream: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_agent_end: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        针对 agent 的三段式回调：start/stream/end。
        - on_agent_start: 传入待调用的 agent 列表元信息
        - on_agent_stream: 每个 agent 执行后的即时结果
        - on_agent_end: 所有 agent 执行完成后的结果列表
        返回所有结果列表。
        """
        # 构造启动阶段的元信息列表
        start_list: List[Dict[str, Any]] = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name")
            info = self.find_tool_info(name) if name else None
            start_list.append({
                "tool_call_id": tc.get("id", ""),
                "tool_name": name,
                "agent_id": info.get("agent_id") if info else None,
                "name": info.get("name") if info else None,
                "description": info.get("description") if info else None,
            })
        if on_agent_start:
            try:
                on_agent_start(start_list)
            except Exception:
                pass

        # 执行并在流阶段回调
        results: List[Dict[str, Any]] = []
        for tc in tool_calls:
            res = self.execute_single_tool_stream(tc, on_agent_stream)
            results.append(res)

        # 结束阶段回调
        if on_agent_end:
            try:
                on_agent_end(results)
            except Exception:
                pass
        return results

    def get_tool_execution_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        error = total - success
        return {
            "total_count": total,
            "success_count": success,
            "error_count": error,
            "success_rate": success / total if total > 0 else 0,
        }

    @staticmethod
    def _normalize_ids(ids: Any) -> List[str]:
        if ids is None:
            return []
        if isinstance(ids, list):
            return [str(x) for x in ids]
        if isinstance(ids, str):
            try:
                parsed = json.loads(ids)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                # 单个字符串当作一个 id
                return [ids]
        return []


def _run_async(coro):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        import asyncio
        return asyncio.run(coro)