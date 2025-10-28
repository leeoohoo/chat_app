#!/usr/bin/env python3
"""
测试修复后的 MCP 工具调用
验证 call 方法调用是否正常工作
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.services.v2.mcp_tool_execute import McpToolExecute


def test_mcp_tool_execute():
    """测试 MCP 工具执行器"""
    print("🧪 测试修复后的 MCP 工具调用...")
    
    # 配置 stdio MCP 服务器
    stdio_servers = [
        {
            "name": "file_reader",
            "command": "python",
            "args": ["file_reader_server.py", "stdio"],
            "alias": "test_fix",
            "env": {}
        }
    ]
    
    # 创建执行器
    executor = McpToolExecute(
        stdio_mcp_servers=stdio_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    )
    
    try:
        # 初始化工具
        print("📋 初始化工具...")
        executor.init()
        
        # 获取可用工具
        tools = executor.get_available_tools()
        print(f"✅ 找到 {len(tools)} 个工具")
        
        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
        
        # 测试工具调用
        if tools:
            print("\n🔧 测试工具调用...")
            
            # 构造一个简单的工具调用
            tool_call = {
                "id": "test_call_123",
                "function": {
                    "name": tools[0]["name"],  # 使用第一个工具
                    "arguments": "{}"  # 空参数
                }
            }
            
            print(f"调用工具: {tool_call['function']['name']}")
            
            # 执行工具调用
            result = executor.execute_single_tool(tool_call)
            
            print(f"✅ 工具调用成功!")
            print(f"   工具ID: {result.get('tool_call_id')}")
            print(f"   工具名: {result.get('name')}")
            print(f"   是否错误: {result.get('is_error')}")
            print(f"   结果长度: {len(str(result.get('content', '')))}")
            
            if not result.get('is_error'):
                print("🎉 MCP 工具调用修复成功!")
                return True
            else:
                print(f"❌ 工具调用返回错误: {result.get('content')}")
                return False
        else:
            print("❌ 没有找到可用工具")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mcp_tool_execute()
    if success:
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)