#!/usr/bin/env python3
"""
完整的工具流程测试
验证从 McpToolExecute 初始化到 OpenAI API 调用的整个工具传递链路
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.v2.mcp_tool_execute import McpToolExecute
from app.services.v2.ai_server import AiServer
from app.services.v2.ai_client import AiClient
from app.services.v2.ai_request_handler import AiRequestHandler


class TestCompleteToolFlow(unittest.TestCase):
    """测试完整的工具流程"""
    
    def setUp(self):
        """设置测试环境"""
        # 模拟 MCP 服务器配置
        self.mcp_servers = [
            {
                "name": "test_server",
                "url": "http://localhost:8080"
            }
        ]
        
        # 模拟工具响应
        self.mock_tools_response = {
            "tools": [
                {
                    "name": "calculator",
                    "description": "计算器工具",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "运算类型"
                            },
                            "a": {
                                "type": "number",
                                "description": "第一个数字"
                            },
                            "b": {
                                "type": "number",
                                "description": "第二个数字"
                            }
                        },
                        "required": ["operation", "a", "b"]
                    }
                }
            ]
        }
        
        # 模拟 OpenAI 响应
        self.mock_openai_response = Mock()
        self.mock_openai_response.choices = [Mock()]
        self.mock_openai_response.choices[0].message = Mock()
        self.mock_openai_response.choices[0].message.content = "测试响应"
        self.mock_openai_response.choices[0].message.tool_calls = None
    
    @patch('app.services.v2.mcp_tool_execute.requests.post')
    def test_complete_tool_flow(self, mock_post):
        """测试完整的工具流程"""
        print("🧪 测试完整的工具流程...")
        
        # 1. 模拟 HTTP 请求响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_tools_response
        mock_post.return_value = mock_response
        
        # 2. 创建并初始化 McpToolExecute
        mcp_tool_execute = McpToolExecute(self.mcp_servers)
        mcp_tool_execute.init()
        
        # 3. 验证工具列表已构建
        tools = mcp_tool_execute.get_available_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["function"]["name"], "test_server_calculator")
        print(f"✅ 工具列表已构建: {len(tools)} 个工具")
        
        # 4. 创建 AiServer 实例
        with patch('app.services.v2.ai_server.OpenAI') as mock_openai_class:
            mock_openai_client = Mock()
            mock_openai_class.return_value = mock_openai_client
            
            # 模拟 OpenAI 客户端的 chat.completions.create 方法
            mock_openai_client.chat.completions.create.return_value = self.mock_openai_response
            
            ai_server = AiServer(
                openai_api_key="test_key",
                mcp_tool_execute=mcp_tool_execute
            )
            
            # 5. 验证 AiServer 可以获取工具列表
            available_tools = ai_server.get_available_tools()
            self.assertEqual(len(available_tools), 1)
            print(f"✅ AiServer 可以获取工具列表: {len(available_tools)} 个工具")
            
            # 6. 模拟聊天请求
            result = ai_server.chat(
                session_id="test_session",
                user_message="请帮我计算 2 + 3",
                use_tools=True
            )
            
            # 7. 验证 OpenAI API 被正确调用
            mock_openai_client.chat.completions.create.assert_called()
            call_args = mock_openai_client.chat.completions.create.call_args
            
            # 8. 验证工具列表被传递给 OpenAI API
            self.assertIn('tools', call_args.kwargs)
            passed_tools = call_args.kwargs['tools']
            self.assertEqual(len(passed_tools), 1)
            self.assertEqual(passed_tools[0]["function"]["name"], "test_server_calculator")
            print(f"✅ 工具列表已传递给 OpenAI API: {len(passed_tools)} 个工具")
            
            # 9. 验证 tool_choice 参数
            self.assertEqual(call_args.kwargs.get('tool_choice'), 'auto')
            print("✅ tool_choice 参数设置正确")
            
            # 10. 验证聊天结果
            self.assertTrue(result.get('success', True))
            print("✅ 聊天请求处理成功")
    
    @patch('app.services.v2.mcp_tool_execute.requests.post')
    def test_tool_flow_without_tools(self, mock_post):
        """测试不使用工具的流程"""
        print("\n🧪 测试不使用工具的流程...")
        
        # 1. 模拟 HTTP 请求响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_tools_response
        mock_post.return_value = mock_response
        
        # 2. 创建并初始化 McpToolExecute
        mcp_tool_execute = McpToolExecute(self.mcp_servers)
        mcp_tool_execute.init()
        
        # 3. 创建 AiServer 实例
        with patch('app.services.v2.ai_server.OpenAI') as mock_openai_class:
            mock_openai_client = Mock()
            mock_openai_class.return_value = mock_openai_client
            mock_openai_client.chat.completions.create.return_value = self.mock_openai_response
            
            ai_server = AiServer(
                openai_api_key="test_key",
                mcp_tool_execute=mcp_tool_execute
            )
            
            # 4. 模拟不使用工具的聊天请求
            result = ai_server.chat(
                session_id="test_session",
                user_message="你好",
                use_tools=False
            )
            
            # 5. 验证 OpenAI API 被调用但没有传递工具
            mock_openai_client.chat.completions.create.assert_called()
            call_args = mock_openai_client.chat.completions.create.call_args
            
            # 6. 验证没有工具参数传递
            self.assertNotIn('tools', call_args.kwargs)
            self.assertNotIn('tool_choice', call_args.kwargs)
            print("✅ 不使用工具时，工具参数未传递给 OpenAI API")
    
    def test_empty_mcp_servers(self):
        """测试空的 MCP 服务器列表"""
        print("\n🧪 测试空的 MCP 服务器列表...")
        
        # 1. 创建空的 MCP 服务器列表
        empty_mcp_servers = []
        
        # 2. 创建并初始化 McpToolExecute
        mcp_tool_execute = McpToolExecute(empty_mcp_servers)
        mcp_tool_execute.init()
        
        # 3. 验证工具列表为空
        tools = mcp_tool_execute.get_available_tools()
        self.assertEqual(len(tools), 0)
        print("✅ 空的 MCP 服务器列表产生空的工具列表")
        
        # 4. 创建 AiServer 实例
        with patch('app.services.v2.ai_server.OpenAI') as mock_openai_class:
            mock_openai_client = Mock()
            mock_openai_class.return_value = mock_openai_client
            mock_openai_client.chat.completions.create.return_value = self.mock_openai_response
            
            ai_server = AiServer(
                openai_api_key="test_key",
                mcp_tool_execute=mcp_tool_execute
            )
            
            # 5. 模拟聊天请求
            result = ai_server.chat(
                session_id="test_session",
                user_message="你好",
                use_tools=True
            )
            
            # 6. 验证 OpenAI API 被调用但没有工具
            mock_openai_client.chat.completions.create.assert_called()
            call_args = mock_openai_client.chat.completions.create.call_args
            
            # 7. 验证没有工具参数传递（因为工具列表为空）
            self.assertNotIn('tools', call_args.kwargs)
            print("✅ 空工具列表时，工具参数未传递给 OpenAI API")
    
    def test_tool_metadata_consistency(self):
        """测试工具元数据的一致性"""
        print("\n🧪 测试工具元数据的一致性...")
        
        with patch('app.services.v2.mcp_tool_execute.requests.post') as mock_post:
            # 1. 模拟 HTTP 请求响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = self.mock_tools_response
            mock_post.return_value = mock_response
            
            # 2. 创建并初始化 McpToolExecute
            mcp_tool_execute = McpToolExecute(self.mcp_servers)
            mcp_tool_execute.init()
            
            # 3. 验证工具元数据
            tools = mcp_tool_execute.get_available_tools()
            self.assertEqual(len(tools), 1, "应该有一个工具")
            tool = tools[0]
            
            # 4. 验证工具格式符合 OpenAI 规范
            self.assertIn("type", tool)
            self.assertEqual(tool["type"], "function")
            self.assertIn("function", tool)
            
            function = tool["function"]
            self.assertIn("name", function)
            self.assertIn("description", function)
            self.assertIn("parameters", function)
            
            # 5. 验证工具元数据存储
            self.assertIn("test_server_calculator", mcp_tool_execute.tool_metadata)
            metadata = mcp_tool_execute.tool_metadata["test_server_calculator"]
            self.assertEqual(metadata["server_name"], "test_server")
            self.assertEqual(metadata["original_name"], "calculator")
            self.assertEqual(metadata["server_url"], "http://localhost:8080")
            
            print("✅ 工具元数据格式和存储正确")


def main():
    """运行测试"""
    print("🚀 开始完整的工具流程测试...\n")
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCompleteToolFlow)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print(f"\n📊 测试总结:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ 失败的测试:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    if result.wasSuccessful():
        print(f"\n🎉 所有测试通过！工具流程验证成功！")
        return True
    else:
        print(f"\n😞 测试失败，请检查问题。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)