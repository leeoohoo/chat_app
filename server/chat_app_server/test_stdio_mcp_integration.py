#!/usr/bin/env python3
"""
测试 stdio MCP 服务器集成
验证配置加载和数据转换是否正确
"""
import sys
import os
import json
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.api.chat_api_v2 import load_mcp_configs_sync
from app.services.v2.mcp_tool_execute import McpToolExecute


def test_config_loading():
    """测试配置加载"""
    print("🧪 测试配置加载")
    print("=" * 50)
    
    # 加载配置
    http_servers, stdio_servers = load_mcp_configs_sync()
    
    print(f"✅ HTTP 服务器数量: {len(http_servers)}")
    print(f"✅ stdio 服务器数量: {len(stdio_servers)}")
    
    if stdio_servers:
        print("\n📋 stdio 服务器配置:")
        for name, config in stdio_servers.items():
            print(f"  服务器: {name}")
            print(f"    命令: {config['command']}")
            print(f"    别名: {config['alias']}")
            print(f"    参数: {config.get('args', [])}")
            print(f"    环境: {config.get('env', {})}")
            print()
    
    return http_servers, stdio_servers


def test_mcp_tool_execute_initialization():
    """测试 McpToolExecute 初始化"""
    print("🔧 测试 McpToolExecute 初始化")
    print("=" * 50)
    
    # 加载配置
    http_servers, stdio_servers = load_mcp_configs_sync()
    
    # 转换 HTTP 配置
    mcp_servers = []
    for name, config in http_servers.items():
        mcp_servers.append({
            "name": name,
            "url": config["url"]
        })
    
    # 转换 stdio 配置
    stdio_mcp_servers = []
    for name, config in stdio_servers.items():
        stdio_mcp_servers.append({
            "name": name,
            "command": config["command"],
            "alias": config["alias"],
            "args": config.get("args", []),
            "env": config.get("env", {})
        })
    
    print(f"📊 转换后的配置:")
    print(f"  HTTP 服务器: {len(mcp_servers)}")
    print(f"  stdio 服务器: {len(stdio_mcp_servers)}")
    
    if stdio_mcp_servers:
        print("\n📋 转换后的 stdio 配置:")
        for server in stdio_mcp_servers:
            print(f"  {json.dumps(server, indent=2, ensure_ascii=False)}")
    
    # 设置配置目录
    config_dir = os.path.expanduser("~/.mcp_framework/configs")
    
    # 创建 McpToolExecute 实例
    try:
        mcp_tool_execute = McpToolExecute(
            mcp_servers=mcp_servers,
            stdio_mcp_servers=stdio_mcp_servers,
            config_dir=config_dir
        )
        
        print(f"\n✅ McpToolExecute 实例创建成功")
        print(f"  HTTP 服务器: {len(mcp_tool_execute.mcp_servers)}")
        print(f"  stdio 服务器: {len(mcp_tool_execute.stdio_mcp_servers)}")
        print(f"  配置目录: {mcp_tool_execute.config_dir}")
        
        return mcp_tool_execute
        
    except Exception as e:
        print(f"❌ McpToolExecute 实例创建失败: {e}")
        raise


def test_tool_building():
    """测试工具构建"""
    print("\n🛠️ 测试工具构建")
    print("=" * 50)
    
    # 创建 McpToolExecute 实例
    mcp_tool_execute = test_mcp_tool_execute_initialization()
    
    try:
        # 初始化工具列表
        mcp_tool_execute.init()
        
        print(f"✅ 工具构建完成")
        print(f"  总工具数量: {len(mcp_tool_execute.tools)}")
        print(f"  工具元数据: {len(mcp_tool_execute.tool_metadata)}")
        
        if mcp_tool_execute.tools:
            print(f"\n📋 可用工具:")
            for i, tool in enumerate(mcp_tool_execute.tools[:5], 1):  # 只显示前5个
                print(f"  {i}. {tool['function']['name']}")
                if i >= 5 and len(mcp_tool_execute.tools) > 5:
                    print(f"  ... 还有 {len(mcp_tool_execute.tools) - 5} 个工具")
                    break
        
        if mcp_tool_execute.stdio_clients:
            print(f"\n🔗 stdio 客户端连接:")
            for name, client in mcp_tool_execute.stdio_clients.items():
                print(f"  {name}: {type(client).__name__}")
        
        return mcp_tool_execute
        
    except Exception as e:
        print(f"❌ 工具构建失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """主测试函数"""
    print("🚀 stdio MCP 服务器集成测试")
    print("=" * 60)
    
    try:
        # 测试配置加载
        test_config_loading()
        
        # 测试 McpToolExecute 初始化
        test_mcp_tool_execute_initialization()
        
        # 测试工具构建
        test_tool_building()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        
        print("\n📋 测试总结:")
        print("✅ 配置加载 - 成功")
        print("✅ 数据转换 - 成功")
        print("✅ McpToolExecute 初始化 - 成功")
        print("✅ 工具构建 - 成功")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)