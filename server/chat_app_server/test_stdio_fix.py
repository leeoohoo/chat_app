#!/usr/bin/env python3
"""
测试修复后的 stdio 工具调用功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.v2.mcp_tool_execute import McpToolExecute

def test_stdio_tool_call():
    """测试 stdio 工具调用"""
    print("🧪 测试修复后的 stdio 工具调用功能")
    print("=" * 50)
    
    # 创建 stdio 服务器配置
    stdio_servers = [
        {
            "name": "file_reader",
            "command": "/Users/lilei/project/mcp_services/file_reader_server/file_reader_server.py",
            "alias": "test_reader",
            "args": ["stdio"]
        }
    ]
    
    try:
        # 创建 McpToolExecute 实例
        print("📝 创建 McpToolExecute 实例...")
        executor = McpToolExecute(
            mcp_servers=[],
            stdio_mcp_servers=stdio_servers,
            config_dir="/Users/lilei/project/config/test_mcp_server_config"
        )
        
        # 初始化工具列表
        print("🔧 初始化工具列表...")
        executor.init()
        
        # 获取可用工具
        tools = executor.get_tools()
        print(f"✅ 获取到 {len(tools)} 个工具")
        
        if len(tools) > 0:
            # 显示第一个工具
            first_tool = tools[0]
            tool_name = first_tool["function"]["name"]
            print(f"📋 第一个工具: {tool_name}")
            
            # 尝试调用一个简单的工具
            if "read_file_lines" in tool_name:
                print("🎯 测试 read_file_lines 工具调用...")
                
                tool_call = {
                    "id": "test_call_1",
                    "function": {
                        "name": tool_name,
                        "arguments": '{"file_path": "/Users/lilei/project/learn/chat_app/server/chat_app_server/README_PYTHON_IMPLEMENTATION.md", "start_line": 1, "end_line": 5}'
                    }
                }
                
                result = executor.execute_single_tool(tool_call)
                
                if result.get("is_error"):
                    print(f"❌ 工具调用失败: {result.get('content')}")
                else:
                    print(f"✅ 工具调用成功!")
                    print(f"📄 结果长度: {len(str(result.get('content', '')))}")
                    
            else:
                print("⚠️  没有找到 read_file_lines 工具，跳过调用测试")
        else:
            print("⚠️  没有获取到任何工具")
            
        print("\n🎉 测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_stdio_tool_call()
    sys.exit(0 if success else 1)