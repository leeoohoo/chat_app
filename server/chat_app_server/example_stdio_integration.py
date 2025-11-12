#!/usr/bin/env python3
"""
stdio Go 工具集成示例
展示如何在 McpToolExecute 中集成 stdio 协议的 go 工具
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.mcp_tool_execute import McpToolExecute

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_1_basic_stdio_integration():
    """示例1: 基本的 stdio 工具集成"""
    print("\n" + "="*60)
    print("📦 示例1: 基本的 stdio 工具集成")
    print("="*60)
    
    # 配置 stdio MCP 服务器
    stdio_mcp_servers = {
        "expert_stream": {
            "name": "expert_stream",
            "command": "./dist/expert-stream-server",  # go 工具的可执行文件路径
            "alias": "expert_instance_1"
        }
    }
    
    # 创建执行器
    async with McpToolExecute(
        mcp_servers={},  # 没有 HTTP 服务器
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    ) as executor:
        # 获取工具列表
        tools = executor.get_tools()
        print(f"\n✅ 成功获取 {len(tools)} 个工具:")
        for tool in tools:
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description']
            print(f"  - {tool_name}: {tool_desc}")
        
        # 调用工具（非流式）
        if tools:
            tool_name = tools[0]['function']['name']
            print(f"\n🔧 调用工具: {tool_name}")
            
            result = await executor.execute(
                tool_name=tool_name,
                arguments={"question": "测试问题：你好！"}
            )
            print(f"✅ 结果: {result[:200]}...")


async def example_2_multiple_go_tools():
    """示例2: 集成多个 go 工具"""
    print("\n" + "="*60)
    print("📦 示例2: 集成多个 go 工具")
    print("="*60)
    
    # 配置多个 stdio MCP 服务器
    stdio_mcp_servers = {
        "expert_stream": {
            "name": "expert_stream",
            "command": "./dist/expert-stream-server",
            "alias": "expert_1"
        },
        "file_reader": {
            "name": "file_reader",
            "command": "./dist/file-reader-server",
            "alias": "file_reader_1"
        }
    }
    
    async with McpToolExecute(
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    ) as executor:
        tools = executor.get_tools()
        print(f"\n✅ 成功获取 {len(tools)} 个工具")
        
        # 按服务器分组显示
        expert_tools = [t for t in tools if t['function']['name'].startswith('expert_stream_')]
        file_reader_tools = [t for t in tools if t['function']['name'].startswith('file_reader_')]
        
        print(f"\n📚 Expert Stream 工具 ({len(expert_tools)} 个):")
        for tool in expert_tools:
            print(f"  - {tool['function']['name']}")
        
        print(f"\n📁 File Reader 工具 ({len(file_reader_tools)} 个):")
        for tool in file_reader_tools:
            print(f"  - {tool['function']['name']}")


async def example_3_streaming_call():
    """示例3: 流式调用 go 工具"""
    print("\n" + "="*60)
    print("📦 示例3: 流式调用 go 工具")
    print("="*60)
    
    stdio_mcp_servers = {
        "expert_stream": {
            "name": "expert_stream",
            "command": "./dist/expert-stream-server",
            "alias": "expert_stream_1"
        }
    }
    
    async with McpToolExecute(
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    ) as executor:
        tools = executor.get_tools()
        
        if tools:
            tool_name = tools[0]['function']['name']
            print(f"\n🔧 流式调用工具: {tool_name}")
            print("📡 接收流式响应:")
            print("-" * 60)
            
            chunk_count = 0
            async for chunk in executor.execute_stream_generator(
                tool_name=tool_name,
                arguments={"question": "请用100字介绍一下 Python"}
            ):
                chunk_count += 1
                print(chunk, end='', flush=True)
            
            print("\n" + "-" * 60)
            print(f"✅ 流式调用完成，共收到 {chunk_count} 个数据块")


async def example_4_http_and_stdio_mixed():
    """示例4: 混合使用 HTTP 和 stdio 协议"""
    print("\n" + "="*60)
    print("📦 示例4: 混合使用 HTTP 和 stdio 协议")
    print("="*60)
    
    # HTTP MCP 服务器
    http_mcp_servers = {
        "http_server": {
            "name": "http_server",
            "url": "http://localhost:8080/mcp"
        }
    }
    
    # stdio MCP 服务器
    stdio_mcp_servers = {
        "expert_stream": {
            "name": "expert_stream",
            "command": "./dist/expert-stream-server",
            "alias": "expert_1"
        },
        "file_reader": {
            "name": "file_reader",
            "command": "./dist/file-reader-server",
            "alias": "file_reader_1"
        }
    }
    
    async with McpToolExecute(
        mcp_servers=http_mcp_servers,
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    ) as executor:
        tools = executor.get_tools()
        
        # 按协议分组
        http_tools = []
        stdio_tools = []
        
        for tool in tools:
            tool_name = tool['function']['name']
            tool_info = executor.find_tool_info(tool_name)
            if tool_info:
                protocol = tool_info.get('protocol', 'unknown')
                if protocol == 'http':
                    http_tools.append(tool)
                elif protocol == 'stdio':
                    stdio_tools.append(tool)
        
        print(f"\n📊 工具统计:")
        print(f"  HTTP 协议工具: {len(http_tools)} 个")
        print(f"  stdio 协议工具: {len(stdio_tools)} 个")
        print(f"  总计: {len(tools)} 个")


async def example_5_different_aliases():
    """示例5: 使用不同的 alias 运行同一个工具的多个实例"""
    print("\n" + "="*60)
    print("📦 示例5: 多实例配置（不同 alias）")
    print("="*60)
    
    # 同一个 go 工具，使用不同的 alias（不同的配置）
    stdio_mcp_servers = {
        "expert_instance_1": {
            "name": "expert_instance_1",
            "command": "./dist/expert-stream-server",
            "alias": "test_no_config"  # 配置 1
        },
        "expert_instance_2": {
            "name": "expert_instance_2",
            "command": "./dist/expert-stream-server",
            "alias": "test_with_config"  # 配置 2
        }
    }
    
    async with McpToolExecute(
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    ) as executor:
        tools = executor.get_tools()
        
        print(f"\n✅ 成功获取 {len(tools)} 个工具（来自 2 个实例）")
        
        # 显示每个实例的工具
        instance1_tools = [t for t in tools if t['function']['name'].startswith('expert_instance_1_')]
        instance2_tools = [t for t in tools if t['function']['name'].startswith('expert_instance_2_')]
        
        print(f"\n📦 实例 1 (test_no_config): {len(instance1_tools)} 个工具")
        for tool in instance1_tools:
            print(f"  - {tool['function']['name']}")
        
        print(f"\n📦 实例 2 (test_with_config): {len(instance2_tools)} 个工具")
        for tool in instance2_tools:
            print(f"  - {tool['function']['name']}")


async def example_6_client_caching():
    """示例6: 客户端缓存机制"""
    print("\n" + "="*60)
    print("📦 示例6: 客户端缓存机制")
    print("="*60)
    
    stdio_mcp_servers = {
        "expert_stream": {
            "name": "expert_stream",
            "command": "./dist/expert-stream-server",
            "alias": "expert_1"
        }
    }
    
    async with McpToolExecute(
        stdio_mcp_servers=stdio_mcp_servers,
        config_dir="/Users/lilei/project/config/test_mcp_server_config"
    ) as executor:
        tools = executor.get_tools()
        
        if tools:
            tool_name = tools[0]['function']['name']
            
            print(f"\n🔧 第一次调用工具（创建客户端）")
            result1 = await executor.execute(
                tool_name=tool_name,
                arguments={"question": "第一次调用"}
            )
            print(f"✅ 第一次调用完成")
            
            print(f"\n🔧 第二次调用工具（复用缓存的客户端）")
            result2 = await executor.execute(
                tool_name=tool_name,
                arguments={"question": "第二次调用"}
            )
            print(f"✅ 第二次调用完成")
            
            print(f"\n💾 客户端缓存状态:")
            print(f"  缓存的客户端数量: {len(executor._stdio_clients)}")


async def main():
    """运行所有示例"""
    print("\n🚀 stdio Go 工具集成示例集")
    print("="*60)
    
    examples = [
        # example_1_basic_stdio_integration,      # 示例1: 基本集成
        # example_2_multiple_go_tools,            # 示例2: 多个工具
        # example_3_streaming_call,               # 示例3: 流式调用
        # example_4_http_and_stdio_mixed,         # 示例4: 混合协议
        example_5_different_aliases,            # 示例5: 多实例
        # example_6_client_caching,               # 示例6: 客户端缓存
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            logger.error(f"❌ 示例执行失败: {e}", exc_info=True)
    
    print("\n" + "="*60)
    print("✅ 所有示例执行完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
