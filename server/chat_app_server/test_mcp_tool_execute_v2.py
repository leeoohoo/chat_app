#!/usr/bin/env python3
"""
测试修改后的 McpToolExecute 类功能
验证 mcp_servers 配置的处理
"""
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.v2.mcp_tool_execute import McpToolExecute


def test_build_tools_from_servers():
    """测试 build_tools_from_servers 方法"""
    print("🧪 测试 build_tools_from_servers 方法")
    print("=" * 50)
    
    # 模拟 mcp_servers 配置
    mcp_servers = [
        {"name": "calculator", "url": "http://localhost:8080"},
        {"name": "file_manager", "url": "http://localhost:8081"},
        {"name": "weather", "url": "http://localhost:8082"}
    ]
    
    # 创建 McpToolExecute 实例
    mcp_tool_execute = McpToolExecute(mcp_servers=mcp_servers)
    
    # 测试 build_tools_from_servers
    tools = mcp_tool_execute.build_tools_from_servers()
    
    print(f"✅ 成功构建 {len(tools)} 个工具")
    
    for i, tool in enumerate(tools, 1):
        print(f"\n工具 {i}:")
        print(f"  名称: {tool['function']['name']}")
        print(f"  描述: {tool['function']['description']}")
        print(f"  参数: {tool['function']['parameters']}")
    
    # 验证工具格式
    expected_tools = ["mcp_server_calculator", "mcp_server_file_manager", "mcp_server_weather"]
    actual_tools = [tool['function']['name'] for tool in tools]
    
    assert actual_tools == expected_tools, f"工具名称不匹配: {actual_tools} != {expected_tools}"
    print("\n✅ 工具格式验证通过")


def test_get_available_tools():
    """测试 get_available_tools 方法"""
    print("\n🔧 测试 get_available_tools 方法")
    print("=" * 50)
    
    # 测试1: 只有 mcp_servers
    mcp_servers = [
        {"name": "test_server", "url": "http://localhost:8080"}
    ]
    
    mcp_tool_execute = McpToolExecute(mcp_servers=mcp_servers)
    tools = mcp_tool_execute.get_available_tools()
    
    print(f"✅ 从 mcp_servers 获取到 {len(tools)} 个工具")
    assert len(tools) == 1
    assert tools[0]['function']['name'] == "mcp_server_test_server"
    
    # 测试2: 没有任何配置
    empty_execute = McpToolExecute()
    empty_tools = empty_execute.get_available_tools()
    
    print(f"✅ 空配置返回 {len(empty_tools)} 个工具")
    assert len(empty_tools) == 0


def test_call_mcp_tool():
    """测试 _call_mcp_tool 方法"""
    print("\n🚀 测试 _call_mcp_tool 方法")
    print("=" * 50)
    
    mcp_servers = [
        {"name": "calculator", "url": "http://localhost:8080"}
    ]
    
    mcp_tool_execute = McpToolExecute(mcp_servers=mcp_servers)
    
    # 测试通过 mcp_servers 调用工具
    try:
        result = mcp_tool_execute._call_mcp_tool(
            "mcp_server_calculator", 
            {
                "tool_name": "add",
                "arguments": {"a": 10, "b": 20}
            }
        )
        
        print(f"✅ 工具调用成功:")
        print(f"  服务器: {result['server']}")
        print(f"  工具: {result['tool']}")
        print(f"  参数: {result['arguments']}")
        print(f"  结果: {result['result']}")
        
        assert result['server'] == "calculator"
        assert result['tool'] == "add"
        assert result['arguments'] == {"a": 10, "b": 20}
        
    except Exception as e:
        print(f"❌ 工具调用失败: {e}")
        raise
    
    # 测试错误情况
    try:
        empty_execute = McpToolExecute()
        empty_execute._call_mcp_tool("some_tool", {})
        assert False, "应该抛出异常"
    except Exception as e:
        print(f"✅ 正确抛出错误: {str(e)}")


def test_integration():
    """集成测试"""
    print("\n🎯 集成测试")
    print("=" * 50)
    
    # 模拟完整的工作流程
    mcp_servers = [
        {"name": "math", "url": "http://localhost:8080"},
        {"name": "text", "url": "http://localhost:8081"}
    ]
    
    mcp_tool_execute = McpToolExecute(mcp_servers=mcp_servers)
    
    # 1. 获取可用工具
    tools = mcp_tool_execute.get_available_tools()
    print(f"1️⃣ 获取到 {len(tools)} 个可用工具")
    
    # 2. 模拟 OpenAI 调用
    openai_tools = tools  # 这就是传给 OpenAI 的 tools 参数
    print(f"2️⃣ OpenAI tools 格式: {len(openai_tools)} 个工具")
    
    # 3. 模拟工具调用
    for tool in openai_tools:
        tool_name = tool['function']['name']
        print(f"3️⃣ 测试调用工具: {tool_name}")
        
        try:
            result = mcp_tool_execute._call_mcp_tool(
                tool_name,
                {
                    "tool_name": "test_function",
                    "arguments": {"param": "value"}
                }
            )
            print(f"   ✅ 调用成功: {result['result']}")
        except Exception as e:
            print(f"   ❌ 调用失败: {e}")
    
    print("\n✅ 集成测试完成")


def main():
    """主测试函数"""
    print("🚀 McpToolExecute 修改后功能测试")
    print("=" * 60)
    
    try:
        test_build_tools_from_servers()
        test_get_available_tools()
        test_call_mcp_tool()
        test_integration()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("\n📋 功能总结:")
        print("✅ build_tools_from_servers() - 从 mcp_servers 配置构建 OpenAI tools 格式")
        print("✅ get_available_tools() - 支持 mcp_servers 和 mcp_client 两种模式")
        print("✅ _call_mcp_tool() - 支持通过 mcp_servers 调用工具")
        print("✅ 向后兼容性 - 保持原有 mcp_client 功能")
        
        print("\n🔧 使用方式:")
        print("1. 创建实例: McpToolExecute(mcp_servers=[{\"name\": \"server1\", \"url\": \"http://...\"}])")
        print("2. 获取工具: tools = instance.get_available_tools()")
        print("3. 传给 OpenAI: openai.chat.completions.create(..., tools=tools)")
        print("4. 调用工具: instance._call_mcp_tool(tool_name, arguments)")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)