#!/usr/bin/env python3
"""
测试配置集成
验证所有修改后的文件是否正确从配置文件读取 config_dir
"""

import sys
import os
from pathlib import Path

# 添加项目路径到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_reader():
    """测试配置读取工具"""
    print("🧪 测试配置读取工具")
    print("=" * 50)
    
    try:
        from app.utils.config_reader import get_config_dir, get_project_root
        
        project_root = get_project_root()
        config_dir = get_config_dir()
        
        print(f"✅ 项目根目录: {project_root}")
        print(f"✅ 配置目录: {config_dir}")
        
        # 验证配置文件是否存在
        config_file = Path(project_root) / "config.json"
        if config_file.exists():
            print(f"✅ 配置文件存在: {config_file}")
        else:
            print(f"❌ 配置文件不存在: {config_file}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 配置读取工具测试失败: {e}")
        return False

def test_config_factory():
    """测试配置工厂"""
    print("\n🏭 测试配置工厂")
    print("=" * 50)
    
    try:
        from app.mcp_manager.configs.config_factory import ConfigInitializerFactory
        
        # 测试不传入 config_dir 参数
        factory = ConfigInitializerFactory()
        print(f"✅ 配置工厂创建成功，配置目录: {factory.config_dir}")
        
        # 测试传入 None
        factory2 = ConfigInitializerFactory(config_dir=None)
        print(f"✅ 配置工厂创建成功（传入None），配置目录: {factory2.config_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置工厂测试失败: {e}")
        return False

def test_expert_stream_config():
    """测试专家流配置"""
    print("\n🌊 测试专家流配置")
    print("=" * 50)
    
    try:
        from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer
        
        # 测试不传入 config_dir 参数
        config = ExpertStreamConfigInitializer()
        print(f"✅ 专家流配置创建成功，配置目录: {config.config_dir}")
        
        # 测试传入 None
        config2 = ExpertStreamConfigInitializer(config_dir=None)
        print(f"✅ 专家流配置创建成功（传入None），配置目录: {config2.config_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 专家流配置测试失败: {e}")
        return False

def test_file_reader_config():
    """测试文件读取配置"""
    print("\n📖 测试文件读取配置")
    print("=" * 50)
    
    try:
        from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer
        
        # 测试不传入 config_dir 参数
        config = FileReaderConfigInitializer()
        print(f"✅ 文件读取配置创建成功，配置目录: {config.config_dir}")
        
        # 测试传入 None
        config2 = FileReaderConfigInitializer(config_dir=None)
        print(f"✅ 文件读取配置创建成功（传入None），配置目录: {config2.config_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ 文件读取配置测试失败: {e}")
        return False

def test_mcp_tool_execute():
    """测试 MCP 工具执行器"""
    print("\n🔧 测试 MCP 工具执行器")
    print("=" * 50)
    
    try:
        from app.services.v2.mcp_tool_execute import McpToolExecute
        
        # 测试不传入 config_dir 参数
        executor = McpToolExecute()
        print(f"✅ MCP 工具执行器创建成功，配置目录: {executor.config_dir}")
        
        # 测试传入 None
        executor2 = McpToolExecute(config_dir=None)
        print(f"✅ MCP 工具执行器创建成功（传入None），配置目录: {executor2.config_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP 工具执行器测试失败: {e}")
        return False

def test_config_consistency():
    """测试配置一致性"""
    print("\n🔍 测试配置一致性")
    print("=" * 50)
    
    try:
        from app.utils.config_reader import get_config_dir
        from app.mcp_manager.configs.config_factory import ConfigInitializerFactory
        from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer
        from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer
        from app.services.v2.mcp_tool_execute import McpToolExecute
        
        # 获取所有配置目录
        base_config_dir = get_config_dir()
        factory_config_dir = str(ConfigInitializerFactory().config_dir)
        expert_config_dir = str(ExpertStreamConfigInitializer().config_dir)
        file_config_dir = str(FileReaderConfigInitializer().config_dir)
        execute_config_dir = McpToolExecute().config_dir
        
        print(f"基础配置目录: {base_config_dir}")
        print(f"配置工厂目录: {factory_config_dir}")
        print(f"专家流目录: {expert_config_dir}")
        print(f"文件读取目录: {file_config_dir}")
        print(f"工具执行器目录: {execute_config_dir}")
        
        # 检查是否一致
        all_dirs = [base_config_dir, factory_config_dir, expert_config_dir, file_config_dir, execute_config_dir]
        if len(set(all_dirs)) == 1:
            print("✅ 所有配置目录一致")
            return True
        else:
            print("❌ 配置目录不一致")
            return False
            
    except Exception as e:
        print(f"❌ 配置一致性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 配置集成测试")
    print("=" * 60)
    
    tests = [
        test_config_reader,
        test_config_factory,
        test_expert_stream_config,
        test_file_reader_config,
        test_mcp_tool_execute,
        test_config_consistency
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ 测试失败: {test.__name__}")
        except Exception as e:
            print(f"❌ 测试异常: {test.__name__} - {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！配置集成成功！")
        print("\n📋 功能总结:")
        print("✅ 创建了全局配置文件 config.json")
        print("✅ 创建了配置读取工具 config_reader.py")
        print("✅ 修改了 config_factory.py 从配置文件读取 config_dir")
        print("✅ 修改了 expert_stream_config.py 从配置文件读取 config_dir")
        print("✅ 修改了 file_reader_config.py 从配置文件读取 config_dir")
        print("✅ 修改了 mcp_tool_execute.py 从配置文件读取 config_dir")
        print("✅ 所有组件使用统一的配置目录")
        return True
    else:
        print("❌ 部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)