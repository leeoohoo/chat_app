"""
MCP管理器使用示例
展示如何在实际项目中使用MCP管理器来管理MCP服务器
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from app.mcp_manager import McpManager


def example_basic_usage():
    """基本使用示例"""
    print("📚 基本使用示例")
    print("=" * 50)
    
    # 1. 初始化MCP管理器
    mcp_manager = McpManager()
    
    # 2. 获取系统信息
    system_info = mcp_manager.get_system_info()
    print(f"🖥️ 当前系统: {system_info['os']} ({system_info['arch']})")
    
    # 3. 检查可用服务器
    available_servers = mcp_manager.get_available_servers()
    print(f"🔧 可用服务器: {list(available_servers.keys())}")
    
    # 4. 为所有可用服务器设置配置
    setup_results = mcp_manager.setup_all_available_servers()
    print(f"⚙️ 配置设置结果: {setup_results}")
    
    return mcp_manager


def example_get_server_config():
    """获取服务器配置示例"""
    print("\n📋 获取服务器配置示例")
    print("=" * 50)
    
    mcp_manager = McpManager()
    
    # 获取expert-stream-server的推荐配置
    expert_config = mcp_manager.get_recommended_config_for_type("expert-stream-server")
    if expert_config:
        print("✅ Expert Stream Server 配置:")
        print(f"   别名: {expert_config['alias']}")
        print(f"   可执行文件: {expert_config['executable_path']}")
        print(f"   配置目录: {expert_config['config_dir']}")
        
        # 获取启动命令信息
        cmd_info = mcp_manager.get_server_command_info(expert_config['alias'])
        print(f"   启动命令: {cmd_info['command']}")
    
    # 获取file-reader-server的推荐配置
    file_reader_config = mcp_manager.get_recommended_config_for_type("file-reader-server")
    if file_reader_config:
        print("\n✅ File Reader Server 配置:")
        print(f"   别名: {file_reader_config['alias']}")
        print(f"   可执行文件: {file_reader_config['executable_path']}")
        print(f"   配置目录: {file_reader_config['config_dir']}")
        
        # 获取启动命令信息
        cmd_info = mcp_manager.get_server_command_info(file_reader_config['alias'])
        print(f"   启动命令: {cmd_info['command']}")
    
    return expert_config, file_reader_config


def example_custom_alias():
    """自定义别名示例"""
    print("\n🏷️ 自定义别名示例")
    print("=" * 50)
    
    mcp_manager = McpManager()
    
    # 使用自定义别名初始化expert-stream-server
    custom_alias = "my_expert_server"
    success, alias = mcp_manager.initialize_server_config(
        server_type="expert-stream-server",
        alias=custom_alias
    )
    
    if success:
        print(f"✅ 自定义别名配置成功: {alias}")
        
        # 获取配置信息
        config = mcp_manager.get_server_config(alias)
        if config:
            print(f"   服务器类型: {config['server_type']}")
            print(f"   可执行文件: {config['executable_path']}")
    else:
        print(f"❌ 自定义别名配置失败")


def example_integration_with_simple_client():
    """与SimpleClient集成示例"""
    print("\n🔗 与SimpleClient集成示例")
    print("=" * 50)
    
    mcp_manager = McpManager()
    
    # 获取expert-stream-server配置
    expert_config = mcp_manager.get_recommended_config_for_type("expert-stream-server")
    if expert_config:
        print("📋 Expert Stream Server SimpleClient 参数:")
        print(f"   server_script = '{expert_config['executable_path']}'")
        print(f"   alias = '{expert_config['alias']}'")
        print(f"   config_dir = '{expert_config['config_dir']}'")
        
        print("\n💡 SimpleClient 初始化代码示例:")
        print("```python")
        print("from your_simple_client_module import SimpleClient")
        print("")
        print("client = SimpleClient(")
        print(f"    server_script='{expert_config['executable_path']}',")
        print(f"    alias='{expert_config['alias']}',")
        print(f"    config_dir='{expert_config['config_dir']}'")
        print(")")
        print("```")
    
    # 获取file-reader-server配置
    file_reader_config = mcp_manager.get_recommended_config_for_type("file-reader-server")
    if file_reader_config:
        print("\n📋 File Reader Server SimpleClient 参数:")
        print(f"   server_script = '{file_reader_config['executable_path']}'")
        print(f"   alias = '{file_reader_config['alias']}'")
        print(f"   config_dir = '{file_reader_config['config_dir']}'")
        
        print("\n💡 SimpleClient 初始化代码示例:")
        print("```python")
        print("from your_simple_client_module import SimpleClient")
        print("")
        print("client = SimpleClient(")
        print(f"    server_script='{file_reader_config['executable_path']}',")
        print(f"    alias='{file_reader_config['alias']}',")
        print(f"    config_dir='{file_reader_config['config_dir']}'")
        print(")")
        print("```")


def example_config_management():
    """配置管理示例"""
    print("\n⚙️ 配置管理示例")
    print("=" * 50)
    
    mcp_manager = McpManager()
    
    # 列出所有配置
    all_configs = mcp_manager.list_all_server_configs()
    print(f"📋 总配置数: {len(all_configs)}")
    
    for alias, config in all_configs.items():
        print(f"   {alias}:")
        print(f"     类型: {config.get('server_type')}")
        print(f"     平台: {config.get('platform')}")
        print(f"     状态: {'✅ 有效' if mcp_manager.validate_server_config(alias) else '❌ 无效'}")
    
    # 按服务器类型分组显示
    print("\n📊 按服务器类型分组:")
    for server_type in ["expert-stream-server", "file-reader-server"]:
        configs = mcp_manager.get_configs_by_server_type(server_type)
        print(f"   {server_type}: {len(configs)} 个配置")
        for alias in configs.keys():
            print(f"     - {alias}")


def main():
    """主函数，运行所有示例"""
    print("🚀 MCP管理器使用示例")
    print("=" * 80)
    
    # 基本使用
    mcp_manager = example_basic_usage()
    
    # 获取服务器配置
    example_get_server_config()
    
    # 自定义别名
    example_custom_alias()
    
    # 与SimpleClient集成
    example_integration_with_simple_client()
    
    # 配置管理
    example_config_management()
    
    # 显示状态摘要
    print("\n📊 最终状态摘要")
    print("=" * 50)
    mcp_manager.print_status()
    
    print("\n🎉 所有示例运行完成！")


if __name__ == "__main__":
    main()