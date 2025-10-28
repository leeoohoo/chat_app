#!/usr/bin/env python3
"""
测试 AI 客户端工具名称显示修复的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tool_result_display():
    """测试工具结果显示格式"""
    
    # 模拟工具执行结果（修复后的格式）
    tool_results = [
        {
            "tool_call_id": "call_1",
            "name": "file_reader_search_files_by_content",  # 使用 name 字段
            "success": True,
            "is_error": False,
            "content": "搜索完成，找到3个文件"
        },
        {
            "tool_call_id": "call_2", 
            "name": "calculator_add",  # 使用 name 字段
            "success": False,
            "is_error": True,
            "content": "计算失败：参数错误"
        }
    ]
    
    print("=== 测试工具结果显示格式 ===")
    
    # 模拟 ai_client.py 中的日志输出逻辑（修复后）
    print("修复后的概览格式:")
    overview = [{'tool_name': tr.get('name', 'unknown'), 'success': tr.get('success', False)} for tr in tool_results]
    print(f"[AI_CLIENT] 工具结果概览: {overview}")
    
    print("\n修复后的详细格式:")
    for i, tr in enumerate(tool_results):
        print(f"[AI_CLIENT] 工具结果 {i+1}: {{'tool_call_id': '{tr.get('tool_call_id', 'unknown')}', 'tool_name': '{tr.get('name', 'unknown')}', 'success': {tr.get('success', False)}, 'content_length': {len(str(tr.get('content', '')))}}}")
    
    print("\n=== 对比修复前的格式 ===")
    print("修复前的概览格式（会显示unknown）:")
    old_overview = [{'tool_name': tr.get('tool_name', 'unknown'), 'success': tr.get('success', False)} for tr in tool_results]
    print(f"[AI_CLIENT] 工具结果概览: {old_overview}")
    
    print("\n修复前的详细格式（会显示unknown）:")
    for i, tr in enumerate(tool_results):
        print(f"[AI_CLIENT] 工具结果 {i+1}: {{'tool_call_id': '{tr.get('tool_call_id', 'unknown')}', 'tool_name': '{tr.get('tool_name', 'unknown')}', 'success': {tr.get('success', False)}, 'content_length': {len(str(tr.get('content', '')))}}}")
    
    print("\n=== 验证修复效果 ===")
    
    # 检查修复后是否正确显示工具名称
    fixed_names = [tr.get('name', 'unknown') for tr in tool_results]
    old_names = [tr.get('tool_name', 'unknown') for tr in tool_results]
    
    print(f"修复后获取的工具名称: {fixed_names}")
    print(f"修复前获取的工具名称: {old_names}")
    
    if all(name != 'unknown' for name in fixed_names):
        print("✅ 修复成功：所有工具名称都正确显示")
    else:
        print("❌ 修复失败：仍有工具名称显示为unknown")
    
    if all(name == 'unknown' for name in old_names):
        print("✅ 确认问题：修复前确实会显示unknown")
    else:
        print("❓ 意外情况：修复前不是所有工具名称都显示unknown")

if __name__ == "__main__":
    print("开始测试 AI 客户端工具名称显示修复...")
    test_tool_result_display()
    print("\n测试完成！")