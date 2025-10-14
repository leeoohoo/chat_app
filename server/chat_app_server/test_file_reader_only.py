#!/usr/bin/env python3
"""
测试更新后的 FileReaderConfigInitializer
"""

import asyncio
import logging
import os
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入配置初始化器
from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer


class TestFileReaderConfig:
    """测试 FileReaderConfigInitializer"""
    
    def __init__(self):
        """初始化测试环境"""
        self.config_dir = "/Users/lilei/project/config/test_file_reader_only"
        # 设置服务器脚本路径 (使用编译后的可执行文件)
        self.file_reader_script = "/Users/lilei/project/learn/chat_app/server/chat_app_server/mcp_services/file-reader-server-macos-arm64/file-reader-server"
        
        # 确保配置目录存在
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
        
    async def test_file_reader_config(self):
        """测试 FileReaderConfigInitializer"""
        logger.info("🧪 测试 FileReaderConfigInitializer...")
        
        try:
            # 创建配置初始化器，增加超时时间
            initializer = FileReaderConfigInitializer(
                server_script=self.file_reader_script,
                config_dir=self.config_dir
            )
            
            # 测试配置创建
            alias = "test_file_reader"
            logger.info(f"开始创建配置: {alias}")
            
            # 使用更长的超时时间
            config = await asyncio.wait_for(
                initializer.initialize_config(alias=alias, config_template="default"),
                timeout=60.0  # 60秒超时
            )
            
            if config:
                logger.info(f"✅ FileReaderConfigInitializer 配置创建成功: {alias}")
                
                # 测试配置获取
                logger.info("测试配置获取...")
                retrieved_config = await asyncio.wait_for(
                    initializer.get_config(alias),
                    timeout=30.0
                )
                if retrieved_config:
                    logger.info("✅ 配置获取成功")
                else:
                    logger.error("❌ 配置获取失败")
                
                # 测试配置更新
                logger.info("测试配置更新...")
                update_data = {"model_name": "gpt-4-turbo"}
                await asyncio.wait_for(
                    initializer.update_config(alias, update_data),
                    timeout=30.0
                )
                logger.info("✅ 配置更新成功")
                
                # 再次获取配置验证更新
                logger.info("验证配置更新...")
                updated_config = await asyncio.wait_for(
                    initializer.get_config(alias),
                    timeout=30.0
                )
                if updated_config and updated_config.get("model_name") == "gpt-4-turbo":
                    logger.info("✅ 配置更新验证成功")
                else:
                    logger.error("❌ 配置更新验证失败")
                    
            else:
                logger.error("❌ FileReaderConfigInitializer 配置创建失败")
                
        except asyncio.TimeoutError:
            logger.error("❌ FileReaderConfigInitializer 测试超时")
        except Exception as e:
            logger.error(f"❌ FileReaderConfigInitializer 测试失败: {e}")
            
    def list_config_files(self):
        """列出创建的配置文件"""
        logger.info("📁 列出创建的配置文件...")
        config_path = Path(self.config_dir)
        
        if config_path.exists():
            config_files = list(config_path.glob("*.json"))
            if config_files:
                logger.info(f"找到 {len(config_files)} 个配置文件:")
                for file in config_files:
                    logger.info(f"   📄 {file.name}")
            else:
                logger.info("未找到配置文件")
        else:
            logger.info("配置目录不存在")
            
    async def run_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始测试 FileReaderConfigInitializer...")
        
        await self.test_file_reader_config()
        
        print("=" * 50)
        self.list_config_files()
        logger.info("✅ 测试完成")


async def main():
    """主函数"""
    tester = TestFileReaderConfig()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())