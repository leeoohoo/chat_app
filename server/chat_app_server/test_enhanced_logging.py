#!/usr/bin/env python3
"""
测试增强后的AI客户端日志输出
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.v2.ai_client import AiClient

# 模拟依赖
class MockAiRequestHandler:
    def prepare_messages_for_api(self, messages):
        return messages
    
    def handle_request(self, **kwargs):
        return {
            "success": True,
            "choices": [{
                "message": {
                    "content": "测试响应",
                    "tool_calls": [{
                        "id": "test_call_1",
                        "function": {
                            "name": "test_tool",
                            "arguments": "{}"
                        }
                    }]
                }
            }]
        }

class MockMcpToolExecute:
    def get_available_tools(self):
        return [{"name": "test_tool", "description": "测试工具"}]
    
    def execute_tools_with_validation(self, tool_calls, on_tool_result=None):
        # 模拟工具执行失败的情况
        return [{
            "tool_call_id": "test_call_1",
            "tool_name": "test_tool",  # 注意这里有正确的tool_name
            "success": False,
            "error": "模拟的工具执行错误",
            "content": "工具执行失败"
        }]

class MockToolResultProcessor:
    def process_tool_results(self, tool_results, session_id, generate_summary=False):
        return {
            "success": True,
            "processed_results": tool_results
        }

class MockMessageManager:
    def get_cache_stats(self):
        return {"cache_hits": 0, "cache_misses": 0}

def test_enhanced_logging():
    """测试增强后的日志输出"""
    print("=== 开始测试增强后的AI客户端日志 ===\n")
    
    # 创建模拟依赖
    ai_request_handler = MockAiRequestHandler()
    mcp_tool_execute = MockMcpToolExecute()
    tool_result_processor = MockToolResultProcessor()
    message_manager = MockMessageManager()
    
    # 创建AI客户端
    ai_client = AiClient(
        ai_request_handler=ai_request_handler,
        mcp_tool_execute=mcp_tool_execute,
        tool_result_processor=tool_result_processor,
        message_manager=message_manager
    )
    
    # 设置较小的最大迭代次数以便测试
    ai_client.set_max_iterations(5)
    
    # 测试消息
    test_messages = [
        {"role": "user", "content": "请帮我测试工具调用"}
    ]
    
    # 执行测试
    try:
        result = ai_client.process_request(
            messages=test_messages,
            session_id="test-session-123",
            model="test-model"
        )
        #
        # print(f"\n=== 测试完成 ===")
        # print(f"最终结果: {result.get('success', False)}")
        # print(f"迭代次数: {result.get('iterations', 0)}")
        
    except Exception as e:
        print(f"测试过程中出现异常: {e}")

if __name__ == "__main__":
    test_enhanced_logging()