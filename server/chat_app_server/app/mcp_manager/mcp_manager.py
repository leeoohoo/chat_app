"""
MCP管理器主类
整合系统检测和配置管理功能，提供统一的MCP服务器管理接口
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from .system_detector import SystemDetector
from .config_manager import ConfigManager
from .configs import ConfigInitializerFactory

logger = logging.getLogger(__name__)


class McpManager:
    """MCP管理器，提供统一的MCP服务器管理接口"""
    
    def __init__(self, mcp_services_dir: Optional[str] = None, config_dir: Optional[str] = None):
        """
        初始化MCP管理器
        
        Args:
            mcp_services_dir: MCP服务器文件目录，默认为相对于当前文件的mcp_services目录
            config_dir: 配置文件目录，默认为相对于当前文件的mcp_config目录
        """
        # 设置默认路径
        if mcp_services_dir is None:
            current_dir = Path(__file__).parent.parent.parent
            mcp_services_dir = current_dir / "mcp_services"
            
        if config_dir is None:
            current_dir = Path(__file__).parent.parent
            config_dir = current_dir / "mcp_config"
            
        self.mcp_services_dir = str(mcp_services_dir)
        self.config_dir = str(config_dir)
        
        # 初始化组件
        self.system_detector = SystemDetector(self.mcp_services_dir)
        self.config_manager = ConfigManager(self.config_dir)
        self.config_factory = ConfigInitializerFactory(self.config_dir)
        
        logger.info(f"🚀 MCP管理器初始化完成")
        logger.info(f"📁 MCP服务器目录: {self.mcp_services_dir}")
        logger.info(f"⚙️ 配置目录: {self.config_dir}")
        logger.info(f"🏭 配置工厂已初始化，支持的服务器类型: {list(self.config_factory.get_supported_servers().keys())}")
    
    def get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        return self.system_detector.get_system_info()
    
    def get_available_servers(self) -> Dict[str, str]:
        """获取所有可用的服务器类型及其可执行文件路径"""
        return self.system_detector.get_available_servers()
    
    def initialize_server_config(self, server_type: str, alias: Optional[str] = None, 
                               force_reinit: bool = False, config_template: str = "default",
                               custom_config: Optional[Dict[str, Any]] = None,
                               **kwargs) -> Tuple[bool, str]:
        """
        初始化服务器配置
        
        Args:
            server_type: 服务器类型 (expert-stream-server, file-reader-server)
            alias: 配置别名，如果不提供则自动生成
            force_reinit: 是否强制重新初始化
            config_template: 配置模板类型 (default, development, production等)
            custom_config: 自定义配置覆盖
            **kwargs: 其他特定于服务器类型的参数
            
        Returns:
            (成功标志, 配置别名)
        """
        # 检查服务器类型是否支持
        if server_type not in self.config_factory.get_supported_servers():
            logger.error(f"❌ 不支持的服务器类型: {server_type}")
            logger.info(f"📋 支持的服务器类型: {list(self.config_factory.get_supported_servers().keys())}")
            return False, ""
        
        # 获取可执行文件路径
        executable_path = self.system_detector.get_server_executable_path(server_type)
        if not executable_path:
            logger.error(f"❌ 无法找到 {server_type} 的可执行文件")
            return False, ""
            
        # 验证可执行文件
        if not self.system_detector.validate_server_path(executable_path):
            logger.error(f"❌ 服务器文件验证失败: {executable_path}")
            return False, ""
            
        # 生成或使用提供的别名
        if alias is None:
            alias = self.config_manager.generate_unique_alias(server_type)
        
        # 检查是否已存在配置
        if self.config_manager.alias_exists(alias) and not force_reinit:
            logger.info(f"ℹ️ 配置已存在: {alias}")
            return True, alias
            
        # 准备系统信息配置
        system_info = self.system_detector.get_system_info()
        system_config = {
            "platform": system_info["platform"],
            "os": system_info["os"],
            "arch": system_info["arch"],
            "mcp_services_dir": self.mcp_services_dir
        }
        
        # 合并自定义配置
        if custom_config is None:
            custom_config = {}
        custom_config.update(system_config)
        
        # 使用配置工厂初始化配置
        success = self.config_factory.initialize_config(
            server_type=server_type,
            alias=alias,
            executable_path=executable_path,
            config_template=config_template,
            custom_config=custom_config,
            **kwargs
        )
        
        if success:
            logger.info(f"🎉 服务器配置初始化成功: {server_type} -> {alias} (模板: {config_template})")
        else:
            logger.error(f"❌ 服务器配置初始化失败: {server_type}")
            
        return success, alias
    
    def get_server_config(self, alias: str) -> Optional[Dict[str, Any]]:
        """
        获取服务器配置
        
        Args:
            alias: 配置别名
            
        Returns:
            配置字典，如果不存在则返回None
        """
        return self.config_manager.get_config(alias)
    
    def list_all_server_configs(self) -> Dict[str, Dict[str, Any]]:
        """列出所有服务器配置"""
        return self.config_manager.list_all_configs()
    
    def get_configs_by_server_type(self, server_type: str) -> Dict[str, Dict[str, Any]]:
        """根据服务器类型获取配置"""
        return self.config_manager.get_configs_by_server_type(server_type)
    
    def delete_server_config(self, alias: str) -> bool:
        """删除服务器配置"""
        return self.config_manager.delete_config(alias)
    
    def validate_server_config(self, alias: str) -> bool:
        """验证服务器配置的有效性"""
        return self.config_manager.validate_config(alias)
    
    def get_server_command_info(self, alias: str) -> Optional[Dict[str, str]]:
        """
        获取服务器启动命令信息
        
        Args:
            alias: 配置别名
            
        Returns:
            包含启动命令信息的字典
        """
        config = self.get_server_config(alias)
        if not config:
            return None
            
        return {
            "command": config["executable_path"],
            "alias": alias,
            "config_dir": self.config_dir,
            "server_type": config["server_type"]
        }
    
    def setup_all_available_servers(self) -> Dict[str, str]:
        """
        为所有可用的服务器类型设置配置
        
        Returns:
            字典，键为服务器类型，值为配置别名
        """
        available_servers = self.get_available_servers()
        setup_results = {}
        
        for server_type in available_servers.keys():
            success, alias = self.initialize_server_config(server_type)
            if success:
                setup_results[server_type] = alias
                logger.info(f"✅ {server_type} 配置设置完成: {alias}")
            else:
                logger.error(f"❌ {server_type} 配置设置失败")
                
        return setup_results
    
    def get_recommended_config_for_type(self, server_type: str) -> Optional[Dict[str, Any]]:
        """
        获取指定服务器类型的推荐配置
        
        Args:
            server_type: 服务器类型
            
        Returns:
            推荐配置字典
        """
        # 首先检查是否已有配置
        existing_configs = self.get_configs_by_server_type(server_type)
        if existing_configs:
            # 返回第一个有效配置
            for alias, config in existing_configs.items():
                if self.validate_server_config(alias):
                    logger.info(f"📋 使用现有配置: {server_type} -> {alias}")
                    return config
                    
        # 如果没有有效配置，创建新的
        success, alias = self.initialize_server_config(server_type)
        if success:
            return self.get_server_config(alias)
            
        return None
    
    def cleanup_invalid_configs(self) -> List[str]:
        """
        清理无效的配置
        
        Returns:
            被清理的配置别名列表
        """
        all_configs = self.list_all_server_configs()
        cleaned_aliases = []
        
        for alias in all_configs.keys():
            if not self.validate_server_config(alias):
                if self.delete_server_config(alias):
                    cleaned_aliases.append(alias)
                    logger.info(f"🧹 清理无效配置: {alias}")
                    
        logger.info(f"🧹 清理完成，共清理 {len(cleaned_aliases)} 个无效配置")
        return cleaned_aliases
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取MCP管理器状态摘要
        
        Returns:
            状态摘要字典
        """
        system_info = self.get_system_info()
        available_servers = self.get_available_servers()
        all_configs = self.list_all_server_configs()
        
        # 统计各服务器类型的配置数量
        config_stats = {}
        for alias, config in all_configs.items():
            server_type = config.get("server_type", "unknown")
            if server_type not in config_stats:
                config_stats[server_type] = 0
            config_stats[server_type] += 1
            
        summary = {
            "system_info": system_info,
            "available_servers": list(available_servers.keys()),
            "total_configs": len(all_configs),
            "config_stats": config_stats,
            "config_dir": self.config_dir,
            "mcp_services_dir": self.mcp_services_dir
        }
        
        return summary
    
    def print_status(self):
        """打印状态信息"""
        summary = self.get_status_summary()
        
        print("🔍 MCP管理器状态")
        print("=" * 50)
    
    # 新增的配置工厂相关方法
    
    def get_available_config_templates(self, server_type: str) -> Optional[Dict[str, str]]:
        """
        获取指定服务器类型的可用配置模板
        
        Args:
            server_type: 服务器类型
            
        Returns:
            可用模板字典，键为模板名，值为描述
        """
        return self.config_factory.get_available_templates(server_type)
    
    def initialize_server_with_template(self, server_type: str, template: str,
                                      alias: Optional[str] = None,
                                      **kwargs) -> Tuple[bool, str]:
        """
        使用指定模板初始化服务器配置
        
        Args:
            server_type: 服务器类型
            template: 配置模板名称
            alias: 配置别名
            **kwargs: 其他参数
            
        Returns:
            (成功标志, 配置别名)
        """
        return self.initialize_server_config(
            server_type=server_type,
            alias=alias,
            config_template=template,
            **kwargs
        )
    
    def update_server_config(self, alias: str, updates: Dict[str, Any]) -> bool:
        """
        更新服务器配置
        
        Args:
            alias: 配置别名
            updates: 要更新的配置项
            
        Returns:
            更新成功返回True
        """
        # 首先获取配置以确定服务器类型
        config = self.get_server_config(alias)
        if not config:
            logger.error(f"❌ 配置不存在: {alias}")
            return False
        
        server_type = config.get("server_type")
        if not server_type:
            logger.error(f"❌ 无法确定服务器类型: {alias}")
            return False
        
        return self.config_factory.update_config(server_type, alias, updates)
    
    def get_config_summary_by_factory(self, alias: str) -> Optional[Dict[str, Any]]:
        """
        使用配置工厂获取配置摘要
        
        Args:
            alias: 配置别名
            
        Returns:
            配置摘要字典
        """
        # 首先获取配置以确定服务器类型
        config = self.get_server_config(alias)
        if not config:
            return None
        
        server_type = config.get("server_type")
        if not server_type:
            return None
        
        return self.config_factory.get_config_summary(server_type, alias)
    
    def list_configs_by_factory(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        使用配置工厂列出所有配置，按服务器类型分组
        
        Returns:
            按服务器类型分组的配置字典
        """
        return self.config_factory.list_all_configs()
    
    def copy_server_config(self, source_alias: str, target_alias: str) -> bool:
        """
        复制服务器配置
        
        Args:
            source_alias: 源配置别名
            target_alias: 目标配置别名
            
        Returns:
            复制成功返回True
        """
        # 获取源配置以确定服务器类型
        source_config = self.get_server_config(source_alias)
        if not source_config:
            logger.error(f"❌ 源配置不存在: {source_alias}")
            return False
        
        server_type = source_config.get("server_type")
        if not server_type:
            logger.error(f"❌ 无法确定服务器类型: {source_alias}")
            return False
        
        return self.config_factory.copy_config(source_alias, target_alias, server_type)
    
    def cleanup_configs_by_factory(self) -> Dict[str, Any]:
        """
        使用配置工厂清理无效配置
        
        Returns:
            清理结果统计
        """
        return self.config_factory.cleanup_invalid_configs()
    
    def get_factory_status(self) -> Dict[str, Any]:
        """
        获取配置工厂状态
        
        Returns:
            工厂状态字典
        """
        return self.config_factory.get_factory_status()
    
    def validate_config_by_factory(self, alias: str) -> bool:
        """
        使用配置工厂验证配置
        
        Args:
            alias: 配置别名
            
        Returns:
            配置有效返回True
        """
        # 获取配置以确定服务器类型
        config = self.get_server_config(alias)
        if not config:
            return False
        
        server_type = config.get("server_type")
        if not server_type:
            return False
        
        return self.config_factory.validate_config(server_type, alias)
    
    def set_project_root_for_file_reader(self, alias: str, project_root: str) -> bool:
        """
        为file-reader-server设置项目根目录
        
        Args:
            alias: 配置别名
            project_root: 项目根目录路径
            
        Returns:
            设置成功返回True
        """
        # 验证是否为file-reader-server配置
        config = self.get_server_config(alias)
        if not config:
            logger.error(f"❌ 配置不存在: {alias}")
            return False
        
        if config.get("server_type") != "file-reader-server":
            logger.error(f"❌ 配置不是file-reader-server类型: {alias}")
            return False
        
        # 获取file-reader配置初始化器
        initializer = self.config_factory.get_initializer("file-reader-server")
        if not initializer:
            logger.error(f"❌ 无法获取file-reader配置初始化器")
            return False
        
        return initializer.set_project_root(alias, project_root)
    
    def get_project_root_for_file_reader(self, alias: str) -> Optional[str]:
        """
        获取file-reader-server的项目根目录
        
        Args:
            alias: 配置别名
            
        Returns:
            项目根目录路径，如果不存在则返回None
        """
        # 验证是否为file-reader-server配置
        config = self.get_server_config(alias)
        if not config:
            return None
        
        if config.get("server_type") != "file-reader-server":
            return None
        
        # 获取file-reader配置初始化器
        initializer = self.config_factory.get_initializer("file-reader-server")
        if not initializer:
            return None
        
        return initializer.get_project_root(alias)
        print(f"🖥️  系统: {summary['system_info']['os']} ({summary['system_info']['arch']})")
        print(f"📁 服务器目录: {summary['mcp_services_dir']}")
        print(f"⚙️  配置目录: {summary['config_dir']}")
        print(f"🔧 可用服务器: {', '.join(summary['available_servers'])}")
        print(f"📊 总配置数: {summary['total_configs']}")
        
        if summary['config_stats']:
            print("📋 配置统计:")
            for server_type, count in summary['config_stats'].items():
                print(f"   - {server_type}: {count} 个配置")
        
        print("=" * 50)