#!/usr/bin/env python3
"""
演示如何使用McpManager创建配置文件
"""
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.mcp_manager.mcp_manager import McpManager


def main():
    """演示创建配置文件"""
    print("🚀 McpManager配置文件创建演示")
    print("=" * 50)
    
    # 初始化McpManager，使用当前目录下的mcp_config作为配置目录
    config_dir = "./mcp_config"
    manager = McpManager(config_dir=config_dir)
    
    print(f"📁 配置目录: {config_dir}")
    print()
    
    # 1. 查看可用的服务器类型
    print("1️⃣ 可用的服务器类型:")
    available_servers = manager.get_available_servers()
    for server_type, description in available_servers.items():
        print(f"   - {server_type}: {description}")
    print()
    
    # 2. 查看expert-stream-server的可用模板
    print("2️⃣ expert-stream-server的可用模板:")
    templates = manager.get_available_config_templates("expert-stream-server")
    if templates:
        for template_name, template_desc in templates.items():
            print(f"   - {template_name}: {template_desc}")
    print()
    
    # 3. 创建一个expert-stream-server配置
    print("3️⃣ 创建expert-stream-server配置...")
    success, alias = manager.initialize_server_with_template(
        server_type="expert-stream-server",
        template="development",
        alias="my_expert_assistant"
    )
    
    if success:
        print(f"✅ 成功创建配置: {alias}")
        
        # 查看配置文件路径
        config_path = Path(config_dir) / f"{alias}.json"
        print(f"📄 配置文件位置: {config_path}")
        
        # 显示配置摘要
        summary = manager.get_config_summary_by_factory(alias)
        if summary:
            print(f"📋 配置摘要:")
            print(f"   - 服务器类型: {summary.get('server_type')}")
            print(f"   - 角色: {summary.get('role')}")
            print(f"   - 可执行文件: {summary.get('executable_path')}")
    else:
        print(f"❌ 创建配置失败")
    print()
    
    # 4. 列出所有配置
    print("4️⃣ 当前所有配置:")
    all_configs = manager.list_all_server_configs()
    for alias, config in all_configs.items():
        print(f"   - {alias} ({config.get('server_type')})")
    print()
    
    print("🎉 演示完成！")
    print(f"💡 提示: 配置文件已保存在 {config_dir} 目录中")


if __name__ == "__main__":
    main()