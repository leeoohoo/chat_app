#!/usr/bin/env python3
"""
测试工具名称和成功状态修复的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.v2.mcp_tool_execute import McpToolExecute

def test_tool_name_and_success_fix():
    """测试工具名称和成功状态的修复"""
    
    # 创建 McpToolExecute 实例
    mcp_executor = McpToolExecute()
    
    # 模拟一个工具调用
    test_tool_call = {
        "id": "test_call_1",
        "type": "function",
        "function": {
            "name": "file_reader_search_files_by_content",
            "arguments": '{"query": "test"}'
        }
    }
    
    print("=== 测试工具执行结果格式 ===")
    print(f"测试工具调用: {test_tool_call}")
    
    try:
        # 测试 execute_single_tool_stream 方法
        result = mcp_executor.execute_single_tool_stream(test_tool_call)
        
        print(f"\n执行结果: {result}")
        
        # 检查必要的字段
        required_fields = ["tool_call_id", "name", "success", "is_error", "content"]
        missing_fields = []
        
        for field in required_fields:
            if field not in result:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 缺少字段: {missing_fields}")
        else:
            print("✅ 所有必要字段都存在")
            
        # 检查字段值
        print(f"\n字段检查:")
        print(f"- tool_call_id: {result.get('tool_call_id')}")
        print(f"- name: {result.get('name')}")
        print(f"- success: {result.get('success')}")
        print(f"- is_error: {result.get('is_error')}")
        print(f"- content 长度: {len(str(result.get('content', '')))}")
        
        # 验证逻辑一致性
        if result.get('success') is not None and result.get('is_error') is not None:
            success = result.get('success')
            is_error = result.get('is_error')
            if success == (not is_error):
                print("✅ success 和 is_error 字段逻辑一致")
            else:
                print(f"❌ success 和 is_error 字段逻辑不一致: success={success}, is_error={is_error}")
        
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()

def test_validation_method():
    """测试带验证的执行方法"""
    
    print("\n=== 测试带验证的执行方法 ===")
    
    mcp_executor = McpToolExecute()
    
    # 测试有效的工具调用
    valid_tool_call = {
        "id": "valid_call_1",
        "type": "function", 
        "function": {
            "name": "file_reader_search_files_by_content",
            "arguments": '{"query": "test"}'
        }
    }
    
    # 测试无效的工具调用（不存在的工具）
    invalid_tool_call = {
        "id": "invalid_call_1",
        "type": "function",
        "function": {
            "name": "non_existent_tool",
            "arguments": '{"param": "value"}'
        }
    }
    
    test_cases = [
        ("有效工具调用", [valid_tool_call]),
        ("无效工具调用", [invalid_tool_call])
    ]
    
    for case_name, tool_calls in test_cases:
        print(f"\n--- {case_name} ---")
        try:
            results = mcp_executor.execute_tools_with_validation(tool_calls)
            
            for i, result in enumerate(results):
                print(f"结果 {i+1}: {result}")
                
                # 检查必要字段
                required_fields = ["tool_call_id", "name", "success", "is_error", "content"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if missing_fields:
                    print(f"  ❌ 缺少字段: {missing_fields}")
                else:
                    print(f"  ✅ 所有必要字段都存在")
                    print(f"  - name: {result.get('name')}")
                    print(f"  - success: {result.get('success')}")
                    print(f"  - is_error: {result.get('is_error')}")
                    
        except Exception as e:
            print(f"❌ {case_name} 执行失败: {e}")

if __name__ == "__main__":
    print("开始测试工具名称和成功状态修复...")
    
    test_tool_name_and_success_fix()
    test_validation_method()
    
    print("\n测试完成！")