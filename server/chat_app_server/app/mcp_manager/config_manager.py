"""
配置管理器
用于管理MCP服务器的配置，包括检查别名配置是否存在，不存在则初始化
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器，用于管理MCP服务器配置"""
    
    def __init__(self, config_dir: str):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 配置目录: {self.config_dir}")
    
    def _get_config_file_path(self, alias: str) -> Path:
        """获取指定别名的配置文件路径"""
        return self.config_dir / f"{alias}.json"
    
    def _get_all_config_files(self) -> List[Path]:
        """获取所有配置文件"""
        return list(self.config_dir.glob("*.json"))
    
    def alias_exists(self, alias: str) -> bool:
        """
        检查指定别名的配置是否存在
        
        Args:
            alias: 配置别名
            
        Returns:
            如果配置存在则返回True
        """
        config_file = self._get_config_file_path(alias)
        exists = config_file.exists()
        logger.info(f"🔍 检查别名 '{alias}' 配置: {'存在' if exists else '不存在'}")
        return exists
    
    def get_config(self, alias: str) -> Optional[Dict[str, Any]]:
        """
        获取指定别名的配置
        
        Args:
            alias: 配置别名
            
        Returns:
            配置字典，如果不存在则返回None
        """
        config_file = self._get_config_file_path(alias)
        
        if not config_file.exists():
            logger.warning(f"⚠️ 配置文件不存在: {config_file}")
            return None
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✅ 成功读取配置: {alias}")
            return config
        except Exception as e:
            logger.error(f"❌ 读取配置文件失败: {e}")
            return None
    
    def save_config(self, alias: str, config: Dict[str, Any]) -> bool:
        """
        保存配置到指定别名
        
        Args:
            alias: 配置别名
            config: 配置字典
            
        Returns:
            保存成功返回True
        """
        config_file = self._get_config_file_path(alias)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 配置保存成功: {alias} -> {config_file}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}")
            return False
    
    def initialize_config(self, alias: str, server_type: str, executable_path: str, 
                         additional_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化配置
        
        Args:
            alias: 配置别名
            server_type: 服务器类型
            executable_path: 可执行文件路径
            additional_config: 额外的配置参数
            
        Returns:
            初始化成功返回True
        """
        if self.alias_exists(alias):
            logger.info(f"ℹ️ 配置已存在，跳过初始化: {alias}")
            return True
            
        # 基础配置
        config = {
            "alias": alias,
            "server_type": server_type,
            "executable_path": executable_path,
            "config_dir": str(self.config_dir),
            "created_at": str(Path().cwd()),  # 当前时间戳
            "status": "initialized"
        }
        
        # 添加额外配置
        if additional_config:
            config.update(additional_config)
            
        success = self.save_config(alias, config)
        if success:
            logger.info(f"🎉 配置初始化成功: {alias}")
        else:
            logger.error(f"❌ 配置初始化失败: {alias}")
            
        return success
    
    def generate_unique_alias(self, server_type: str, prefix: str = "mcp") -> str:
        """
        生成唯一的别名
        
        Args:
            server_type: 服务器类型
            prefix: 别名前缀
            
        Returns:
            唯一的别名
        """
        # 生成基础别名
        base_alias = f"{prefix}_{server_type.replace('-', '_')}"
        
        # 如果不存在，直接返回
        if not self.alias_exists(base_alias):
            return base_alias
            
        # 如果存在，添加UUID后缀
        unique_suffix = str(uuid.uuid4())[:8]
        unique_alias = f"{base_alias}_{unique_suffix}"
        
        # 确保唯一性
        while self.alias_exists(unique_alias):
            unique_suffix = str(uuid.uuid4())[:8]
            unique_alias = f"{base_alias}_{unique_suffix}"
            
        logger.info(f"🔄 生成唯一别名: {unique_alias}")
        return unique_alias
    
    def list_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有配置
        
        Returns:
            所有配置的字典，键为别名，值为配置内容
        """
        configs = {}
        config_files = self._get_all_config_files()
        
        for config_file in config_files:
            alias = config_file.stem  # 文件名不含扩展名
            config = self.get_config(alias)
            if config:
                configs[alias] = config
                
        logger.info(f"📋 找到 {len(configs)} 个配置")
        return configs
    
    def delete_config(self, alias: str) -> bool:
        """
        删除指定别名的配置
        
        Args:
            alias: 配置别名
            
        Returns:
            删除成功返回True
        """
        config_file = self._get_config_file_path(alias)
        
        if not config_file.exists():
            logger.warning(f"⚠️ 配置不存在，无需删除: {alias}")
            return True
            
        try:
            config_file.unlink()
            logger.info(f"🗑️ 配置删除成功: {alias}")
            return True
        except Exception as e:
            logger.error(f"❌ 删除配置失败: {e}")
            return False
    
    def update_config(self, alias: str, updates: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            alias: 配置别名
            updates: 要更新的配置项
            
        Returns:
            更新成功返回True
        """
        config = self.get_config(alias)
        if not config:
            logger.error(f"❌ 配置不存在，无法更新: {alias}")
            return False
            
        # 更新配置
        config.update(updates)
        
        return self.save_config(alias, config)
    
    def get_configs_by_server_type(self, server_type: str) -> Dict[str, Dict[str, Any]]:
        """
        根据服务器类型获取配置
        
        Args:
            server_type: 服务器类型
            
        Returns:
            匹配的配置字典
        """
        all_configs = self.list_all_configs()
        matching_configs = {}
        
        for alias, config in all_configs.items():
            if config.get("server_type") == server_type:
                matching_configs[alias] = config
                
        logger.info(f"🔍 找到 {len(matching_configs)} 个 {server_type} 类型的配置")
        return matching_configs
    
    def validate_config(self, alias: str) -> bool:
        """
        验证配置的有效性
        
        Args:
            alias: 配置别名
            
        Returns:
            配置有效返回True
        """
        config = self.get_config(alias)
        if not config:
            return False
            
        # 检查必需字段
        required_fields = ["alias", "server_type", "executable_path"]
        for field in required_fields:
            if field not in config:
                logger.error(f"❌ 配置缺少必需字段 '{field}': {alias}")
                return False
                
        # 检查可执行文件是否存在
        executable_path = config.get("executable_path")
        if not Path(executable_path).exists():
            logger.error(f"❌ 可执行文件不存在: {executable_path}")
            return False
            
        logger.info(f"✅ 配置验证通过: {alias}")
        return True