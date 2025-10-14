#!/usr/bin/env python3
"""
测试分离式配置初始化功能
验证不同MCP服务器类型的配置初始化和管理功能
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from app.mcp_manager.mcp_manager import McpManager
from app.mcp_manager.configs import ConfigInitializerFactory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_config_factory():
    """测试配置工厂基本功能"""
    print("\n" + "="*60)
    print("🧪 测试配置工厂基本功能")
    print("="*60)
    
    # 使用临时配置目录
    test_config_dir = current_dir / "test_configs"
    test_config_dir.mkdir(exist_ok=True)
    
    try:
        # 初始化配置工厂
        factory = ConfigInitializerFactory(str(test_config_dir))
        
        # 测试支持的服务器类型
        supported_servers = factory.get_supported_servers()
        print(f"📋 支持的服务器类型: {list(supported_servers.keys())}")
        
        # 测试获取初始化器
        for server_type in supported_servers.keys():
            initializer = factory.get_initializer(server_type)
            if initializer:
                print(f"✅ {server_type} 初始化器创建成功")
                
                # 测试获取配置模板
                templates = initializer.get_config_templates()
                print(f"   📝 可用模板: {list(templates.keys())}")
            else:
                print(f"❌ {server_type} 初始化器创建失败")
        
        # 测试工厂状态
        status = factory.get_factory_status()
        print(f"🏭 工厂状态: {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置工厂测试失败: {e}")
        return False
    finally:
        # 清理测试目录
        import shutil
        if test_config_dir.exists():
            shutil.rmtree(test_config_dir)


def test_expert_stream_config():
    """测试Expert Stream Server配置初始化"""
    print("\n" + "="*60)
    print("🧪 测试Expert Stream Server配置初始化")
    print("="*60)
    
    # 使用临时配置目录
    test_config_dir = current_dir / "test_expert_configs"
    test_config_dir.mkdir(exist_ok=True)
    
    try:
        from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer
        
        initializer = ExpertStreamConfigInitializer(str(test_config_dir))
        
        # 测试不同配置模板
        templates = ["default", "development", "production", "code_review"]
        test_executable = "/fake/path/to/expert-stream-server"
        
        for template in templates:
            alias = f"expert_test_{template}"
            print(f"\n🔧 测试 {template} 模板...")
            
            # 初始化配置
            success = initializer.initialize_config(
                alias=alias,
                executable_path=test_executable,
                config_template=template,
                custom_config={
                    "api_key": f"test_key_{template}",
                    "model_name": "gpt-4"
                }
            )
            
            if success:
                print(f"✅ {template} 模板初始化成功")
                
                # 验证配置
                if initializer.validate_config(alias):
                    print(f"✅ {template} 配置验证通过")
                else:
                    print(f"❌ {template} 配置验证失败")
                
                # 获取配置摘要
                summary = initializer.get_config_summary(alias)
                if summary:
                    print(f"📋 配置摘要: {summary['alias']} - {summary['server_type']}")
                    print(f"   🔑 API密钥: {summary.get('api_key_set', 'N/A')}")
                    print(f"   🤖 模型: {summary.get('model_name', 'N/A')}")
                
                # 测试配置更新
                update_success = initializer.update_config(alias, {
                    "log_level": "DEBUG",
                    "custom_setting": f"updated_{template}"
                })
                
                if update_success:
                    print(f"✅ {template} 配置更新成功")
                else:
                    print(f"❌ {template} 配置更新失败")
                    
            else:
                print(f"❌ {template} 模板初始化失败")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Expert Stream配置测试失败: {e}")
        return False
    finally:
        # 清理测试目录
        import shutil
        if test_config_dir.exists():
            shutil.rmtree(test_config_dir)


def test_file_reader_config():
    """测试File Reader Server配置初始化"""
    print("\n" + "="*60)
    print("🧪 测试File Reader Server配置初始化")
    print("="*60)
    
    # 使用临时配置目录
    test_config_dir = current_dir / "test_file_reader_configs"
    test_config_dir.mkdir(exist_ok=True)
    
    try:
        from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer
        
        initializer = FileReaderConfigInitializer(str(test_config_dir))
        
        # 测试不同配置模板
        templates = ["default", "development", "production", "research"]
        test_executable = "/fake/path/to/file-reader-server"
        test_project_root = str(current_dir.parent)  # 使用当前项目目录
        
        for template in templates:
            alias = f"file_reader_test_{template}"
            print(f"\n🔧 测试 {template} 模板...")
            
            # 初始化配置
            success = initializer.initialize_config(
                alias=alias,
                executable_path=test_executable,
                config_template=template,
                project_root=test_project_root,
                custom_config={
                    "max_file_size": 20 if template == "development" else 10
                }
            )
            
            if success:
                print(f"✅ {template} 模板初始化成功")
                
                # 验证配置
                if initializer.validate_config(alias):
                    print(f"✅ {template} 配置验证通过")
                else:
                    print(f"❌ {template} 配置验证失败")
                
                # 获取配置摘要
                summary = initializer.get_config_summary(alias)
                if summary:
                    print(f"📋 配置摘要: {summary['alias']} - {summary['server_type']}")
                    print(f"   📂 项目根目录: {summary.get('project_root', 'N/A')}")
                    print(f"   📏 最大文件大小: {summary.get('max_file_size', 'N/A')}MB")
                    print(f"   👁️ 隐藏文件: {summary.get('enable_hidden_files', 'N/A')}")
                
                # 测试项目根目录设置
                new_project_root = str(current_dir)
                if initializer.set_project_root(alias, new_project_root):
                    print(f"✅ {template} 项目根目录设置成功")
                    
                    # 验证设置
                    current_root = initializer.get_project_root(alias)
                    if current_root == new_project_root:
                        print(f"✅ {template} 项目根目录验证成功")
                    else:
                        print(f"❌ {template} 项目根目录验证失败")
                else:
                    print(f"❌ {template} 项目根目录设置失败")
                    
            else:
                print(f"❌ {template} 模板初始化失败")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ File Reader配置测试失败: {e}")
        return False
    finally:
        # 清理测试目录
        import shutil
        if test_config_dir.exists():
            shutil.rmtree(test_config_dir)


def test_mcp_manager_integration():
    """测试McpManager与新配置系统的集成"""
    print("\n" + "="*60)
    print("🧪 测试McpManager与新配置系统的集成")
    print("="*60)
    
    # 使用临时配置目录
    test_config_dir = current_dir / "test_mcp_manager_configs"
    test_config_dir.mkdir(exist_ok=True)
    
    try:
        # 初始化McpManager
        manager = McpManager(config_dir=str(test_config_dir))
        
        print(f"🚀 McpManager初始化完成")
        
        # 测试系统信息
        system_info = manager.get_system_info()
        print(f"🖥️ 系统信息: {system_info['os']} ({system_info['arch']})")
        
        # 测试配置工厂状态
        factory_status = manager.get_factory_status()
        print(f"🏭 配置工厂状态: {factory_status}")
        
        # 测试可用配置模板
        for server_type in ["expert-stream-server", "file-reader-server"]:
            templates = manager.get_available_config_templates(server_type)
            if templates:
                print(f"📝 {server_type} 可用模板: {list(templates.keys())}")
            else:
                print(f"❌ 无法获取 {server_type} 的配置模板")
        
        # 模拟初始化配置（使用假的可执行文件路径）
        test_configs = [
            {
                "server_type": "expert-stream-server",
                "template": "development",
                "alias": "expert_dev_test",
                "custom_config": {"api_key": "test_key", "model_name": "gpt-4"}
            },
            {
                "server_type": "file-reader-server", 
                "template": "development",
                "alias": "file_reader_dev_test",
                "custom_config": {"project_root": str(current_dir.parent)}
            }
        ]
        
        for config_info in test_configs:
            print(f"\n🔧 测试 {config_info['server_type']} 配置初始化...")
            
            # 由于没有真实的可执行文件，我们直接使用配置工厂
            success = manager.config_factory.initialize_config(
                server_type=config_info["server_type"],
                alias=config_info["alias"],
                executable_path=f"/fake/path/to/{config_info['server_type']}",
                config_template=config_info["template"],
                custom_config=config_info["custom_config"]
            )
            
            if success:
                print(f"✅ {config_info['server_type']} 配置初始化成功")
                
                # 测试配置摘要
                summary = manager.get_config_summary_by_factory(config_info["alias"])
                if summary:
                    print(f"📋 配置摘要: {summary}")
                
                # 测试配置验证
                if manager.validate_config_by_factory(config_info["alias"]):
                    print(f"✅ {config_info['server_type']} 配置验证通过")
                else:
                    print(f"❌ {config_info['server_type']} 配置验证失败")
                    
                # 测试配置更新
                update_success = manager.update_server_config(
                    config_info["alias"], 
                    {"log_level": "DEBUG", "test_update": True}
                )
                
                if update_success:
                    print(f"✅ {config_info['server_type']} 配置更新成功")
                else:
                    print(f"❌ {config_info['server_type']} 配置更新失败")
                    
            else:
                print(f"❌ {config_info['server_type']} 配置初始化失败")
        
        # 测试按工厂列出所有配置
        all_configs = manager.list_configs_by_factory()
        print(f"\n📋 所有配置 (按服务器类型分组):")
        for server_type, configs in all_configs.items():
            print(f"  {server_type}: {len(configs)} 个配置")
            for alias, config in configs.items():
                print(f"    - {alias}: {config.get('version', 'N/A')}")
        
        # 测试配置复制
        if "expert_dev_test" in [config["alias"] for config in test_configs]:
            copy_success = manager.copy_server_config("expert_dev_test", "expert_dev_copy")
            if copy_success:
                print(f"✅ 配置复制成功: expert_dev_test -> expert_dev_copy")
            else:
                print(f"❌ 配置复制失败")
        
        # 测试清理功能
        cleanup_result = manager.cleanup_configs_by_factory()
        print(f"🧹 配置清理结果: {cleanup_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ McpManager集成测试失败: {e}")
        return False
    finally:
        # 清理测试目录
        import shutil
        if test_config_dir.exists():
            shutil.rmtree(test_config_dir)


def main():
    """主测试函数"""
    print("🚀 开始测试分离式配置初始化功能")
    print("="*80)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("配置工厂基本功能", test_config_factory),
        ("Expert Stream Server配置", test_expert_stream_config),
        ("File Reader Server配置", test_file_reader_config),
        ("McpManager集成测试", test_mcp_manager_integration)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 开始测试: {test_name}")
            result = test_func()
            test_results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
                
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
            test_results.append((test_name, False))
    
    # 输出测试结果摘要
    print("\n" + "="*80)
    print("📊 测试结果摘要")
    print("="*80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！分离式配置初始化功能正常工作。")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)