"""
配置初始化工厂类
根据服务器类型选择对应的配置初始化器
"""

import logging
from typing import Dict, Any, Optional, Type, Union
from pathlib import Path

from .expert_stream_config import ExpertStreamConfigInitializer
from .file_reader_config import FileReaderConfigInitializer

logger = logging.getLogger(__name__)


class ConfigInitializerFactory:
    """配置初始化器工厂类"""
    
    # 支持的服务器类型映射
    SUPPORTED_SERVERS = {
        "expert-stream-server": ExpertStreamConfigInitializer,
        "file-reader-server": FileReaderConfigInitializer,
    }
    
    def __init__(self, config_dir: str):
        """
        初始化工厂
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._initializers = {}  # 缓存初始化器实例
        
    def get_initializer(self, server_type: str) -> Optional[Union[ExpertStreamConfigInitializer, FileReaderConfigInitializer]]:
        """
        获取指定服务器类型的配置初始化器
        
        Args:
            server_type: 服务器类型
            
        Returns:
            对应的配置初始化器实例，如果不支持则返回None
        """
        if server_type not in self.SUPPORTED_SERVERS:
            logger.error(f"❌ 不支持的服务器类型: {server_type}")
            logger.info(f"📋 支持的服务器类型: {list(self.SUPPORTED_SERVERS.keys())}")
            return None
        
        # 使用缓存的初始化器实例
        if server_type not in self._initializers:
            initializer_class = self.SUPPORTED_SERVERS[server_type]
            self._initializers[server_type] = initializer_class(str(self.config_dir))
            logger.debug(f"🏭 创建 {server_type} 配置初始化器实例")
        
        return self._initializers[server_type]
    
    def initialize_config(self, server_type: str, alias: str, executable_path: str,
                         config_template: str = "default",
                         custom_config: Optional[Dict[str, Any]] = None,
                         **kwargs) -> bool:
        """
        初始化指定服务器类型的配置
        
        Args:
            server_type: 服务器类型
            alias: 配置别名
            executable_path: 可执行文件路径
            config_template: 配置模板类型
            custom_config: 自定义配置覆盖
            **kwargs: 其他特定于服务器类型的参数
            
        Returns:
            初始化成功返回True
        """
        initializer = self.get_initializer(server_type)
        if not initializer:
            return False
        
        try:
            logger.info(f"🚀 开始初始化 {server_type} 配置: {alias}")
            
            # 调用对应初始化器的初始化方法
            success = initializer.initialize_config(
                alias=alias,
                executable_path=executable_path,
                config_template=config_template,
                custom_config=custom_config,
                **kwargs
            )
            
            if success:
                logger.info(f"✅ {server_type} 配置初始化成功: {alias}")
            else:
                logger.error(f"❌ {server_type} 配置初始化失败: {alias}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 配置初始化过程中发生异常: {e}")
            return False
    
    def validate_config(self, server_type: str, alias: str) -> bool:
        """
        验证指定服务器类型的配置
        
        Args:
            server_type: 服务器类型
            alias: 配置别名
            
        Returns:
            配置有效返回True
        """
        initializer = self.get_initializer(server_type)
        if not initializer:
            return False
        
        return initializer.validate_config(alias)
    
    def update_config(self, server_type: str, alias: str, updates: Dict[str, Any]) -> bool:
        """
        更新指定服务器类型的配置
        
        Args:
            server_type: 服务器类型
            alias: 配置别名
            updates: 要更新的配置项
            
        Returns:
            更新成功返回True
        """
        initializer = self.get_initializer(server_type)
        if not initializer:
            return False
        
        return initializer.update_config(alias, updates)
    
    def get_config_summary(self, server_type: str, alias: str) -> Optional[Dict[str, Any]]:
        """
        获取指定服务器类型的配置摘要
        
        Args:
            server_type: 服务器类型
            alias: 配置别名
            
        Returns:
            配置摘要字典
        """
        initializer = self.get_initializer(server_type)
        if not initializer:
            return None
        
        return initializer.get_config_summary(alias)
    
    def get_available_templates(self, server_type: str) -> Optional[Dict[str, str]]:
        """
        获取指定服务器类型的可用配置模板
        
        Args:
            server_type: 服务器类型
            
        Returns:
            可用模板字典
        """
        initializer = self.get_initializer(server_type)
        if not initializer:
            return None
        
        return initializer.get_config_templates()
    
    def get_supported_servers(self) -> Dict[str, str]:
        """
        获取支持的服务器类型列表
        
        Returns:
            支持的服务器类型及其描述
        """
        return {
            "expert-stream-server": "专家流服务器 - AI对话和专家咨询",
            "file-reader-server": "文件读取服务器 - 文件系统访问和内容读取"
        }
    
    def list_configs_by_type(self, server_type: str) -> Dict[str, Dict[str, Any]]:
        """
        列出指定服务器类型的所有配置
        
        Args:
            server_type: 服务器类型
            
        Returns:
            配置字典，键为别名，值为配置摘要
        """
        configs = {}
        
        # 查找所有配置文件
        for config_file in self.config_dir.glob("*.json"):
            alias = config_file.stem
            summary = self.get_config_summary(server_type, alias)
            
            # 只返回匹配服务器类型的配置
            if summary and summary.get("server_type") == server_type:
                configs[alias] = summary
        
        return configs
    
    def list_all_configs(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        列出所有服务器类型的配置
        
        Returns:
            按服务器类型分组的配置字典
        """
        all_configs = {}
        
        for server_type in self.SUPPORTED_SERVERS.keys():
            configs = self.list_configs_by_type(server_type)
            if configs:
                all_configs[server_type] = configs
        
        return all_configs
    
    def delete_config(self, alias: str) -> bool:
        """
        删除配置文件
        
        Args:
            alias: 配置别名
            
        Returns:
            删除成功返回True
        """
        config_file = self.config_dir / f"{alias}.json"
        
        if not config_file.exists():
            logger.warning(f"⚠️ 配置文件不存在: {config_file}")
            return False
        
        try:
            config_file.unlink()
            logger.info(f"🗑️ 配置文件已删除: {alias}")
            return True
        except Exception as e:
            logger.error(f"❌ 删除配置文件失败: {e}")
            return False
    
    def copy_config(self, source_alias: str, target_alias: str, 
                   server_type: Optional[str] = None) -> bool:
        """
        复制配置文件
        
        Args:
            source_alias: 源配置别名
            target_alias: 目标配置别名
            server_type: 服务器类型（可选，用于验证）
            
        Returns:
            复制成功返回True
        """
        source_file = self.config_dir / f"{source_alias}.json"
        target_file = self.config_dir / f"{target_alias}.json"
        
        if not source_file.exists():
            logger.error(f"❌ 源配置文件不存在: {source_file}")
            return False
        
        if target_file.exists():
            logger.error(f"❌ 目标配置文件已存在: {target_file}")
            return False
        
        try:
            import json
            
            # 读取源配置
            with open(source_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证服务器类型（如果指定）
            if server_type and config.get("server_type") != server_type:
                logger.error(f"❌ 服务器类型不匹配: 期望 {server_type}, 实际 {config.get('server_type')}")
                return False
            
            # 更新别名和时间戳
            config["alias"] = target_alias
            config["created_at"] = self._get_current_timestamp()
            config["updated_at"] = self._get_current_timestamp()
            
            # 保存目标配置
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📋 配置复制成功: {source_alias} -> {target_alias}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置复制失败: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_factory_status(self) -> Dict[str, Any]:
        """
        获取工厂状态信息
        
        Returns:
            工厂状态字典
        """
        status = {
            "config_dir": str(self.config_dir),
            "supported_servers": list(self.SUPPORTED_SERVERS.keys()),
            "initialized_types": list(self._initializers.keys()),
            "total_configs": len(list(self.config_dir.glob("*.json"))),
            "configs_by_type": {}
        }
        
        # 统计各类型配置数量
        for server_type in self.SUPPORTED_SERVERS.keys():
            configs = self.list_configs_by_type(server_type)
            status["configs_by_type"][server_type] = len(configs)
        
        return status
    
    def cleanup_invalid_configs(self) -> Dict[str, Any]:
        """
        清理无效的配置文件
        
        Returns:
            清理结果统计
        """
        cleanup_result = {
            "total_checked": 0,
            "invalid_configs": [],
            "deleted_configs": [],
            "errors": []
        }
        
        # 检查所有配置文件
        for config_file in self.config_dir.glob("*.json"):
            alias = config_file.stem
            cleanup_result["total_checked"] += 1
            
            try:
                import json
                
                # 读取配置文件
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                server_type = config.get("server_type")
                
                # 检查是否为支持的服务器类型
                if server_type not in self.SUPPORTED_SERVERS:
                    cleanup_result["invalid_configs"].append({
                        "alias": alias,
                        "reason": f"不支持的服务器类型: {server_type}"
                    })
                    continue
                
                # 验证配置
                if not self.validate_config(server_type, alias):
                    cleanup_result["invalid_configs"].append({
                        "alias": alias,
                        "reason": "配置验证失败"
                    })
                
            except Exception as e:
                cleanup_result["errors"].append({
                    "alias": alias,
                    "error": str(e)
                })
        
        logger.info(f"🧹 配置清理完成: 检查 {cleanup_result['total_checked']} 个配置")
        logger.info(f"⚠️ 发现 {len(cleanup_result['invalid_configs'])} 个无效配置")
        logger.info(f"❌ 发生 {len(cleanup_result['errors'])} 个错误")
        
        return cleanup_result