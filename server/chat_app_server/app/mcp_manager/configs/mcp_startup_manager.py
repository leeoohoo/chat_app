"""
MCP 配置初始化器的总入口管理类
统一管理所有 MCP 服务器的配置初始化
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..system_detector import SystemDetector
from .expert_stream_config import ExpertStreamConfigInitializer
from .file_reader_config import FileReaderConfigInitializer

logger = logging.getLogger(__name__)


class MCPStartupManager:
    """MCP 配置初始化器总入口管理类"""
    
    def __init__(self, config_dir: str = None, mcp_services_dir: str = None):
        """
        初始化管理器
        
        Args:
            config_dir: 配置文件目录
            mcp_services_dir: MCP服务目录路径
        """
        self.config_dir = config_dir
        
        # 如果没有指定mcp_services_dir，使用默认路径
        if mcp_services_dir is None:
            # 获取当前文件的父目录，然后向上找到项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent  # 回到chat_app_server目录
            mcp_services_dir = str(project_root / "mcp_services")
        
        self.mcp_services_dir = mcp_services_dir
        self.system_detector = SystemDetector(mcp_services_dir)
        
        # 初始化器实例字典
        self.initializers: Dict[str, Any] = {}
        
        logger.info(f"📋 MCP启动管理器已创建，配置目录: {config_dir}, MCP服务目录: {mcp_services_dir}")
    
    def _get_or_create_initializer(self, server_type: str, server_path: str):
        """
        获取或创建配置初始化器实例
        
        Args:
            server_type: 服务器类型
            server_path: 服务器可执行文件路径
            
        Returns:
            配置初始化器实例
        """
        if server_type not in self.initializers:
            if server_type == "expert-stream-server":
                self.initializers[server_type] = ExpertStreamConfigInitializer(
                    config_dir=self.config_dir,
                    server_script=server_path
                )
            elif server_type == "file-reader-server":
                self.initializers[server_type] = FileReaderConfigInitializer(
                    config_dir=self.config_dir,
                    server_script=server_path
                )
            else:
                logger.warning(f"⚠️ 未知的服务器类型: {server_type}")
                return None
            
            logger.info(f"📝 创建 {server_type} 配置初始化器")
        
        return self.initializers[server_type]
    
    async def _initialize_expert_stream(self, server_path: str) -> bool:
        """
        初始化 Expert Stream Server 配置
        
        Args:
            server_path: 服务器可执行文件路径
            
        Returns:
            是否初始化成功
        """
        try:
            initializer = self._get_or_create_initializer("expert-stream-server", server_path)
            if not initializer:
                return False
            
            # 初始化默认配置（直接使用get_default_config()中的所有配置）
            success = await initializer.initialize_config(
                alias="default",
                config_template="default"
                # 不传递custom_config，直接使用get_default_config()中的完整配置
            )
            
            if success:
                logger.info("✅ Expert Stream Server 启动初始化成功")
            else:
                logger.warning("⚠️ Expert Stream Server 启动初始化失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Expert Stream Server 启动初始化异常: {e}")
            return False
    
    async def _initialize_file_reader(self, server_path: str) -> bool:
        """
        初始化 File Reader Server 配置
        
        Args:
            server_path: 服务器可执行文件路径
            
        Returns:
            是否初始化成功
        """
        try:
            initializer = self._get_or_create_initializer("file-reader-server", server_path)
            if not initializer:
                return False
            
            # 初始化默认配置（直接使用get_default_config()中的所有配置）
            success = await initializer.initialize_config(
                alias="default",
                config_template="default"
                # 不传递project_root和custom_config，直接使用get_default_config()中的完整配置
            )
            
            if success:
                logger.info("✅ File Reader Server 启动初始化成功")
            else:
                logger.warning("⚠️ File Reader Server 启动初始化失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ File Reader Server 启动初始化异常: {e}")
            return False
    
    async def initialize_all(self) -> Dict[str, bool]:
        """
        初始化所有可用的MCP服务器配置
        
        Returns:
            各服务器初始化结果字典
        """
        logger.info("🚀 开始MCP配置启动初始化...")
        
        # 检测系统中可用的服务器
        available_servers = self.system_detector.get_available_servers()
        results = {}
        
        for server_type, server_path in available_servers.items():
            logger.info(f"🔧 初始化 {server_type} 配置...")
            
            if not server_path:
                logger.warning(f"⚠️ {server_type} 可执行文件路径未找到")
                results[server_type] = False
                continue
            
            # 根据服务器类型调用相应的初始化方法
            if server_type == "expert-stream-server":
                success = await self._initialize_expert_stream(server_path)
            elif server_type == "file-reader-server":
                success = await self._initialize_file_reader(server_path)
            else:
                logger.info(f"ℹ️ {server_type} 暂无启动初始化逻辑")
                success = None
            
            results[server_type] = success
        
        # 统计结果
        success_count = sum(1 for result in results.values() if result is True)
        failed_count = sum(1 for result in results.values() if result is False)
        skipped_count = sum(1 for result in results.values() if result is None)
        
        logger.info(f"✅ MCP配置启动初始化完成: {success_count} 成功, {failed_count} 失败, {skipped_count} 跳过")
        
        return results
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "available_servers": self.system_detector.get_available_servers(),
            "initialized_servers": list(self.initializers.keys()),
            "system_info": self.system_detector.get_system_info()
        }
    
    def get_initializer(self, server_type: str):
        """
        获取指定类型的配置初始化器
        
        Args:
            server_type: 服务器类型
            
        Returns:
            配置初始化器实例或None
        """
        return self.initializers.get(server_type)


# 全局实例
_startup_manager: Optional[MCPStartupManager] = None


def get_startup_manager(config_dir: str = None, mcp_services_dir: str = None) -> MCPStartupManager:
    """
    获取全局启动管理器实例
    
    Args:
        config_dir: 配置文件目录
        mcp_services_dir: MCP服务目录路径
        
    Returns:
        MCPStartupManager实例
    """
    global _startup_manager
    if _startup_manager is None:
        _startup_manager = MCPStartupManager(config_dir, mcp_services_dir)
    return _startup_manager


async def startup_initialize_mcp(config_dir: str = None, mcp_services_dir: str = None) -> Dict[str, bool]:
    """
    启动时初始化所有MCP配置的便捷函数
    
    Args:
        config_dir: 配置文件目录
        mcp_services_dir: MCP服务目录路径
        
    Returns:
        初始化结果字典
    """
    manager = get_startup_manager(config_dir, mcp_services_dir)
    return await manager.initialize_all()