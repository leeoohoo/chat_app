#!/usr/bin/env python3
"""
分离式配置初始化系统使用示例
演示如何使用新的配置系统来管理不同类型的MCP服务器
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.mcp_manager.configs import ConfigInitializerFactory
from app.mcp_manager.mcp_manager import McpManager


def example_1_basic_factory_usage():
    """示例1: 基本的配置工厂使用"""
    print("=" * 60)
    print("📚 示例1: 基本的配置工厂使用")
    print("=" * 60)
    
    # 使用临时配置目录
    config_dir = current_dir / "example_configs"
    config_dir.mkdir(exist_ok=True)
    
    try:
        # 初始化配置工厂
        factory = ConfigInitializerFactory(str(config_dir))
        
        # 查看支持的服务器类型
        supported_servers = factory.get_supported_servers()
        print(f"🔧 支持的服务器类型: {list(supported_servers.keys())}")
        
        # 初始化Expert Stream Server配置
        print("\n🤖 初始化Expert Stream Server配置...")
        success = factory.initialize_config(
            server_type="expert-stream-server",
            alias="my_expert_assistant",
            executable_path="/usr/local/bin/expert-stream-server",  # 示例路径
            config_template="development",
            custom_config={
                "api_key": "sk-your-openai-api-key-here",
                "model_name": "gpt-4",
                "system_prompt": "You are a helpful coding assistant specialized in Python.",
                "log_level": "INFO"
            }
        )
        
        if success:
            print("✅ Expert Stream Server配置初始化成功")
            
            # 获取配置摘要
            summary = factory.get_config_summary("expert-stream-server", "my_expert_assistant")
            print(f"📋 配置摘要: {summary}")
        else:
            print("❌ Expert Stream Server配置初始化失败")
        
        # 初始化File Reader Server配置
        print("\n📁 初始化File Reader Server配置...")
        success = factory.initialize_config(
            server_type="file-reader-server",
            alias="my_file_reader",
            executable_path="/usr/local/bin/file-reader-server",  # 示例路径
            config_template="development",
            project_root=str(project_root),
            custom_config={
                "max_file_size": 20,
                "enable_hidden_files": True,
                "log_level": "DEBUG"
            }
        )
        
        if success:
            print("✅ File Reader Server配置初始化成功")
            
            # 获取配置摘要
            summary = factory.get_config_summary("file-reader-server", "my_file_reader")
            print(f"📋 配置摘要: {summary}")
        else:
            print("❌ File Reader Server配置初始化失败")
        
        # 列出所有配置
        print("\n📋 所有配置:")
        all_configs = factory.list_all_configs()
        for server_type, configs in all_configs.items():
            print(f"  {server_type}: {len(configs)} 个配置")
            for alias in configs.keys():
                print(f"    - {alias}")
        
    finally:
        # 清理示例配置目录
        import shutil
        if config_dir.exists():
            shutil.rmtree(config_dir)


def example_2_mcp_manager_integration():
    """示例2: 通过McpManager使用配置系统"""
    print("\n" + "=" * 60)
    print("📚 示例2: 通过McpManager使用配置系统")
    print("=" * 60)
    
    # 使用临时配置目录
    config_dir = current_dir / "example_mcp_configs"
    config_dir.mkdir(exist_ok=True)
    
    try:
        # 初始化McpManager
        manager = McpManager(config_dir=str(config_dir))
        print("🚀 McpManager初始化完成")
        
        # 查看可用的配置模板
        print("\n📝 可用的配置模板:")
        for server_type in ["expert-stream-server", "file-reader-server"]:
            templates = manager.get_available_config_templates(server_type)
            if templates:
                print(f"  {server_type}:")
                for template_name, template_desc in templates.items():
                    print(f"    - {template_name}: {template_desc}")
        
        # 使用模板初始化Expert Stream Server
        print("\n🤖 使用模板初始化Expert Stream Server...")
        success, alias = manager.initialize_server_with_template(
            server_type="expert-stream-server",
            template="code_review",
            alias="expert_code_reviewer",
            api_key="sk-your-api-key-for-code-review",
            model_name="gpt-4",
            system_prompt="You are an expert code reviewer. Focus on code quality, best practices, and potential issues."
        )
        
        if success:
            print("✅ Expert Stream Server (代码审查)配置成功")
        
        # 使用模板初始化File Reader Server
        print("\n📁 使用模板初始化File Reader Server...")
        success, alias = manager.initialize_server_with_template(
            server_type="file-reader-server",
            template="production",
            alias="project_file_reader",
            project_root=str(project_root)
        )
        
        if success:
            print("✅ File Reader Server (生产环境)配置成功")
        
        # 更新配置
        print("\n🔧 更新配置...")
        update_success = manager.update_server_config("expert_code_reviewer", {
            "temperature": 0.3,  # 代码审查需要更严格
            "max_tokens": 2000,
            "enable_history": True
        })
        
        if update_success:
            print("✅ Expert Stream Server配置更新成功")
        
        # 设置File Reader的项目根目录
        print("\n📂 设置File Reader项目根目录...")
        root_success = manager.set_project_root_for_file_reader(
            "project_file_reader", 
            str(current_dir.parent)
        )
        
        if root_success:
            current_root = manager.get_project_root_for_file_reader("project_file_reader")
            print(f"✅ 项目根目录设置成功: {current_root}")
        
        # 获取配置摘要
        print("\n📊 配置摘要:")
        for alias in ["expert_code_reviewer", "project_file_reader"]:
            summary = manager.get_config_summary_by_factory(alias)
            if summary:
                print(f"  {alias}:")
                print(f"    类型: {summary.get('server_type', 'N/A')}")
                print(f"    版本: {summary.get('version', 'N/A')}")
                print(f"    模板: {summary.get('template', 'N/A')}")
        
        # 复制配置
        print("\n📋 复制配置...")
        copy_success = manager.copy_server_config("expert_code_reviewer", "expert_backup")
        if copy_success:
            print("✅ 配置复制成功: expert_code_reviewer -> expert_backup")
        
        # 列出所有配置
        print("\n📋 所有配置 (按服务器类型分组):")
        all_configs = manager.list_configs_by_factory()
        for server_type, configs in all_configs.items():
            print(f"  {server_type}: {len(configs)} 个配置")
            for alias, config in configs.items():
                print(f"    - {alias} (v{config.get('version', 'N/A')})")
        
    finally:
        # 清理示例配置目录
        import shutil
        if config_dir.exists():
            shutil.rmtree(config_dir)


def example_3_advanced_configuration():
    """示例3: 高级配置管理"""
    print("\n" + "=" * 60)
    print("📚 示例3: 高级配置管理")
    print("=" * 60)
    
    # 使用临时配置目录
    config_dir = current_dir / "example_advanced_configs"
    config_dir.mkdir(exist_ok=True)
    
    try:
        # 直接使用专门的配置初始化器
        from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer
        from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer
        
        # 创建配置工厂实例
        factory = ConfigInitializerFactory(str(config_dir))
        
        # Expert Stream配置管理
        print("🤖 Expert Stream高级配置管理...")
        expert_initializer = ExpertStreamConfigInitializer(str(config_dir))
        
        # 创建多个不同用途的配置
        expert_configs = [
            {
                "alias": "expert_dev",
                "template": "development",
                "custom": {
                    "api_key": "sk-dev-key",
                    "model_name": "gpt-3.5-turbo",
                    "log_level": "DEBUG"
                }
            },
            {
                "alias": "expert_prod",
                "template": "production", 
                "custom": {
                    "api_key": "sk-prod-key",
                    "model_name": "gpt-4",
                    "log_level": "INFO"
                }
            },
            {
                "alias": "expert_reviewer",
                "template": "code_review",
                "custom": {
                    "api_key": "sk-review-key",
                    "model_name": "gpt-4",
                    "temperature": 0.2
                }
            }
        ]
        
        for config in expert_configs:
            success = expert_initializer.initialize_config(
                alias=config["alias"],
                executable_path="/usr/local/bin/expert-stream-server",
                config_template=config["template"],
                custom_config=config["custom"]
            )
            
            if success:
                print(f"✅ {config['alias']} 配置创建成功")
                
                # 验证配置
                if expert_initializer.validate_config(config["alias"]):
                    print(f"✅ {config['alias']} 配置验证通过")
                else:
                    print(f"❌ {config['alias']} 配置验证失败")
        
        # File Reader配置管理
        print("\n📁 File Reader高级配置管理...")
        file_initializer = FileReaderConfigInitializer(str(config_dir))
        
        # 创建不同项目的配置
        file_configs = [
            {
                "alias": "reader_main_project",
                "template": "development",
                "project_root": str(project_root),
                "custom": {
                    "max_file_size": 50,
                    "enable_hidden_files": True
                }
            },
            {
                "alias": "reader_research",
                "template": "research",
                "project_root": str(current_dir),
                "custom": {
                    "max_file_size": 100,
                    "file_extensions": [".py", ".md", ".txt", ".json", ".yaml"]
                }
            }
        ]
        
        for config in file_configs:
            success = file_initializer.initialize_config(
                alias=config["alias"],
                executable_path="/usr/local/bin/file-reader-server",
                config_template=config["template"],
                project_root=config["project_root"],
                custom_config=config["custom"]
            )
            
            if success:
                print(f"✅ {config['alias']} 配置创建成功")
                
                # 获取项目根目录
                current_root = file_initializer.get_project_root(config["alias"])
                print(f"   📂 项目根目录: {current_root}")
        
        # 批量操作示例
        print("\n🔧 批量操作示例...")
        
        # 获取所有Expert Stream配置的摘要
        expert_configs_list = factory.list_configs_by_type("expert-stream-server")
        print(f"📊 Expert Stream配置数量: {len(expert_configs_list)}")
        
        for alias in expert_configs_list.keys():
            summary = expert_initializer.get_config_summary(alias)
            if summary:
                print(f"  {alias}: {summary.get('role', 'N/A')} 角色")
        
        # 批量更新配置
        print("\n🔄 批量更新配置...")
        for alias in expert_configs_list.keys():
            update_success = expert_initializer.update_config(alias, {
                "updated_at": "2024-01-01T00:00:00Z",
                "batch_update": True
            })
            if update_success:
                print(f"  ✅ {alias} 更新成功")
        
        # 配置复制和删除示例
        print("\n📋 配置复制和删除示例...")
        
        # 复制配置
        copy_success = factory.copy_config("expert_dev", "expert_dev_backup")
        if copy_success:
            print("✅ 配置复制成功: expert_dev -> expert_dev_backup")
        
        # 删除备份配置
        delete_success = factory.delete_config("expert_dev_backup")
        if delete_success:
            print("✅ 备份配置删除成功")
        
    finally:
        # 清理示例配置目录
        import shutil
        if config_dir.exists():
            shutil.rmtree(config_dir)


def main():
    """主函数 - 运行所有示例"""
    print("🚀 分离式配置初始化系统使用示例")
    print("=" * 80)
    
    try:
        # 运行示例
        example_1_basic_factory_usage()
        example_2_mcp_manager_integration()
        example_3_advanced_configuration()
        
        print("\n" + "=" * 80)
        print("🎉 所有示例运行完成！")
        print("=" * 80)
        
        print("\n💡 关键要点:")
        print("1. 🏭 使用ConfigInitializerFactory作为统一入口")
        print("2. 🔧 每个服务器类型都有专门的配置初始化器")
        print("3. 📝 支持多种配置模板，适应不同使用场景")
        print("4. 🔄 提供完整的配置生命周期管理")
        print("5. 🧪 通过McpManager可以更方便地管理配置")
        
        print("\n📚 更多信息请参考:")
        print("- README.md: 详细文档和API参考")
        print("- test_separate_configs.py: 完整的测试用例")
        
    except Exception as e:
        print(f"❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()