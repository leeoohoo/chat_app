#!/usr/bin/env python3
"""
测试修改后的 build_tools 方法
验证 stdio 服务器的工具列表构建是否正常工作
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.v2.mcp_tool_execute import McpToolExecute


def test_build_tools_with_stdio():
    """测试 stdio 服务器的工具构建"""
    
    # 模拟 stdio 服务器配置
    stdio_servers = [
        {
            "name": "file_reader",
            "command": "python echo_server.py stdio",  # 使用项目中的 echo_server.py
            "alias": "test_file_reader"
        }
    ]
    
    # 创建 McpToolExecute 实例
    executor = McpToolExecute(
        mcp_servers=[],  # 不测试 HTTP 服务器
        stdio_mcp_servers=stdio_servers,
        config_dir=None
    )
    
    print("开始测试 build_tools 方法...")
    
    try:
        # 调用 build_tools 方法
        executor.build_tools()
        
        # 检查结果
        tools = executor.get_available_tools()
        print(f"成功构建了 {len(tools)} 个工具")
        
        # 打印工具详情
        for i, tool in enumerate(tools, 1):
            function_info = tool.get("function", {})
            print(f"\n工具 {i}:")
            print(f"  名称: {function_info.get('name', 'N/A')}")
            print(f"  描述: {function_info.get('description', 'N/A')[:100]}...")
            
            parameters = function_info.get('parameters', {})
            properties = parameters.get('properties', {})
            required = parameters.get('required', [])
            
            print(f"  参数数量: {len(properties)}")
            print(f"  必需参数: {required}")
        
        # 检查工具元数据
        print(f"\n工具元数据数量: {len(executor.tool_metadata)}")
        for tool_name, metadata in executor.tool_metadata.items():
            print(f"  {tool_name}: {metadata['server_type']} 服务器")
        
        print("\n✅ build_tools 方法测试成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ build_tools 方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_object_structure():
    """测试 Tool 对象的结构"""
    print("\n" + "="*50)
    print("测试 Tool 对象结构...")
    
    try:
        from mcp_framework.client.simple import SimpleClient
        
        async def test_tool_structure():
            # 使用 echo_server.py 进行测试
            async with SimpleClient(
                server_script="python echo_server.py stdio",
                alias="test_structure"
            ) as client:
                tools = await client.list_tools()
                
                print(f"获取到 {len(tools)} 个工具对象")
                
                for i, tool in enumerate(tools, 1):
                    print(f"\n工具 {i} 对象结构:")
                    print(f"  类型: {type(tool)}")
                    print(f"  name: {getattr(tool, 'name', 'N/A')}")
                    print(f"  description: {getattr(tool, 'description', 'N/A')[:100]}...")
                    print(f"  input_schema: {type(getattr(tool, 'input_schema', None))}")
                    
                    # 检查 input_schema 的内容
                    input_schema = getattr(tool, 'input_schema', None)
                    if input_schema:
                        print(f"  input_schema 内容: {input_schema}")
                
                return tools
        
        tools = asyncio.run(test_tool_structure())
        print("\n✅ Tool 对象结构测试成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ Tool 对象结构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("开始测试修改后的 build_tools 方法...")
    
    # 测试 Tool 对象结构
    structure_test_passed = test_tool_object_structure()
    
    # 测试 build_tools 方法
    build_test_passed = test_build_tools_with_stdio()
    
    print("\n" + "="*50)
    print("测试总结:")
    print(f"Tool 对象结构测试: {'✅ 通过' if structure_test_passed else '❌ 失败'}")
    print(f"build_tools 方法测试: {'✅ 通过' if build_test_passed else '❌ 失败'}")
    
    if structure_test_passed and build_test_passed:
        print("\n🎉 所有测试都通过了！修改成功。")
        sys.exit(0)
    else:
        print("\n⚠️ 有测试失败，请检查代码。")
        sys.exit(1)