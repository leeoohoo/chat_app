#!/usr/bin/env python3
"""
测试McpManager与mcp_tool_execute.py的集成
"""
import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.mcp_manager.mcp_manager import McpManager
from app.services.mcp_tool_execute import McpToolExecute


async def test_integration():
    """测试McpManager与McpToolExecute的集成"""
    print("🧪 开始测试McpManager与McpToolExecute的集成...")
    
    # 创建临时配置目录
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = temp_dir
        print(f"📁 使用临时配置目录: {config_dir}")
        
        # 1. 使用McpManager创建配置
        print("\n1️⃣ 使用McpManager创建配置...")
        manager = McpManager(config_dir=config_dir)
        
        # 创建expert-stream-server配置
        success, expert_alias = manager.initialize_server_with_template(
            server_type="expert-stream-server",
            template="development"
        )
        if success:
            print(f"✅ 创建expert-stream-server配置: {expert_alias}")
        else:
            print(f"❌ 创建expert-stream-server配置失败")
            return False
        
        # 创建file-reader-server配置
        success, file_reader_alias = manager.initialize_server_with_template(
            server_type="file-reader-server", 
            template="basic"
        )
        if success:
            print(f"✅ 创建file-reader-server配置: {file_reader_alias}")
        else:
            print(f"❌ 创建file-reader-server配置失败")
            return False
        
        # 2. 列出所有配置文件
        print("\n2️⃣ 列出配置文件...")
        config_files = list(Path(config_dir).glob("*.json"))
        print(f"📄 找到 {len(config_files)} 个配置文件:")
        for config_file in config_files:
            print(f"   - {config_file.name}")
        
        # 3. 模拟从配置文件加载配置（类似chat_api.py中的load_mcp_configs）
        print("\n3️⃣ 模拟从配置文件加载配置...")
        stdio_servers = {}
        
        for config_file in config_files:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            server_name = config.get('alias', config_file.stem)
            command = config.get('command', '')
            args = config.get('args', [])
            env = config.get('env', {})
            
            stdio_servers[server_name] = {
                'command': command,
                'alias': server_name,
                'args': args,
                'env': env
            }
            print(f"   📋 加载配置: {server_name} -> {command}")
        
        # 4. 使用McpToolExecute初始化工具执行器
        print("\n4️⃣ 使用McpToolExecute初始化工具执行器...")
        mcp_executor = McpToolExecute(
            mcp_servers={},  # HTTP服务器为空
            stdio_mcp_servers=stdio_servers
        )
        
        # 验证config_dir设置
        print(f"🔧 McpToolExecute配置目录: {mcp_executor.config_dir}")
        print(f"🔧 McpManager配置目录: {config_dir}")
        
        # 5. 初始化工具执行器
        print("\n5️⃣ 初始化工具执行器...")
        try:
            await mcp_executor.init()
            tools = mcp_executor.get_tools()
            print(f"✅ 工具执行器初始化成功，加载了 {len(tools)} 个工具")
            
            # 列出可用工具
            if tools:
                print("🔧 可用工具:")
                for tool in tools[:5]:  # 只显示前5个工具
                    print(f"   - {tool.get('function', {}).get('name', 'Unknown')}: {tool.get('function', {}).get('description', 'No description')}")
                if len(tools) > 5:
                    print(f"   ... 还有 {len(tools) - 5} 个工具")
            else:
                print("⚠️  没有加载到任何工具")
                
        except Exception as e:
            print(f"❌ 工具执行器初始化失败: {e}")
            return False
        
        # 6. 测试配置目录兼容性
        print("\n6️⃣ 测试配置目录兼容性...")
        
        # McpToolExecute使用当前工作目录/mcp_config
        mcp_tool_config_dir = os.path.join(os.getcwd(), "mcp_config")
        
        # 如果配置目录不同，复制配置文件
        if config_dir != mcp_tool_config_dir:
            print(f"📂 配置目录不同，需要同步:")
            print(f"   McpManager: {config_dir}")
            print(f"   McpToolExecute: {mcp_tool_config_dir}")
            
            # 创建mcp_config目录
            os.makedirs(mcp_tool_config_dir, exist_ok=True)
            
            # 复制配置文件
            for config_file in config_files:
                dest_file = os.path.join(mcp_tool_config_dir, config_file.name)
                shutil.copy2(config_file, dest_file)
                print(f"   📋 复制: {config_file.name}")
            
            # 重新初始化工具执行器以使用新的配置目录
            print("\n🔄 使用同步后的配置重新初始化...")
            mcp_executor_synced = McpToolExecute(
                mcp_servers={},
                stdio_mcp_servers=stdio_servers
            )
            
            try:
                await mcp_executor_synced.init()
                tools_synced = mcp_executor_synced.get_tools()
                print(f"✅ 同步后工具执行器初始化成功，加载了 {len(tools_synced)} 个工具")
            except Exception as e:
                print(f"❌ 同步后工具执行器初始化失败: {e}")
                return False
        else:
            print("✅ 配置目录一致，无需同步")
        
        print("\n🎉 集成测试完成！")
        return True


async def main():
    """主函数"""
    try:
        success = await test_integration()
        if success:
            print("\n✅ 所有测试通过！McpManager与McpToolExecute集成正常。")
        else:
            print("\n❌ 测试失败！")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())