#!/usr/bin/env python3
"""
简单的 MCP 服务器用于测试 McpToolExecute 功能
"""
import sys
from pathlib import Path

# 添加 mcp_framework 路径
mcp_framework_path = Path(__file__).parent / "mcp_framework"
if mcp_framework_path.exists():
    sys.path.insert(0, str(mcp_framework_path))

try:
    from mcp_framework import EnhancedMCPServer, simple_main
    from mcp_framework.core.decorators import R, O
    from typing_extensions import Annotated
except ImportError:
    print("❌ 无法导入 mcp_framework，请确保已安装")
    print("💡 可以使用以下命令安装:")
    print("   pip install mcp-framework")
    sys.exit(1)

# 创建服务器实例
server = EnhancedMCPServer(
    name="test-mcp-server",
    version="1.0.0",
    description="用于测试 McpToolExecute 的简单 MCP 服务器"
)

@server.tool("计算器")
async def calculator(
    operation: Annotated[str, R("运算类型：add, sub, mul, div")],
    a: Annotated[float, R("第一个数字")],
    b: Annotated[float, R("第二个数字")]
):
    """执行基本数学运算"""
    try:
        if operation == "add":
            result = a + b
        elif operation == "sub":
            result = a - b
        elif operation == "mul":
            result = a * b
        elif operation == "div":
            if b == 0:
                return {"error": "除数不能为零"}
            result = a / b
        else:
            return {"error": f"不支持的运算类型: {operation}"}
        
        return {
            "operation": operation,
            "operands": [a, b],
            "result": result,
            "expression": f"{a} {operation} {b} = {result}"
        }
    except Exception as e:
        return {"error": f"计算错误: {str(e)}"}

@server.tool("问候")
async def greet(
    name: Annotated[str, R("姓名")],
    language: Annotated[str, O("语言", "zh")] = "zh"
):
    """向用户问候"""
    greetings = {
        "zh": f"你好，{name}！",
        "en": f"Hello, {name}!",
        "es": f"¡Hola, {name}!",
        "fr": f"Bonjour, {name}!"
    }
    
    greeting = greetings.get(language, greetings["zh"])
    
    return {
        "greeting": greeting,
        "name": name,
        "language": language,
        "timestamp": "2024-01-01T00:00:00Z"
    }

@server.tool("获取服务器信息")
async def get_server_info():
    """获取服务器基本信息"""
    return {
        "name": server.name,
        "version": server.version,
        "description": server.description,
        "tools_count": len(server._tools),
        "available_tools": list(server._tools.keys())
    }

@server.tool("文本处理")
async def text_processor(
    text: Annotated[str, R("要处理的文本")],
    operation: Annotated[str, R("操作类型：upper, lower, reverse, length")]
):
    """处理文本"""
    try:
        if operation == "upper":
            result = text.upper()
        elif operation == "lower":
            result = text.lower()
        elif operation == "reverse":
            result = text[::-1]
        elif operation == "length":
            result = len(text)
        else:
            return {"error": f"不支持的操作: {operation}"}
        
        return {
            "original": text,
            "operation": operation,
            "result": result
        }
    except Exception as e:
        return {"error": f"文本处理错误: {str(e)}"}

if __name__ == "__main__":
    print("🚀 启动测试 MCP 服务器...")
    print("📋 可用工具:")
    for tool_name in server._tools.keys():
        print(f"   - {tool_name}")
    print("\n💡 使用方法:")
    print("   python test_mcp_server.py http 8080")
    print("   python test_mcp_server.py stdio")
    print()
    
    # 使用简化启动器
    simple_main(server, "TestMCPServer")