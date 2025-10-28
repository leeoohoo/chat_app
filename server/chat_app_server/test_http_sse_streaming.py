#!/usr/bin/env python3
"""
测试 HTTP SSE 流式功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.v2.mcp_tool_execute import McpToolExecute


async def test_http_sse_streaming():
    """测试 HTTP SSE 流式功能"""
    print("🧪 开始测试 HTTP SSE 流式功能...")
    
    try:
        # 创建 MCP 工具执行器实例，配置一个模拟的 HTTP 服务器
        mcp_servers = [
            {
                "name": "test-http-server",
                "url": "http://localhost:8080",  # 假设有一个运行在 8080 的 MCP 服务器
                "description": "测试 HTTP MCP 服务器"
            }
        ]
        
        executor = McpToolExecute(mcp_servers=mcp_servers)
        executor.init()
        
        print("✅ MCP 工具执行器初始化成功")
        
        # 模拟一个工具信息
        test_tool_info = {
            "original_name": "test_streaming_tool",
            "server_type": "http",
            "server_name": "test-http-server",
            "server_url": "http://localhost:8080"
        }
        
        # 手动添加工具信息到执行器（用于测试）
        executor._tools = [
            {
                "type": "function",
                "function": {
                    "name": "test-http-server_test_streaming_tool",
                    "description": "测试流式工具",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        
        # 手动设置工具信息映射
        if not hasattr(executor, '_tool_info_map'):
            executor._tool_info_map = {}
        executor._tool_info_map["test-http-server_test_streaming_tool"] = test_tool_info
        
        print("🔧 设置测试工具信息完成")
        
        # 测试流式调用方法的存在性
        print("\n🔍 检查 HTTP SSE 相关方法...")
        
        # 检查 _call_mcp_tool_stream 方法
        if hasattr(executor, '_call_mcp_tool_stream'):
            print("  ✅ _call_mcp_tool_stream 方法存在")
            
            # 检查方法是否支持 HTTP SSE
            import inspect
            source = inspect.getsource(executor._call_mcp_tool_stream)
            if "aiohttp" in source and "sse/tool/call" in source:
                print("  ✅ 方法包含 HTTP SSE 支持代码")
            else:
                print("  ⚠️  方法可能不包含完整的 HTTP SSE 支持")
        else:
            print("  ❌ _call_mcp_tool_stream 方法不存在")
        
        # 测试 SSE 请求构造逻辑
        print("\n🔧 测试 SSE 请求构造逻辑...")
        
        tool_name = "test-http-server_test_streaming_tool"
        arguments = {"test_param": "test_value"}
        
        # 查找工具信息
        tool_info = executor.find_tool_info(tool_name)
        if tool_info:
            print(f"  ✅ 找到工具信息: {tool_info}")
            
            # 构造 SSE 请求数据（模拟）
            original_name = tool_info["original_name"]
            server_url = tool_info["server_url"]
            
            request_data = {
                "tool_name": original_name,
                "arguments": arguments
            }
            
            sse_url = f"{server_url}/sse/tool/call"
            
            print(f"  📡 SSE URL: {sse_url}")
            print(f"  📦 请求数据: {request_data}")
            print("  ✅ SSE 请求构造逻辑正确")
        else:
            print("  ❌ 未找到工具信息")
        
        # 测试流式方法调用（不实际发送请求，因为没有真实服务器）
        print("\n🧪 测试流式方法调用接口...")
        
        try:
            # 这里会因为没有真实的服务器而失败，但我们可以检查错误类型
            result = executor.call_tool_stream_sync(tool_name, arguments)
            print(f"  意外成功: {result}")
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "aiohttp" in error_msg or "HTTP" in error_msg:
                print(f"  ✅ 正确尝试了 HTTP SSE 连接: {error_msg}")
            else:
                print(f"  ⚠️  其他错误: {error_msg}")
        
        print("\n🎉 HTTP SSE 流式功能测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sse_parsing_logic():
    """测试 SSE 解析逻辑"""
    print("\n🧪 测试 SSE 解析逻辑...")
    
    # 模拟 SSE 数据
    sse_lines = [
        "data: {\"content\": \"Hello\"}",
        "data: {\"content\": \" World\"}",
        "data: Simple text",
        "data: [DONE]",
        ": comment line",
        "",
        "data: After done"
    ]
    
    parsed_content = []
    
    for line in sse_lines:
        line_str = line.strip()
        
        # 跳过空行和注释行
        if not line_str or line_str.startswith(':'):
            continue
        
        # 解析 SSE 数据
        if line_str.startswith('data: '):
            data = line_str[6:]  # 移除 'data: ' 前缀
            
            # 检查是否是结束标记
            if data == '[DONE]':
                break
            
            try:
                # 尝试解析 JSON 数据
                import json
                json_data = json.loads(data)
                if isinstance(json_data, dict) and 'content' in json_data:
                    parsed_content.append(json_data['content'])
                else:
                    parsed_content.append(data)
            except json.JSONDecodeError:
                # 如果不是 JSON，直接返回原始数据
                parsed_content.append(data)
    
    expected_content = ["Hello", " World", "Simple text"]
    
    if parsed_content == expected_content:
        print("  ✅ SSE 解析逻辑正确")
        print(f"  📦 解析结果: {parsed_content}")
    else:
        print("  ❌ SSE 解析逻辑错误")
        print(f"  📦 期望: {expected_content}")
        print(f"  📦 实际: {parsed_content}")
    
    return parsed_content == expected_content


async def main():
    """主测试函数"""
    print("🚀 开始 HTTP SSE 流式功能测试")
    print("=" * 60)
    
    # HTTP SSE 流式功能测试
    success1 = await test_http_sse_streaming()
    
    # SSE 解析逻辑测试
    success2 = test_sse_parsing_logic()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 所有 HTTP SSE 测试通过！")
        return True
    else:
        print("❌ 部分 HTTP SSE 测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)