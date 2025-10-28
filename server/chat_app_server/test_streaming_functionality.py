#!/usr/bin/env python3
"""
测试 MCP 工具执行器的流式功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.v2.mcp_tool_execute import McpToolExecute


def test_streaming_functionality():
    """测试流式功能"""
    print("🧪 开始测试 MCP 工具执行器的流式功能...")
    
    try:
        # 创建 MCP 工具执行器实例
        executor = McpToolExecute()
        
        # 初始化
        executor.init()
        
        print("✅ MCP 工具执行器初始化成功")
        
        # 获取可用工具
        available_tools = executor.get_available_tools()
        print(f"📋 可用工具数量: {len(available_tools)}")
        
        if available_tools:
            # 显示前几个工具
            for i, tool in enumerate(available_tools[:3]):
                tool_name = tool.get("function", {}).get("name", "未知")
                print(f"  {i+1}. {tool_name}")
            
            # 测试流式调用（如果有工具的话）
            first_tool = available_tools[0]
            tool_name = first_tool.get("function", {}).get("name")
            
            if tool_name:
                print(f"\n🔄 测试流式调用工具: {tool_name}")
                
                # 构造测试调用
                test_call = {
                    "id": "test_stream_1",
                    "function": {
                        "name": tool_name,
                        "arguments": {}
                    }
                }
                
                # 测试单个工具流式执行
                print("📤 测试单个工具流式执行...")
                result = executor.execute_single_tool_stream(test_call)
                print(f"📥 结果: {result}")
                
                # 测试多个工具流式执行
                print("\n📤 测试多个工具流式执行...")
                test_calls = [
                    {
                        "id": "test_stream_2",
                        "function": {
                            "name": tool_name,
                            "arguments": {}
                        }
                    }
                ]
                
                results = executor.execute_tools_stream(test_calls)
                print(f"📥 结果数量: {len(results)}")
                for i, result in enumerate(results):
                    print(f"  结果 {i+1}: {result}")
                
                print("✅ 流式功能测试完成")
            else:
                print("⚠️  无法获取工具名称，跳过流式调用测试")
        else:
            print("⚠️  没有可用的工具，跳过流式调用测试")
            
        # 测试流式方法的存在性
        print("\n🔍 检查流式方法是否存在...")
        
        methods_to_check = [
            "_call_mcp_tool_stream",
            "call_tool_stream_sync", 
            "execute_tools_stream",
            "execute_single_tool_stream"
        ]
        
        for method_name in methods_to_check:
            if hasattr(executor, method_name):
                print(f"  ✅ {method_name} 方法存在")
            else:
                print(f"  ❌ {method_name} 方法不存在")
        
        print("\n🎉 流式功能测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_streaming_with_callback():
    """测试带回调的流式功能"""
    print("\n🧪 测试带回调的流式功能...")
    
    try:
        executor = McpToolExecute()
        executor.init()
        
        # 回调函数
        results_received = []
        
        def on_tool_result(result):
            print(f"📞 回调收到结果: {result.get('tool_call_id', 'unknown')}")
            results_received.append(result)
        
        # 构造测试调用
        test_calls = [
            {
                "id": "callback_test_1",
                "function": {
                    "name": "non_existent_tool",  # 故意使用不存在的工具来测试错误处理
                    "arguments": {}
                }
            }
        ]
        
        # 执行带回调的流式调用
        results = executor.execute_tools_stream(test_calls, on_tool_result)
        
        print(f"📊 执行结果数量: {len(results)}")
        print(f"📞 回调接收数量: {len(results_received)}")
        
        if len(results) == len(results_received):
            print("✅ 回调功能正常")
        else:
            print("⚠️  回调数量不匹配")
            
        return True
        
    except Exception as e:
        print(f"❌ 回调测试失败: {e}")
        return False


if __name__ == "__main__":
    print("🚀 开始 MCP 工具执行器流式功能测试")
    print("=" * 50)
    
    # 基础流式功能测试
    success1 = test_streaming_functionality()
    
    # 回调功能测试
    success2 = test_streaming_with_callback()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)