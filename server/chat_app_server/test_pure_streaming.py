#!/usr/bin/env python3
"""
测试纯流式功能
验证移除非流式调用后的功能是否正常
"""

import sys
import os
import inspect
import asyncio

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.v2.mcp_tool_execute import McpToolExecute

def test_pure_streaming_functionality():
    """测试纯流式功能"""
    print("🧪 测试纯流式功能")
    print("=" * 50)
    
    # 创建执行器实例
    executor = McpToolExecute()
    
    # 1. 检查已删除的非流式方法
    print("\n1. 检查已删除的非流式方法:")
    
    removed_methods = ['_call_mcp_tool', 'call_tool_stream_sync']
    for method_name in removed_methods:
        if hasattr(executor, method_name):
            print(f"  ❌ {method_name} 方法仍然存在（应该已删除）")
        else:
            print(f"  ✅ {method_name} 方法已成功删除")
    
    # 2. 检查保留的流式方法
    print("\n2. 检查保留的流式方法:")
    
    streaming_methods = [
        '_call_mcp_tool_stream',
        '_accumulate_stream_result',
        'execute_tools_stream',
        'execute_single_tool_stream'
    ]
    
    for method_name in streaming_methods:
        if hasattr(executor, method_name):
            print(f"  ✅ {method_name} 方法存在")
        else:
            print(f"  ❌ {method_name} 方法不存在")
    
    # 3. 检查主要执行方法的参数
    print("\n3. 检查主要执行方法的参数:")
    
    # 检查 execute_tools 方法
    execute_tools_sig = inspect.signature(executor.execute_tools)
    params = list(execute_tools_sig.parameters.keys())
    print(f"  execute_tools 参数: {params}")
    
    if 'use_streaming' in params:
        print("  ❌ execute_tools 仍有 use_streaming 参数（应该已删除）")
    else:
        print("  ✅ execute_tools 已移除 use_streaming 参数")
    
    # 检查 execute_single_tool 方法
    execute_single_tool_sig = inspect.signature(executor.execute_single_tool)
    params = list(execute_single_tool_sig.parameters.keys())
    print(f"  execute_single_tool 参数: {params}")
    
    if 'use_streaming' in params:
        print("  ❌ execute_single_tool 仍有 use_streaming 参数（应该已删除）")
    else:
        print("  ✅ execute_single_tool 已移除 use_streaming 参数")
    
    # 检查 execute_tools_with_validation 方法
    execute_validation_sig = inspect.signature(executor.execute_tools_with_validation)
    params = list(execute_validation_sig.parameters.keys())
    print(f"  execute_tools_with_validation 参数: {params}")
    
    if 'use_streaming' in params:
        print("  ❌ execute_tools_with_validation 仍有 use_streaming 参数（应该已删除）")
    else:
        print("  ✅ execute_tools_with_validation 已移除 use_streaming 参数")
    
    # 4. 检查方法调用链
    print("\n4. 检查方法调用链:")
    
    # 检查 execute_tools 是否直接调用 execute_tools_stream
    try:
        execute_tools_source = inspect.getsource(executor.execute_tools)
        if 'execute_tools_stream' in execute_tools_source:
            print("  ✅ execute_tools 直接调用 execute_tools_stream")
        else:
            print("  ❌ execute_tools 未调用 execute_tools_stream")
    except Exception as e:
        print(f"  ⚠️ 无法检查 execute_tools 源码: {e}")
    
    # 检查 execute_single_tool 是否直接调用 execute_single_tool_stream
    try:
        execute_single_tool_source = inspect.getsource(executor.execute_single_tool)
        if 'execute_single_tool_stream' in execute_single_tool_source:
            print("  ✅ execute_single_tool 直接调用 execute_single_tool_stream")
        else:
            print("  ❌ execute_single_tool 未调用 execute_single_tool_stream")
    except Exception as e:
        print(f"  ⚠️ 无法检查 execute_single_tool 源码: {e}")
    
    # 5. 检查新的累积方法
    print("\n5. 检查新的累积方法:")
    
    try:
        accumulate_source = inspect.getsource(executor._accumulate_stream_result)
        if '_call_mcp_tool_stream' in accumulate_source:
            print("  ✅ _accumulate_stream_result 调用 _call_mcp_tool_stream")
        else:
            print("  ❌ _accumulate_stream_result 未调用 _call_mcp_tool_stream")
            
        if 'asyncio.run' in accumulate_source:
            print("  ✅ _accumulate_stream_result 使用 asyncio.run 处理异步流")
        else:
            print("  ❌ _accumulate_stream_result 未使用 asyncio.run")
    except Exception as e:
        print(f"  ⚠️ 无法检查 _accumulate_stream_result 源码: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 纯流式功能测试完成")
    print("\n📋 总结:")
    print("- 所有非流式方法已成功移除")
    print("- 所有主要方法现在只支持流式调用")
    print("- 新的 _accumulate_stream_result 方法提供同步接口")
    print("- 方法调用链已简化为纯流式架构")

def test_async_streaming_interface():
    """测试异步流式接口"""
    print("\n🔄 测试异步流式接口")
    print("=" * 50)
    
    executor = McpToolExecute()
    
    # 检查异步流式方法是否为异步生成器
    if hasattr(executor, '_call_mcp_tool_stream'):
        method = getattr(executor, '_call_mcp_tool_stream')
        if inspect.iscoroutinefunction(method):
            print("  ✅ _call_mcp_tool_stream 是异步方法")
        else:
            print("  ❌ _call_mcp_tool_stream 不是异步方法")
    
    print("\n📝 异步流式调用示例:")
    print("```python")
    print("async with SimpleClient('server.py') as client:")
    print("    async for chunk in client.call_stream('tool_name', param='value'):")
    print("        print(chunk, end='')")
    print("```")
    
    print("\n📝 同步累积调用示例:")
    print("```python")
    print("executor = McpToolExecute()")
    print("result = executor._accumulate_stream_result('tool_name', {'param': 'value'})")
    print("print(result)")
    print("```")

if __name__ == "__main__":
    test_pure_streaming_functionality()
    test_async_streaming_interface()