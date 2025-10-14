"""
MCP管理器测试脚本
用于测试MCP管理器的功能并验证与现有代码的兼容性
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from app.mcp_manager import McpManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_mcp_manager():
    """测试MCP管理器的基本功能"""
    print("🧪 开始测试MCP管理器")
    print("=" * 60)
    
    try:
        # 1. 初始化MCP管理器
        print("1️⃣ 初始化MCP管理器...")
        mcp_manager = McpManager()
        
        # 2. 显示系统信息
        print("\n2️⃣ 系统信息:")
        system_info = mcp_manager.get_system_info()
        for key, value in system_info.items():
            print(f"   {key}: {value}")
        
        # 3. 检查可用服务器
        print("\n3️⃣ 检查可用服务器:")
        available_servers = mcp_manager.get_available_servers()
        if available_servers:
            for server_type, path in available_servers.items():
                print(f"   ✅ {server_type}: {path}")
        else:
            print("   ❌ 未找到可用服务器")
            return False
        
        # 4. 初始化服务器配置
        print("\n4️⃣ 初始化服务器配置:")
        setup_results = mcp_manager.setup_all_available_servers()
        for server_type, alias in setup_results.items():
            print(f"   ✅ {server_type} -> {alias}")
        
        # 5. 列出所有配置
        print("\n5️⃣ 所有配置:")
        all_configs = mcp_manager.list_all_server_configs()
        for alias, config in all_configs.items():
            print(f"   📋 {alias}:")
            print(f"      类型: {config.get('server_type')}")
            print(f"      路径: {config.get('executable_path')}")
            print(f"      平台: {config.get('platform')}")
        
        # 6. 验证配置
        print("\n6️⃣ 验证配置:")
        for alias in all_configs.keys():
            is_valid = mcp_manager.validate_server_config(alias)
            status = "✅ 有效" if is_valid else "❌ 无效"
            print(f"   {alias}: {status}")
        
        # 7. 获取启动命令信息
        print("\n7️⃣ 启动命令信息:")
        for alias in all_configs.keys():
            cmd_info = mcp_manager.get_server_command_info(alias)
            if cmd_info:
                print(f"   📋 {alias}:")
                print(f"      命令: {cmd_info['command']}")
                print(f"      配置目录: {cmd_info['config_dir']}")
        
        # 8. 显示状态摘要
        print("\n8️⃣ 状态摘要:")
        mcp_manager.print_status()
        
        print("\n🎉 MCP管理器测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compatibility_with_mcp_tool_execute():
    """测试与mcp_tool_execute.py的兼容性"""
    print("\n🔗 测试与mcp_tool_execute.py的兼容性")
    print("=" * 60)
    
    try:
        # 检查mcp_tool_execute.py中的config_dir设置
        mcp_tool_execute_path = Path(__file__).parent.parent / "services" / "mcp_tool_execute.py"
        
        if not mcp_tool_execute_path.exists():
            print(f"⚠️ 未找到mcp_tool_execute.py: {mcp_tool_execute_path}")
            return False
            
        # 读取文件内容检查config_dir设置
        with open(mcp_tool_execute_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否包含config_dir设置
        if 'config_dir' in content and 'mcp_config' in content:
            print("✅ 发现mcp_tool_execute.py中的config_dir设置")
            
            # 初始化MCP管理器
            mcp_manager = McpManager()
            
            # 检查配置目录是否一致
            expected_config_dir = str(Path(__file__).parent.parent / "mcp_config")
            actual_config_dir = mcp_manager.config_dir
            
            print(f"📁 期望配置目录: {expected_config_dir}")
            print(f"📁 实际配置目录: {actual_config_dir}")
            
            if Path(expected_config_dir).resolve() == Path(actual_config_dir).resolve():
                print("✅ 配置目录一致，兼容性良好")
                return True
            else:
                print("⚠️ 配置目录不一致，可能存在兼容性问题")
                return False
        else:
            print("⚠️ 未在mcp_tool_execute.py中找到config_dir设置")
            return False
            
    except Exception as e:
        logger.error(f"❌ 兼容性测试失败: {e}")
        return False


def test_server_type_configs():
    """测试不同服务器类型的配置"""
    print("\n🔧 测试不同服务器类型的配置")
    print("=" * 60)
    
    try:
        mcp_manager = McpManager()
        
        # 测试expert-stream-server配置
        print("1️⃣ 测试expert-stream-server配置:")
        expert_config = mcp_manager.get_recommended_config_for_type("expert-stream-server")
        if expert_config:
            print(f"   ✅ 获取到配置: {expert_config['alias']}")
            print(f"   📁 可执行文件: {expert_config['executable_path']}")
        else:
            print("   ❌ 无法获取expert-stream-server配置")
            
        # 测试file-reader-server配置
        print("\n2️⃣ 测试file-reader-server配置:")
        file_reader_config = mcp_manager.get_recommended_config_for_type("file-reader-server")
        if file_reader_config:
            print(f"   ✅ 获取到配置: {file_reader_config['alias']}")
            print(f"   📁 可执行文件: {file_reader_config['executable_path']}")
        else:
            print("   ❌ 无法获取file-reader-server配置")
            
        return expert_config is not None and file_reader_config is not None
        
    except Exception as e:
        logger.error(f"❌ 服务器类型配置测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 MCP管理器完整测试套件")
    print("=" * 80)
    
    test_results = []
    
    # 基本功能测试
    test_results.append(("基本功能测试", test_mcp_manager()))
    
    # 兼容性测试
    test_results.append(("兼容性测试", test_compatibility_with_mcp_tool_execute()))
    
    # 服务器类型配置测试
    test_results.append(("服务器类型配置测试", test_server_type_configs()))
    
    # 显示测试结果
    print("\n📊 测试结果汇总")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！MCP管理器功能正常。")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)