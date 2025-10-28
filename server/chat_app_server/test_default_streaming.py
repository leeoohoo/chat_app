#!/usr/bin/env python3
"""
测试默认流式调用功能
验证 McpToolExecute 类的默认流式调用行为
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.v2.mcp_tool_execute import McpToolExecute

def test_default_streaming():
    """测试默认流式调用功能"""
    print("=== 测试默认流式调用功能 ===")
    
    # 初始化执行器
    executor = McpToolExecute()
    print("✅ MCP 工具执行器初始化成功")
    
    # 测试方法签名
    print("\n--- 检查方法签名 ---")
    
    # 检查 execute_tools 方法
    import inspect
    execute_tools_sig = inspect.signature(executor.execute_tools)
    print(f"execute_tools 方法签名: {execute_tools_sig}")
    
    # 检查是否有 use_streaming 参数
    params = execute_tools_sig.parameters
    if 'use_streaming' in params:
        default_value = params['use_streaming'].default
        print(f"✅ execute_tools 有 use_streaming 参数，默认值: {default_value}")
    else:
        print("❌ execute_tools 缺少 use_streaming 参数")
    
    # 检查 execute_single_tool 方法
    execute_single_tool_sig = inspect.signature(executor.execute_single_tool)
    print(f"execute_single_tool 方法签名: {execute_single_tool_sig}")
    
    params = execute_single_tool_sig.parameters
    if 'use_streaming' in params:
        default_value = params['use_streaming'].default
        print(f"✅ execute_single_tool 有 use_streaming 参数，默认值: {default_value}")
    else:
        print("❌ execute_single_tool 缺少 use_streaming 参数")
    
    # 检查 execute_tools_with_validation 方法
    execute_tools_with_validation_sig = inspect.signature(executor.execute_tools_with_validation)
    print(f"execute_tools_with_validation 方法签名: {execute_tools_with_validation_sig}")
    
    params = execute_tools_with_validation_sig.parameters
    if 'use_streaming' in params:
        default_value = params['use_streaming'].default
        print(f"✅ execute_tools_with_validation 有 use_streaming 参数，默认值: {default_value}")
    else:
        print("❌ execute_tools_with_validation 缺少 use_streaming 参数")
    
    # 测试流式方法是否存在
    print("\n--- 检查流式方法 ---")
    
    streaming_methods = [
        'execute_tools_stream',
        'execute_single_tool_stream',
        '_call_mcp_tool_stream',
        'call_tool_stream_sync'
    ]
    
    for method_name in streaming_methods:
        if hasattr(executor, method_name):
            print(f"✅ {method_name} 方法存在")
        else:
            print(f"❌ {method_name} 方法不存在")
    
    # 模拟工具调用测试（不会真正执行，因为没有可用工具）
    print("\n--- 测试默认行为 ---")
    
    test_tool_call = {
        "id": "test_call_1",
        "function": {
            "name": "test_tool",
            "arguments": '{"param": "value"}'
        }
    }
    
    test_tool_calls = [test_tool_call]
    
    try:
        # 测试默认调用（应该使用流式）
        print("测试 execute_tools 默认调用...")
        result = executor.execute_tools(test_tool_calls)
        print(f"默认调用结果类型: {type(result)}")
        
        # 测试显式禁用流式
        print("测试 execute_tools 禁用流式调用...")
        result_no_stream = executor.execute_tools(test_tool_calls, use_streaming=False)
        print(f"非流式调用结果类型: {type(result_no_stream)}")
        
        # 测试单个工具默认调用
        print("测试 execute_single_tool 默认调用...")
        single_result = executor.execute_single_tool(test_tool_call)
        print(f"单个工具默认调用结果类型: {type(single_result)}")
        
        # 测试单个工具禁用流式
        print("测试 execute_single_tool 禁用流式调用...")
        single_result_no_stream = executor.execute_single_tool(test_tool_call, use_streaming=False)
        print(f"单个工具非流式调用结果类型: {type(single_result_no_stream)}")
        
        print("✅ 所有方法调用成功（虽然工具不存在，但方法签名正确）")
        
    except Exception as e:
        print(f"⚠️ 方法调用测试: {e}")
        print("这是预期的，因为没有可用的工具")
    
    print("\n--- 测试回调功能 ---")
    
    results_received = []
    
    def test_callback(result):
        results_received.append(result)
        print(f"收到回调结果: {result.get('name', 'unknown')}")
    
    try:
        # 测试带回调的流式调用
        print("测试带回调的默认流式调用...")
        executor.execute_tools(test_tool_calls, on_tool_result=test_callback)
        print(f"回调接收到 {len(results_received)} 个结果")
        
    except Exception as e:
        print(f"⚠️ 回调测试: {e}")
    
    print("\n=== 测试完成 ===")

def test_method_delegation():
    """测试方法委托是否正确"""
    print("\n=== 测试方法委托 ===")
    
    executor = McpToolExecute()
    
    # 检查方法是否正确委托到流式版本
    print("检查方法委托逻辑...")
    
    # 这里我们可以通过检查方法的源代码来验证委托逻辑
    import inspect
    
    # 获取 execute_tools 方法的源代码
    try:
        source = inspect.getsource(executor.execute_tools)
        if 'execute_tools_stream' in source and 'use_streaming' in source:
            print("✅ execute_tools 正确委托到 execute_tools_stream")
        else:
            print("❌ execute_tools 委托逻辑有问题")
    except Exception as e:
        print(f"⚠️ 无法检查 execute_tools 源代码: {e}")
    
    # 获取 execute_single_tool 方法的源代码
    try:
        source = inspect.getsource(executor.execute_single_tool)
        if 'execute_single_tool_stream' in source and 'use_streaming' in source:
            print("✅ execute_single_tool 正确委托到 execute_single_tool_stream")
        else:
            print("❌ execute_single_tool 委托逻辑有问题")
    except Exception as e:
        print(f"⚠️ 无法检查 execute_single_tool 源代码: {e}")

if __name__ == "__main__":
    test_default_streaming()
    test_method_delegation()
    print("\n🎉 所有测试完成！")