#!/usr/bin/env python3
"""
测试修正后的 McpToolExecute 实现
验证与前端架构的一致性
"""
import sys
import os
import json
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.v2.mcp_tool_execute import McpToolExecute


def test_basic_initialization():
    """测试基本初始化"""
    print("=== 测试基本初始化 ===")
    
    mcp_servers = [
        {"name": "test_server", "url": "http://localhost:8080"},
        {"name": "file_server", "url": "http://localhost:9000"}
    ]
    
    executor = McpToolExecute(mcp_servers)
    
    assert executor.mcp_servers == mcp_servers
    assert executor.tools == []
    assert executor.tool_metadata == {}
    
    print("✅ 基本初始化测试通过")


def test_build_tools_mock():
    """测试构建工具列表（使用模拟响应）"""
    print("\n=== 测试构建工具列表 ===")
    
    mcp_servers = [
        {"name": "test_server", "url": "http://localhost:8080"}
    ]
    
    executor = McpToolExecute(mcp_servers)
    
    # 模拟 HTTP 响应
    mock_response = Mock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test",
        "result": {
            "tools": [
                {
                    "name": "calculator",
                    "description": "计算器工具",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "operation": {"type": "string"},
                            "a": {"type": "number"},
                            "b": {"type": "number"}
                        }
                    }
                },
                {
                    "name": "greet",
                    "description": "问候工具",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        }
                    }
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    
    with patch.object(executor.session, 'post', return_value=mock_response):
        executor.build_tools()
    
    # 验证工具列表
    tools = executor.get_tools()
    assert len(tools) == 2
    
    # 验证工具格式
    tool1 = tools[0]
    assert tool1["type"] == "function"
    assert tool1["function"]["name"] == "test_server_calculator"
    assert tool1["function"]["description"] == "计算器工具"
    
    tool2 = tools[1]
    assert tool2["function"]["name"] == "test_server_greet"
    
    # 验证工具元数据
    metadata1 = executor.find_tool_info("test_server_calculator")
    assert metadata1["original_name"] == "calculator"
    assert metadata1["server_name"] == "test_server"
    assert metadata1["server_url"] == "http://localhost:8080"
    
    print("✅ 构建工具列表测试通过")
    print(f"   构建了 {len(tools)} 个工具")
    for tool in tools:
        print(f"   - {tool['function']['name']}: {tool['function']['description']}")


def test_call_mcp_tool_mock():
    """测试调用 MCP 工具（使用模拟响应）"""
    print("\n=== 测试调用 MCP 工具 ===")
    
    mcp_servers = [
        {"name": "test_server", "url": "http://localhost:8080"}
    ]
    
    executor = McpToolExecute(mcp_servers)
    
    # 先设置工具元数据
    executor.tool_metadata["test_server_calculator"] = {
        "original_name": "calculator",
        "server_name": "test_server",
        "server_url": "http://localhost:8080",
        "supports_streaming": True
    }
    
    # 模拟工具调用响应
    mock_response = Mock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test",
        "result": {
            "content": "计算结果: 15",
            "isError": False
        }
    }
    mock_response.raise_for_status.return_value = None
    
    with patch.object(executor.session, 'post', return_value=mock_response):
        result = executor._call_mcp_tool("test_server_calculator", {
            "operation": "add",
            "a": 10,
            "b": 5
        })
    
    assert result["content"] == "计算结果: 15"
    assert result["isError"] == False
    
    print("✅ 调用 MCP 工具测试通过")
    print(f"   调用结果: {result}")


def test_execute_tools():
    """测试执行工具调用"""
    print("\n=== 测试执行工具调用 ===")
    
    mcp_servers = [
        {"name": "test_server", "url": "http://localhost:8080"}
    ]
    
    executor = McpToolExecute(mcp_servers)
    
    # 设置工具元数据
    executor.tool_metadata["test_server_greet"] = {
        "original_name": "greet",
        "server_name": "test_server", 
        "server_url": "http://localhost:8080",
        "supports_streaming": True
    }
    
    # 模拟工具调用响应
    mock_response = Mock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": "test",
        "result": "你好，张三！"
    }
    mock_response.raise_for_status.return_value = None
    
    tool_calls = [
        {
            "id": "call_123",
            "function": {
                "name": "test_server_greet",
                "arguments": json.dumps({"name": "张三"})
            }
        }
    ]
    
    with patch.object(executor.session, 'post', return_value=mock_response):
        results = executor.execute_tools(tool_calls)
    
    assert len(results) == 1
    result = results[0]
    assert result["tool_call_id"] == "call_123"
    assert result["name"] == "test_server_greet"
    assert result["is_error"] == False
    
    print("✅ 执行工具调用测试通过")
    print(f"   执行结果: {result}")


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    executor = McpToolExecute([])
    
    # 测试工具未找到
    try:
        executor._call_mcp_tool("nonexistent_tool", {})
        assert False, "应该抛出异常"
    except Exception as e:
        assert "工具未找到" in str(e)
        print("✅ 工具未找到错误处理正确")
    
    # 测试无效的工具调用
    tool_calls = [
        {
            "id": "call_456",
            "function": {
                "name": "invalid_tool",
                "arguments": "invalid_json"
            }
        }
    ]
    
    results = executor.execute_tools(tool_calls)
    assert len(results) == 1
    assert results[0]["is_error"] == True
    
    print("✅ 错误处理测试通过")


def test_architecture_consistency():
    """测试与前端架构的一致性"""
    print("\n=== 测试与前端架构的一致性 ===")
    
    mcp_servers = [
        {"name": "server1", "url": "http://localhost:8080"},
        {"name": "server2", "url": "http://localhost:9000"}
    ]
    
    executor = McpToolExecute(mcp_servers)
    
    # 检查关键方法是否存在
    assert hasattr(executor, 'init'), "缺少 init 方法"
    assert hasattr(executor, 'build_tools'), "缺少 build_tools 方法"
    assert hasattr(executor, 'get_tools'), "缺少 get_tools 方法"
    assert hasattr(executor, 'find_tool_info'), "缺少 find_tool_info 方法"
    assert hasattr(executor, 'execute_tools'), "缺少 execute_tools 方法"
    
    # 检查属性
    assert hasattr(executor, 'mcp_servers'), "缺少 mcp_servers 属性"
    assert hasattr(executor, 'tools'), "缺少 tools 属性"
    assert hasattr(executor, 'tool_metadata'), "缺少 tool_metadata 属性"
    assert hasattr(executor, 'session'), "缺少 session 属性"
    
    # 检查初始状态
    assert executor.tools == []
    assert executor.tool_metadata == {}
    assert executor.mcp_servers == mcp_servers
    
    print("✅ 与前端架构一致性测试通过")
    print("   所有必要的方法和属性都存在")


def main():
    """运行所有测试"""
    print("开始测试修正后的 McpToolExecute 实现")
    print("=" * 50)
    
    try:
        test_basic_initialization()
        test_build_tools_mock()
        test_call_mcp_tool_mock()
        test_execute_tools()
        test_error_handling()
        test_architecture_consistency()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试通过！")
        print("\n修正后的 McpToolExecute 特性:")
        print("✅ 移除了错误的 mcp_client 概念")
        print("✅ 直接处理 mcp_servers 配置")
        print("✅ 通过 HTTP 请求获取工具列表")
        print("✅ 实现工具元数据管理")
        print("✅ 直接通过 HTTP 调用 MCP 服务器")
        print("✅ 与前端架构保持一致")
        print("✅ 使用正确的 Python 语法（无 async/await）")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)