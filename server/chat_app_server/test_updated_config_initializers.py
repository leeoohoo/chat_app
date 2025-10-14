#!/usr/bin/env python3
"""
测试更新后的配置初始化器
验证 ExpertStreamConfigInitializer 和 FileReaderConfigInitializer 使用 SimpleClient 的功能
"""

import asyncio
import logging
import os
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入配置初始化器
from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer
from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer


class UpdatedConfigInitializersTest:
    """测试更新后的配置初始化器"""
    
    def __init__(self):
        """初始化测试环境"""
        self.config_dir = "/Users/lilei/project/config/test_updated_config"
        # 设置服务器脚本路径 (使用编译后的可执行文件)
        self.expert_stream_script = "/Users/lilei/project/learn/chat_app/server/chat_app_server/mcp_services/expert-stream-server-macos-arm64/expert-stream-server"
        self.file_reader_script = "/Users/lilei/project/learn/chat_app/server/chat_app_server/mcp_services/file-reader-server-macos-arm64/file-reader-server"
        
        # 确保配置目录存在
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
        # 初始化配置器
        self.expert_stream_initializer = ExpertStreamConfigInitializer(
            config_dir=self.config_dir,
            server_script=self.expert_stream_script
        )
        
        self.file_reader_initializer = FileReaderConfigInitializer(
            config_dir=self.config_dir,
            server_script=self.file_reader_script
        )
    
    async def test_expert_stream_config(self):
        """测试 ExpertStreamConfigInitializer"""
        logger.info("🧪 测试 ExpertStreamConfigInitializer...")
        
        # 测试创建配置
        alias = "test_expert_assistant"
        custom_config = {
            "api_key": "test-api-key-123",
            "model_name": "gpt-4",
            "system_prompt": "你是一个测试助手",
            "custom_setting": "test_value"
        }
        
        success = await self.expert_stream_initializer.initialize_config(
            alias=alias,
            config_template="default",
            custom_config=custom_config
        )
        
        if success:
            logger.info(f"✅ ExpertStreamConfigInitializer 配置创建成功: {alias}")
            
            # 测试获取配置
            config = await self.expert_stream_initializer.get_config(alias)
            if config:
                logger.info(f"✅ 配置获取成功，角色: {config.get('role')}")
                logger.info(f"   模型: {config.get('model_name')}")
                logger.info(f"   自定义设置: {config.get('custom_setting')}")
            
            # 测试更新配置
            updates = {
                "model_name": "gpt-4-turbo",
                "custom_setting": "updated_value"
            }
            update_success = await self.expert_stream_initializer.update_config(alias, updates)
            if update_success:
                logger.info("✅ 配置更新成功")
                
                # 验证更新
                updated_config = await self.expert_stream_initializer.get_config(alias)
                if updated_config:
                    logger.info(f"   更新后模型: {updated_config.get('model_name')}")
                    logger.info(f"   更新后自定义设置: {updated_config.get('custom_setting')}")
        else:
            logger.error("❌ ExpertStreamConfigInitializer 配置创建失败")
    
    async def test_file_reader_config(self):
        """测试 FileReaderConfigInitializer"""
        logger.info("🧪 测试 FileReaderConfigInitializer...")
        
        # 测试创建配置
        alias = "test_file_reader"
        project_root = "/Users/lilei/project/learn/chat_app"
        custom_config = {
            "max_file_size": 20,
            "enable_hidden_files": True,
            "custom_setting": "file_reader_test"
        }
        
        success = await self.file_reader_initializer.initialize_config(
            alias=alias,
            config_template="development",
            project_root=project_root,
            custom_config=custom_config
        )
        
        if success:
            logger.info(f"✅ FileReaderConfigInitializer 配置创建成功: {alias}")
            
            # 测试获取配置
            config = await self.file_reader_initializer.get_config(alias)
            if config:
                logger.info(f"✅ 配置获取成功，角色: {config.get('role')}")
                logger.info(f"   项目根目录: {config.get('project_root')}")
                logger.info(f"   最大文件大小: {config.get('max_file_size')} MB")
                logger.info(f"   启用隐藏文件: {config.get('enable_hidden_files')}")
            
            # 测试更新配置
            updates = {
                "max_file_size": 50,
                "enable_hidden_files": False,
                "custom_setting": "updated_file_reader_value"
            }
            update_success = await self.file_reader_initializer.update_config(alias, updates)
            if update_success:
                logger.info("✅ 配置更新成功")
                
                # 验证更新
                updated_config = await self.file_reader_initializer.get_config(alias)
                if updated_config:
                    logger.info(f"   更新后最大文件大小: {updated_config.get('max_file_size')} MB")
                    logger.info(f"   更新后隐藏文件设置: {updated_config.get('enable_hidden_files')}")
                    logger.info(f"   更新后自定义设置: {updated_config.get('custom_setting')}")
        else:
            logger.error("❌ FileReaderConfigInitializer 配置创建失败")
    
    async def list_created_configs(self):
        """列出创建的配置文件"""
        logger.info("📁 列出创建的配置文件...")
        
        config_path = Path(self.config_dir)
        if config_path.exists():
            config_files = list(config_path.glob("*.json"))
            if config_files:
                logger.info(f"找到 {len(config_files)} 个配置文件:")
                for config_file in config_files:
                    logger.info(f"   📄 {config_file.name}")
            else:
                logger.info("未找到配置文件")
        else:
            logger.info("配置目录不存在")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始测试更新后的配置初始化器...")
        
        try:
            # 测试 ExpertStreamConfigInitializer
            await self.test_expert_stream_config()
            
            print("\n" + "="*50 + "\n")
            
            # 测试 FileReaderConfigInitializer
            await self.test_file_reader_config()
            
            print("\n" + "="*50 + "\n")
            
            # 列出创建的配置文件
            await self.list_created_configs()
            
            logger.info("✅ 所有测试完成")
            
        except Exception as e:
            logger.error(f"❌ 测试过程中出现错误: {e}")
            raise


async def main():
    """主函数"""
    test = UpdatedConfigInitializersTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())