#!/usr/bin/env python3
"""
MCP 配置初始化器 API 测试脚本
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API 基础 URL
BASE_URL = "http://localhost:8000/api/mcp-initializers"


class McpApiTester:
    """MCP API 测试器"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_expert_stream_api(self):
        """测试 Expert Stream API"""
        logger.info("🧪 测试 Expert Stream API...")
        
        # 测试数据
        test_alias = "api_test_expert"
        test_config = {
            "alias": test_alias,
            "custom_config": {
                "log_level": "DEBUG",
                "timeout": 30
            }
        }
        
        try:
            # 1. 初始化配置
            logger.info("📝 初始化 Expert Stream 配置...")
            async with self.session.post(
                f"{BASE_URL}/expert-stream/initialize",
                json=test_config
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 初始化成功: {result['message']}")
                    logger.info(f"📁 配置路径: {result['config_path']}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 初始化失败: {response.status} - {error_text}")
                    return False
            
            # 2. 获取配置
            logger.info("📖 获取 Expert Stream 配置...")
            async with self.session.get(
                f"{BASE_URL}/expert-stream/{test_alias}"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 获取成功: {result['message']}")
                    logger.info(f"🔧 配置数据: {json.dumps(result['config_data'], indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 获取失败: {response.status} - {error_text}")
                    return False
            
            # 3. 更新配置
            logger.info("🔄 更新 Expert Stream 配置...")
            update_data = {
                "alias": test_alias,
                "config_data": {
                    "server_name": "expert_stream_server",
                    "alias": test_alias,
                    "log_level": "INFO",
                    "timeout": 60,
                    "updated_by_api": True
                }
            }
            async with self.session.put(
                f"{BASE_URL}/expert-stream/{test_alias}",
                json=update_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 更新成功: {result['message']}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 更新失败: {response.status} - {error_text}")
                    return False
            
            # 4. 删除配置
            logger.info("🗑️ 删除 Expert Stream 配置...")
            async with self.session.delete(
                f"{BASE_URL}/expert-stream/{test_alias}"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 删除成功: {result['message']}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 删除失败: {response.status} - {error_text}")
                    return False
            
            logger.info("🎉 Expert Stream API 测试全部通过！")
            return True
            
        except Exception as e:
            logger.error(f"❌ Expert Stream API 测试异常: {e}")
            return False
    
    async def test_file_reader_api(self):
        """测试 File Reader API"""
        logger.info("🧪 测试 File Reader API...")
        
        # 测试数据
        test_alias = "api_test_file_reader"
        test_config = {
            "alias": test_alias,
            "project_root": "/Users/lilei/project",
            "custom_config": {
                "log_level": "DEBUG",
                "max_file_size": 2097152
            }
        }
        
        try:
            # 1. 初始化配置
            logger.info("📝 初始化 File Reader 配置...")
            async with self.session.post(
                f"{BASE_URL}/file-reader/initialize",
                json=test_config
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 初始化成功: {result['message']}")
                    logger.info(f"📁 配置路径: {result['config_path']}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 初始化失败: {response.status} - {error_text}")
                    return False
            
            # 2. 获取配置
            logger.info("📖 获取 File Reader 配置...")
            async with self.session.get(
                f"{BASE_URL}/file-reader/{test_alias}"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 获取成功: {result['message']}")
                    logger.info(f"🔧 配置数据: {json.dumps(result['config_data'], indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 获取失败: {response.status} - {error_text}")
                    return False
            
            # 3. 更新配置
            logger.info("🔄 更新 File Reader 配置...")
            update_data = {
                "alias": test_alias,
                "config_data": {
                    "server_name": "File Reader MCP Server",
                    "alias": test_alias,
                    "log_level": "INFO",
                    "timeout": 30,
                    "project_root": "/Users/lilei/project",
                    "max_file_size": 1048576,
                    "updated_by_api": True
                }
            }
            async with self.session.put(
                f"{BASE_URL}/file-reader/{test_alias}",
                json=update_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 更新成功: {result['message']}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 更新失败: {response.status} - {error_text}")
                    return False
            
            # 4. 删除配置
            logger.info("🗑️ 删除 File Reader 配置...")
            async with self.session.delete(
                f"{BASE_URL}/file-reader/{test_alias}"
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 删除成功: {result['message']}")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 删除失败: {response.status} - {error_text}")
                    return False
            
            logger.info("🎉 File Reader API 测试全部通过！")
            return True
            
        except Exception as e:
            logger.error(f"❌ File Reader API 测试异常: {e}")
            return False
    
    async def test_list_configs_api(self):
        """测试配置列表 API"""
        logger.info("🧪 测试配置列表 API...")
        
        try:
            async with self.session.get(f"{BASE_URL}/list") as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ 获取配置列表成功")
                    logger.info(f"📊 配置总数: {result['total']}")
                    for config in result['configs']:
                        logger.info(f"  📄 {config['file_name']} - {config['type']} - {config['alias']}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ 获取配置列表失败: {response.status} - {error_text}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ 配置列表 API 测试异常: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始 MCP 配置初始化器 API 测试...")
        
        results = []
        
        # 测试配置列表
        results.append(await self.test_list_configs_api())
        
        # 测试 Expert Stream API
        results.append(await self.test_expert_stream_api())
        
        # 测试 File Reader API
        results.append(await self.test_file_reader_api())
        
        # 再次测试配置列表
        results.append(await self.test_list_configs_api())
        
        # 总结结果
        passed = sum(results)
        total = len(results)
        
        logger.info("=" * 60)
        if passed == total:
            logger.info(f"🎊 所有测试都通过了！({passed}/{total})")
        else:
            logger.error(f"❌ 有 {total - passed} 个测试失败 ({passed}/{total})")
        
        return passed == total


async def main():
    """主函数"""
    async with McpApiTester() as tester:
        success = await tester.run_all_tests()
        return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)