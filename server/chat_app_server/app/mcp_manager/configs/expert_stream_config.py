"""
Expert Stream Server 配置初始化器
使用 SimpleClient 进行配置管理
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from mcp_framework.client.simple import SimpleClient

from ...utils.config_reader import get_config_dir

logger = logging.getLogger(__name__)


class ExpertStreamConfigInitializer:
    """Expert Stream Server 配置初始化器 - 基于 SimpleClient"""
    
    def __init__(self, config_dir: str = None, server_script: str = None):
        """
        初始化配置器
        
        Args:
            config_dir: 配置文件目录，如果为None则从配置文件读取
            server_script: 服务器可执行文件路径
        """
        if config_dir is None:
            config_dir = get_config_dir()
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.server_script = server_script
        self.server_type = "expert-stream-server"
        
    def get_default_config(self) -> Dict[str, Any]:
        """
        获取 expert-stream-server 的默认配置
        基于 SimpleClient 的配置格式
        """
        return {
            # 服务器基本信息
            "server_name": "ExpertStreamServer",
            "log_level": "INFO",
            "max_connections": 100,
            "timeout": 30,
            # 核心配置参数 - 需要用户配置
            "api_key": "16994514-0eaa-450b-961a-372e5eae0509",  # 需要用户提供
            "model_name": "kimi-k2-250905",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "system_prompt": "你是一个专业的AI助手，能够熟练的使用工具查到对应的文件后提供准确、详细和有用的回答。",
            
            # MCP服务器配置
            "mcp_servers": "[]",  # JSON字符串格式
            
            # stdio MCP服务器配置
            "stdio_mcp_servers": "file_find:/Users/lilei/project/learn/chat_app/server/chat_app_server/mcp_services/file-reader-server-macos-arm64/file-reader-server--default",  # 格式: "server_name:path--alias"
            
            # 数据库配置
            "mongodb_url": "",  # 可选的MongoDB连接URL
            
            # 历史记录配置
            "history_limit": "10",
            "enable_history": False,
            
            # 角色和工具配置
            "role": "assistant",
            "tool_description": "🤖 **AI Assistant** - Professional AI Task Executor",
            "parameter_description": "🎯 **Task Parameter**: Send your request to the AI assistant",
            
            # 总结配置
            "summary_interval": 10,
            "max_rounds": 50,
            "summary_instruction": "You are a professional conversation analysis expert.",
            "summary_request": "Please analyze the conversation and provide a concise summary.",
            "summary_length_threshold": 50000
        }
    
  
    

    
    async def initialize_config(self, alias: str, 
                         config_template: str = "default",
                         custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        使用 SimpleClient 初始化配置文件
        
        Args:
            alias: 配置别名
            config_template: 配置模板类型
            custom_config: 自定义配置参数
            
        Returns:
            是否初始化成功
        """
        try:
            logger.info(f"🚀 开始初始化 Expert Stream Server 配置: {alias}")
            
           
            config = self.get_default_config()
            
            # 设置角色为别名
            config["role"] = alias
            
            # 应用自定义配置
            if custom_config:
                config.update(custom_config)
            
            # 使用 SimpleClient 创建配置
            async with SimpleClient(
                self.server_script,
                alias=alias,
                config_dir=str(self.config_dir)
            ) as client:
                # 获取当前配置
                current_config = await client.config()
                
                # 批量更新配置
                await client.update(**config)
            
            logger.info(f"✅ Expert Stream Server 配置初始化成功: {alias}")
            logger.info(f"📁 配置目录: {self.config_dir}")
            logger.info(f"🎯 配置模板: {config_template}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置初始化失败: {e}")
            return False
    
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
                "server_type", "alias", "executable_path",
                "model_name", "base_url", "system_prompt", "api_key"
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
            
            logger.info(f"✅ Expert Stream Server 配置验证通过: {alias}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置验证失败: {e}")
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
        config_file = self.config_dir / f"{alias}.json"
        
        if not config_file.exists():
            logger.warning(f"⚠️ 配置文件不存在: {config_file}")
            return False
        
        try:
            # 读取现有配置
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 应用更新
            config.update(updates)
            config["updated_at"] = self._get_current_timestamp()
            
            # 保存更新后的配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Expert Stream Server 配置更新成功: {alias}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置更新失败: {e}")
            return False
    
    def get_config_templates(self) -> Dict[str, str]:
        """获取可用的配置模板列表"""
        return {
            "default": "默认配置 - 通用AI助手",
            "development": "开发配置 - 开发任务助手",
            "code_review": "代码审查配置 - 代码分析助手"
        }
    
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
            async with SimpleClient(
                self.server_script,
                alias=alias,
                config_dir=str(self.config_dir)
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
                config_dir=str(self.config_dir)
            ) as client:
                # 获取配置
                config = await client.config()
            
            logger.info(f"✅ 配置获取成功: {alias}")
            return config
            
        except Exception as e:
            logger.error(f"❌ 配置获取失败: {e}")
            return None
    
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
                "role": config.get("role", "unknown"),
                "model_name": config.get("model_name", "unknown"),
                "created_at": config.get("created_at", "unknown"),
                "updated_at": config.get("updated_at", "unknown"),
                "version": config.get("version", "unknown"),
                "has_api_key": bool(config.get("api_key", "")),
                "enable_history": config.get("enable_history", False),
                "config_file": str(config_file)
            }
            
        except Exception as e:
            logger.error(f"❌ 获取配置摘要失败: {e}")
            return None