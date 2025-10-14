#!/usr/bin/env python3
"""
SimpleClient 配置管理演示
基于 expert_stream_server_test_dual_instance_config.py 的模式
"""

import asyncio
import sys
import os
from pathlib import Path
from mcp_framework.client.simple import SimpleClient

class SimpleClientConfigDemo:
    def __init__(self):
        # 设置服务器脚本路径
        self.server_script = "/Users/lilei/project/learn/chat_app/server/chat_app_server/mcp_services/expert-stream-server-macos-arm64/expert-stream-server"
        # 设置配置目录
        self.config_dir = "/Users/lilei/project/learn/chat_app/server/chat_app_server/mcp_config"
        
        # 确保配置目录存在
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
    async def demo_create_and_manage_config(self):
        """演示如何使用 SimpleClient 创建和管理配置"""
        print("🚀 SimpleClient 配置管理演示")
        print(f"📁 配置目录: {self.config_dir}")
        print(f"🖥️  服务器脚本: {self.server_script}")
        
        # 定义要创建的配置
        demo_configs = {
            "demo_assistant": {
                "server_name": "ExpertStreamServer",
                "log_level": "INFO",
                "max_connections": 30,
                "timeout": 50,
                # 核心配置参数
                "api_key": "sk-demo-key-for-testing",
                "model_name": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "system_prompt": "你是一个演示用的AI助手，专门用于展示配置管理功能。",
                # MCP服务器配置
                "mcp_servers": "[]",
                "stdio_mcp_servers": "",
                # 数据库配置
                "mongodb_url": "",
                # 历史记录配置
                "history_limit": "15",
                "enable_history": True,
                # 角色和工具配置
                "role": "demo_assistant",
                "tool_description": "🎯 **Demo Assistant** - Configuration Management Demo",
                "parameter_description": "📋 **Demo Parameter**: Test configuration management",
                # 总结配置
                "summary_interval": 4,
                "max_rounds": 20,
                "summary_instruction": "You are a demo configuration analyzer.",
                "summary_request": "Generate demo configuration summary.",
                "summary_length_threshold": 25000,
                # 自定义设置
                "custom_setting": "demo_value_123"
            },
            "production_assistant": {
                "server_name": "ExpertStreamServer",
                "log_level": "WARNING",
                "max_connections": 100,
                "timeout": 120,
                # 核心配置参数
                "api_key": "sk-production-key-placeholder",
                "model_name": "gpt-4-turbo",
                "base_url": "https://api.openai.com/v1",
                "system_prompt": "你是一个生产环境的AI助手，提供专业、准确的服务。",
                # MCP服务器配置
                "mcp_servers": "[]",
                "stdio_mcp_servers": "",
                # 数据库配置
                "mongodb_url": "mongodb://localhost:27017/production_chat",
                # 历史记录配置
                "history_limit": "50",
                "enable_history": True,
                # 角色和工具配置
                "role": "production_assistant",
                "tool_description": "🏭 **Production Assistant** - Enterprise Grade AI Service",
                "parameter_description": "🎯 **Production Parameter**: Enterprise task execution",
                # 总结配置
                "summary_interval": 10,
                "max_rounds": 50,
                "summary_instruction": "You are a professional production environment analyzer.",
                "summary_request": "Generate comprehensive production analysis report.",
                "summary_length_threshold": 50000,
                # 自定义设置
                "custom_setting": "production_value_456"
            }
        }
        
        success_count = 0
        
        for alias, config_data in demo_configs.items():
            print(f"\n📝 创建配置: {alias}")
            
            try:
                # 使用 SimpleClient 创建和管理配置
                async with SimpleClient(
                    self.server_script, 
                    alias=alias, 
                    config_dir=self.config_dir
                ) as client:
                    print(f"   ✅ 成功连接到 SimpleClient '{alias}'")
                    
                    # 获取当前配置
                    current_config = await client.config()
                    print(f"   📋 当前配置项数量: {len(current_config)}")
                    
                    # 批量更新配置
                    print(f"   🔧 批量更新配置...")
                    update_success = await client.update(**config_data)
                    if update_success:
                        print(f"   ✅ 配置批量更新成功")
                    else:
                        print(f"   ⚠️  配置批量更新返回 False")
                    
                    # 设置关键配置项
                    key_configs = [
                        ("custom_setting", config_data["custom_setting"]),
                        ("model_name", config_data["model_name"]),
                        ("role", config_data["role"])
                    ]
                    
                    for key, value in key_configs:
                        set_success = await client.set(key, value)
                        if set_success:
                            print(f"   ✅ 设置 {key} = {value}")
                        else:
                            print(f"   ⚠️  设置 {key} 失败")
                    
                    # 验证配置
                    updated_config = await client.config()
                    print(f"   🔍 更新后配置项数量: {len(updated_config)}")
                    
                    # 检查关键配置项
                    custom_setting = await client.get("custom_setting", "未设置")
                    model_name = await client.get("model_name", "未设置")
                    role = await client.get("role", "未设置")
                    
                    print(f"   📊 配置验证:")
                    print(f"      - custom_setting: {custom_setting}")
                    print(f"      - model_name: {model_name}")
                    print(f"      - role: {role}")
                    
                    if custom_setting == config_data["custom_setting"]:
                        print(f"   ✅ 配置验证成功")
                        success_count += 1
                    else:
                        print(f"   ❌ 配置验证失败")
                        
            except Exception as e:
                print(f"   ❌ 配置 '{alias}' 创建失败: {e}")
        
        print(f"\n📊 总结:")
        print(f"   成功创建配置: {success_count}/{len(demo_configs)}")
        
        return success_count == len(demo_configs)
    
    async def demo_list_config_files(self):
        """演示列出创建的配置文件"""
        print(f"\n📁 配置文件列表 ({self.config_dir}):")
        
        config_path = Path(self.config_dir)
        if config_path.exists():
            config_files = list(config_path.glob("*.json"))
            if config_files:
                for config_file in sorted(config_files):
                    print(f"   📄 {config_file.name}")
                    # 显示文件大小
                    size = config_file.stat().st_size
                    print(f"      大小: {size} bytes")
            else:
                print("   📭 没有找到配置文件")
        else:
            print(f"   ❌ 配置目录不存在: {config_path}")
    
    async def demo_read_existing_config(self):
        """演示读取已存在的配置"""
        print(f"\n🔍 读取已存在的配置...")
        
        # 尝试读取之前创建的配置
        test_aliases = ["demo_assistant", "production_assistant"]
        
        for alias in test_aliases:
            print(f"\n   📖 读取配置: {alias}")
            
            try:
                async with SimpleClient(
                    self.server_script, 
                    alias=alias, 
                    config_dir=self.config_dir
                ) as client:
                    
                    # 获取配置
                    config = await client.config()
                    print(f"      配置项数量: {len(config)}")
                    
                    # 显示关键配置
                    key_items = ["custom_setting", "model_name", "role", "log_level"]
                    for key in key_items:
                        value = await client.get(key, "未设置")
                        print(f"      {key}: {value}")
                        
            except Exception as e:
                print(f"      ❌ 读取配置失败: {e}")

async def main():
    """主函数"""
    demo = SimpleClientConfigDemo()
    
    print("=" * 60)
    print("SimpleClient 配置管理演示")
    print("=" * 60)
    
    try:
        # 1. 创建和管理配置
        success = await demo.demo_create_and_manage_config()
        
        # 2. 列出配置文件
        await demo.demo_list_config_files()
        
        # 3. 读取已存在的配置
        await demo.demo_read_existing_config()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ 演示完成！所有配置创建成功。")
            return 0
        else:
            print("⚠️  演示完成，但部分配置创建失败。")
            return 1
            
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))