"""
File Reader Server 配置初始化器
使用 SimpleClient 进行配置管理
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from mcp_framework.client.simple import SimpleClient

logger = logging.getLogger(__name__)


class FileReaderConfigInitializer:
    """File Reader Server 配置初始化器 - 基于 SimpleClient"""
    
    def __init__(self, config_dir: str, server_script: str):
        """
        初始化配置器
        
        Args:
            config_dir: 配置文件目录
            server_script: 服务器可执行文件路径
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.server_script = server_script
        self.server_type = "file-reader-server"
        
    def get_default_config(self) -> Dict[str, Any]:
        """
        获取 file-reader-server 的默认配置
        基于 SimpleClient 的配置格式
        """
        return {
            # 服务器基本信息
            "server_name": "FileReaderServer",
            "log_level": "INFO",
            "max_connections": 50,
            "timeout": 30,
            
            # 核心配置参数
            "project_root": "",  # 项目根目录，需要用户设置
            "max_file_size": 10,  # 最大文件大小（MB）
            "enable_hidden_files": False,  # 是否启用隐藏文件访问
            
            # 文件访问配置
            "allowed_extensions": [
                ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
                ".json", ".xml", ".yaml", ".yml", ".md", ".txt", ".log",
                ".conf", ".ini", ".cfg", ".toml", ".properties",
                ".sql", ".sh", ".bat", ".ps1", ".dockerfile", ".gitignore"
            ],
            "blocked_paths": [
                "__pycache__", ".git", ".svn", ".hg", "node_modules",
                ".vscode", ".idea", "*.pyc", "*.pyo", "*.pyd",
                ".DS_Store", "Thumbs.db"
            ],
            
            # 安全配置
            "enable_path_traversal_protection": True,
            "max_depth": 10,  # 最大目录遍历深度
            "enable_symlink_follow": False,  # 是否跟随符号链接
            
            # 缓存配置
            "enable_cache": True,
            "cache_ttl": 300,  # 缓存生存时间（秒）
            "max_cache_size": 100,  # 最大缓存条目数
            
            # 角色和工具配置
            "role": "file_reader",
            "tool_description": "📁 **File Reader** - Advanced File System Navigator",
            "parameter_description": "📂 **File Path**: Specify the file or directory path to read"
        }
    
    def get_development_config(self) -> Dict[str, Any]:
        """获取开发环境的配置模板"""
        config = self.get_default_config()
        config.update({
            "log_level": "DEBUG",
            "enable_hidden_files": True,
            "max_file_size": 50,  # 开发环境允许更大文件
            "allowed_extensions": config["allowed_extensions"] + [
                ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".php",
                ".rb", ".swift", ".kt", ".scala", ".clj", ".hs", ".elm"
            ],
            "max_search_results": 500,
            "enable_symlink_follow": True,
            "cache_size": 200
        })
        return config
    
    def get_production_config(self) -> Dict[str, Any]:
        """获取生产环境的配置模板"""
        config = self.get_default_config()
        config.update({
            "log_level": "WARNING",
            "max_file_size": 5,  # 生产环境限制文件大小
            "enable_hidden_files": False,
            "max_search_results": 50,
            "search_timeout": 15,
            "enable_symlink_follow": False,
            "restrict_to_project": True,
            "cache_size": 50
        })
        return config
    
    def get_research_config(self) -> Dict[str, Any]:
        """获取研究/分析环境的配置模板"""
        config = self.get_default_config()
        config.update({
            "log_level": "DEBUG",
            "max_file_size": 100,  # 研究环境允许大文件
            "enable_hidden_files": True,
            "allowed_extensions": config["allowed_extensions"] + [
                ".csv", ".tsv", ".xlsx", ".pdf", ".doc", ".docx",
                ".ipynb", ".r", ".R", ".m", ".mat", ".data"
            ],
            "max_search_results": 1000,
            "search_timeout": 60,
            "max_lines_per_file": 50000,
            "enable_symlink_follow": True,
            "cache_size": 500,
            "cache_ttl": 600
        })
        return config
    
    async def initialize_config(self, alias: str,
                         config_template: str = "default",
                         project_root: Optional[str] = None,
                         custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        使用 SimpleClient 初始化配置文件
        
        Args:
            alias: 配置别名
            config_template: 配置模板类型 ("default", "development", "production", "research")
            project_root: 项目根目录
            custom_config: 自定义配置参数
            
        Returns:
            是否初始化成功
        """
        try:
            logger.info(f"🚀 开始初始化 File Reader Server 配置: {alias}")
            
            # 获取配置模板
            if config_template == "development":
                config = self.get_development_config()
            elif config_template == "production":
                config = self.get_production_config()
            elif config_template == "research":
                config = self.get_research_config()
            else:
                config = self.get_default_config()
            
            # 设置项目根目录
            if project_root:
                config["project_root"] = project_root
            
            # 设置角色为别名
            config["role"] = alias
            
            # 应用自定义配置
            if custom_config:
                config.update(custom_config)
            
            # 使用 SimpleClient 创建配置
            async with SimpleClient(
                self.server_script,
                alias=alias,
                config_dir=str(self.config_dir),
                startup_timeout=15.0,
                response_timeout=60.0
            ) as client:
                # 获取当前配置
                current_config = await client.config()
                
                # 批量更新配置
                await client.update(**config)
            
            logger.info(f"✅ File Reader Server 配置初始化成功: {alias}")
            logger.info(f"📁 配置目录: {self.config_dir}")
            logger.info(f"🎯 配置模板: {config_template}")
            if project_root:
                logger.info(f"📂 项目根目录: {project_root}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置初始化失败: {e}")
            return False
    
    async def update_config(self, alias: str, updates: Dict[str, Any]) -> bool:
        """
        使用 SimpleClient 更新配置
        
        Args:
            alias: 配置别名
            updates: 要更新的配置项
            
        Returns:
            是否更新成功
        """
        try:
            logger.info(f"🔄 开始更新配置: {alias}")
            
            # 使用 SimpleClient 更新配置
            async with SimpleClient(
                self.server_script,
                alias=alias,
                config_dir=str(self.config_dir),
                startup_timeout=15.0,
                response_timeout=60.0
            ) as client:
                # 更新配置
                await client.update(**updates)
            
            logger.info(f"✅ 配置更新成功: {alias}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置更新失败: {e}")
            return False
    
    async def get_config(self, alias: str) -> Optional[Dict[str, Any]]:
        """
        使用 SimpleClient 获取配置
        
        Args:
            alias: 配置别名
            
        Returns:
            配置字典或None
        """
        try:
            async with SimpleClient(
                self.server_script,
                alias=alias,
                config_dir=str(self.config_dir),
                startup_timeout=15.0,
                response_timeout=60.0
            ) as client:
                # 获取配置
                config = await client.config()
            
            logger.info(f"✅ 配置获取成功: {alias}")
            return config
            
        except Exception as e:
            logger.error(f"❌ 配置获取失败: {e}")
            return None
    
    def validate_config(self, alias: str) -> bool:
        """
        验证配置文件的完整性
        
        Args:
            alias: 配置别名
            
        Returns:
            配置有效返回True
        """
        config_file = self.config_dir / f"{alias}.json"
        
        if not config_file.exists():
            logger.warning(f"⚠️ 配置文件不存在: {config_file}")
            return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 检查必需的配置项
            required_fields = [
                "server_type", "alias", "executable_path", "project_root"
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in config or not config[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"⚠️ 配置缺少必需字段: {missing_fields}")
                return False
            
            # 检查服务器类型
            if config.get("server_type") != self.server_type:
                logger.warning(f"⚠️ 服务器类型不匹配: 期望 {self.server_type}, 实际 {config.get('server_type')}")
                return False
            
            # 检查项目根目录是否存在
            project_root = Path(config["project_root"])
            if not project_root.exists():
                logger.warning(f"⚠️ 项目根目录不存在: {project_root}")
                return False
            
            # 检查数值配置的合理性
            if config.get("max_file_size", 0) <= 0:
                logger.warning(f"⚠️ 最大文件大小配置无效: {config.get('max_file_size')}")
                return False
            
            logger.info(f"✅ File Reader Server 配置验证通过: {alias}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置验证失败: {e}")
            return False
    
    def get_config_templates(self) -> Dict[str, str]:
        """获取可用的配置模板列表"""
        return {
            "default": "默认配置 - 通用文件读取",
            "development": "开发配置 - 开发环境优化",
            "production": "生产配置 - 安全限制",
            "research": "研究配置 - 大文件分析"
        }
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_config_summary(self, alias: str) -> Optional[Dict[str, Any]]:
        """
        获取配置摘要信息
        
        Args:
            alias: 配置别名
            
        Returns:
            配置摘要字典
        """
        config_file = self.config_dir / f"{alias}.json"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return {
                "alias": config.get("alias", alias),
                "server_type": config.get("server_type", "unknown"),
                "project_root": config.get("project_root", "unknown"),
                "max_file_size": config.get("max_file_size", "unknown"),
                "enable_hidden_files": config.get("enable_hidden_files", False),
                "created_at": config.get("created_at", "unknown"),
                "updated_at": config.get("updated_at", "unknown"),
                "version": config.get("version", "unknown"),
                "allowed_extensions_count": len(config.get("allowed_extensions", [])),
                "config_file": str(config_file)
            }
            
        except Exception as e:
            logger.error(f"❌ 获取配置摘要失败: {e}")
            return None
    
    def set_project_root(self, alias: str, project_root: str) -> bool:
        """
        设置项目根目录
        
        Args:
            alias: 配置别名
            project_root: 新的项目根目录
            
        Returns:
            设置成功返回True
        """
        # 验证目录是否存在
        root_path = Path(project_root)
        if not root_path.exists():
            logger.error(f"❌ 项目根目录不存在: {project_root}")
            return False
        
        if not root_path.is_dir():
            logger.error(f"❌ 路径不是目录: {project_root}")
            return False
        
        # 更新配置
        return self.update_config(alias, {"project_root": str(root_path.absolute())})
    
    def get_project_root(self, alias: str) -> Optional[str]:
        """
        获取项目根目录
        
        Args:
            alias: 配置别名
            
        Returns:
            项目根目录路径，如果不存在则返回None
        """
        config_file = self.config_dir / f"{alias}.json"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get("project_root")
        except Exception as e:
            logger.error(f"❌ 获取项目根目录失败: {e}")
            return None