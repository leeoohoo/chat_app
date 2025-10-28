#!/usr/bin/env python3
"""
测试工具调用日志输出 - 使用用户提供的真实工具调用格式
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
        # 模拟返回用户提供的工具调用格式
        return {
            "success": True,
            "choices": [{
                "message": {
                    "content": "我需要搜索包含'权限'关键词的文件。",
                    "tool_calls": [
                        {
                            'function': {
                                'arguments': '{"query": "权限"}', 
                                'name': 'file_reader_search_files_by_content'
                            }, 
                            'id': 'file_reader_search_files_by_content:0', 
                            'type': 'function'
                        }
                    ]
                }
            }]
        }

class MockMcpToolExecute:
    def get_available_tools(self):
        return [
            {
                "name": "file_reader_search_files_by_content", 
                "description": "搜索文件内容"
            }
        ]
    
    def execute_tools_with_validation(self, tool_calls, on_tool_result=None):
        # 模拟工具执行结果
        results = []
        for tool_call in tool_calls:
            result = {
                "tool_call_id": tool_call.get('id', 'unknown'),
                "tool_name": tool_call.get('function', {}).get('name', 'unknown'),
                "success": True,
                "content": f"找到3个包含'权限'的文件：\n1. config.py\n2. auth.py\n3. permissions.py"
            }
            results.append(result)
            
            # 如果有回调函数，调用它
            if on_tool_result:
                on_tool_result(result)
        
        return results

class MockToolResultProcessor:
    def process_tool_results(self, tool_results, session_id, generate_summary=False):
        return {
            "success": True,
            "processed_results": tool_results,
            "summary": "成功搜索到包含'权限'关键词的文件"
        }

class MockMessageManager:
    def get_cache_stats(self):
        return {"cache_hits": 0, "cache_misses": 0}

def test_tool_call_logging():
    """测试工具调用日志输出"""
    print("=== 测试工具调用日志输出 ===\n")
    print("模拟的工具调用格式:")
    print("[{'function': {'arguments': '{\"query\": \"权限\"}', 'name': 'file_reader_search_files_by_content'}, 'id': 'file_reader_search_files_by_content:0', 'type': 'function'}]")
    print("\n" + "="*50 + "\n")
    
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
    
    # 设置较小的最大迭代次数
    ai_client.set_max_iterations(3)
    
    # 测试消息
    test_messages = [
        {"role": "user", "content": "请搜索包含'权限'关键词的文件"}
    ]
    
    # 定义工具结果回调
    def on_tool_result(result):
        print(f"[CALLBACK] 工具结果回调: {result.get('tool_name', 'unknown')} - 成功: {result.get('success', False)}")
    
    # 执行测试
    try:
        print("开始执行AI客户端请求...\n")
        result = ai_client.process_request(
            messages=test_messages,
            session_id="test-tool-call-session",
            model="gpt-4",
            on_tool_result=on_tool_result
        )
        

        if result.get('final_response'):
            final_msg = result['final_response'].get('choices', [{}])[0].get('message', {})
            print(f"最终响应内容: {final_msg.get('content', 'N/A')}")
        
    except Exception as e:
        print(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tool_call_logging()