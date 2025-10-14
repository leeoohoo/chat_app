"""
系统检测器
根据操作系统和架构选择合适的MCP服务器文件
"""

import platform
import os
from typing import Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SystemDetector:
    """系统检测器，用于检测当前系统并选择合适的MCP服务器文件"""
    
    def __init__(self, mcp_services_dir: str):
        """
        初始化系统检测器
        
        Args:
            mcp_services_dir: MCP服务器文件目录
        """
        self.mcp_services_dir = Path(mcp_services_dir)
        self._system_info = self._detect_system()
        
    def _detect_system(self) -> Dict[str, str]:
        """检测当前系统信息"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # 标准化系统名称
        if system == "darwin":
            os_name = "macos"
        elif system == "windows":
            os_name = "windows"
        elif system == "linux":
            os_name = "linux"
        else:
            os_name = system
            
        # 标准化架构名称
        if machine in ["x86_64", "amd64"]:
            arch = "x86_64"
        elif machine in ["arm64", "aarch64"]:
            arch = "arm64"
        elif machine in ["i386", "i686"]:
            arch = "x86"
        else:
            arch = machine
            
        system_info = {
            "os": os_name,
            "arch": arch,
            "platform": f"{os_name}-{arch}"
        }
        
        logger.info(f"🔍 检测到系统信息: {system_info}")
        return system_info
    
    def get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        return self._system_info.copy()
    
    def get_server_executable_path(self, server_type: str) -> Optional[str]:
        """
        获取指定类型服务器的可执行文件路径
        
        Args:
            server_type: 服务器类型 (expert-stream-server, file-reader-server)
            
        Returns:
            可执行文件的完整路径，如果找不到则返回None
        """
        platform_name = self._system_info["platform"]
        
        # 构建服务器目录名
        server_dir_name = f"{server_type}-{platform_name}"
        server_dir = self.mcp_services_dir / server_dir_name
        
        # 确定可执行文件名
        if self._system_info["os"] == "windows":
            executable_name = f"{server_type}.exe"
        else:
            executable_name = server_type
            
        executable_path = server_dir / executable_name
        
        # 检查文件是否存在
        if executable_path.exists():
            logger.info(f"✅ 找到 {server_type} 可执行文件: {executable_path}")
            return str(executable_path)
        else:
            logger.warning(f"❌ 未找到 {server_type} 可执行文件: {executable_path}")
            return None
    
    def get_available_servers(self) -> Dict[str, str]:
        """
        获取所有可用的服务器类型及其可执行文件路径
        
        Returns:
            字典，键为服务器类型，值为可执行文件路径
        """
        server_types = ["expert-stream-server", "file-reader-server"]
        available_servers = {}
        
        for server_type in server_types:
            executable_path = self.get_server_executable_path(server_type)
            if executable_path:
                available_servers[server_type] = executable_path
                
        logger.info(f"📋 可用服务器: {list(available_servers.keys())}")
        return available_servers
    
    def validate_server_path(self, server_path: str) -> bool:
        """
        验证服务器路径是否有效
        
        Args:
            server_path: 服务器可执行文件路径
            
        Returns:
            如果路径有效且文件存在则返回True
        """
        path = Path(server_path)
        
        if not path.exists():
            logger.error(f"❌ 服务器文件不存在: {server_path}")
            return False
            
        if not path.is_file():
            logger.error(f"❌ 路径不是文件: {server_path}")
            return False
            
        # 在Unix系统上检查执行权限
        if self._system_info["os"] != "windows":
            if not os.access(path, os.X_OK):
                logger.warning(f"⚠️ 文件没有执行权限: {server_path}")
                # 尝试添加执行权限
                try:
                    path.chmod(path.stat().st_mode | 0o111)
                    logger.info(f"✅ 已添加执行权限: {server_path}")
                except Exception as e:
                    logger.error(f"❌ 无法添加执行权限: {e}")
                    return False
                    
        logger.info(f"✅ 服务器路径验证通过: {server_path}")
        return True
    
    def get_recommended_server_config(self, server_type: str) -> Optional[Dict[str, str]]:
        """
        获取推荐的服务器配置
        
        Args:
            server_type: 服务器类型
            
        Returns:
            包含服务器配置信息的字典
        """
        executable_path = self.get_server_executable_path(server_type)
        if not executable_path:
            return None
            
        config = {
            "server_type": server_type,
            "executable_path": executable_path,
            "platform": self._system_info["platform"],
            "os": self._system_info["os"],
            "arch": self._system_info["arch"]
        }
        
        return config