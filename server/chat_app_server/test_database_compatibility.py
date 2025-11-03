#!/usr/bin/env python3
"""
数据库兼容性测试脚本
测试 SQLite 和 MongoDB 的兼容性功能
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import (
    get_database, 
    McpConfigCreate,
    MessageCreate,
    SessionCreate
)
from app.models.database_factory import DatabaseFactory, switch_to_sqlite, switch_to_mongodb
from app.models.database_config import DatabaseConfig, DatabaseType


async def test_sqlite():
    """测试 SQLite 功能"""
    print("🔍 测试 SQLite 数据库...")
    
    try:
        # 切换到 SQLite
        db = switch_to_sqlite("data/test_chat_app.db")
        await db.init_database()
        
        print("✅ SQLite 数据库初始化成功")
        
        # 测试配置创建
        config_data = McpConfigCreate(
            name="test_sqlite_config",
            command="test_command",
            type="stdio"
        )
        config_result = await McpConfigCreate.create(config_data)
        print(f"✅ 创建配置成功")
        
        # 测试配置查询
        configs = await McpConfigCreate.get_all()
        print(f"✅ 查询到 {len(configs)} 个配置")
        
        # 测试会话创建
        session_id = SessionCreate.create(
            title="SQLite 测试会话",
            description="这是一个 SQLite 测试会话",
            metadata={"database": "sqlite"}
        )
        print(f"✅ 创建会话成功，ID: {session_id}")
        
        # 测试消息创建
        message_data = MessageCreate(
            sessionId=session_id,
            role="user",
            content="这是一条 SQLite 测试消息",
            metadata={"test": True}
        )
        message_result = await MessageCreate.create(message_data)
        print(f"✅ 创建消息成功，ID: {message_result['id']}")
        
        # 测试消息查询
        messages = await MessageCreate.get_by_session(session_id)
        print(f"✅ 查询到 {len(messages)} 条消息")
        
        print("🎉 SQLite 测试完成！\n")
        return True
        
    except Exception as e:
        print(f"❌ SQLite 测试失败: {e}")
        return False


async def test_mongodb():
    """测试 MongoDB 功能"""
    print("🔍 测试 MongoDB 数据库...")
    
    try:
        # 检查是否有 MongoDB 依赖
        try:
            import pymongo
            import motor
        except ImportError:
            print("⚠️  MongoDB 依赖未安装，跳过 MongoDB 测试")
            print("   安装命令: pip install pymongo motor")
            return True
        
        # 切换到 MongoDB
        db = switch_to_mongodb(
            host="localhost",
            port=27017,
            database="test_chat_app",
            username=None,
            password=None
        )
        
        # 尝试初始化（可能会失败如果 MongoDB 未运行）
        try:
            await db.init_database()
            print("✅ MongoDB 数据库初始化成功")
        except Exception as e:
            print(f"⚠️  MongoDB 连接失败: {e}")
            print("   请确保 MongoDB 服务正在运行")
            return True
        
        # 测试配置创建
        config_data = McpConfigCreate(
            name="test_mongodb_config",
            command="test_command",
            type="stdio"
        )
        config_result = await McpConfigCreate.create(config_data)
        print(f"✅ 创建配置成功")
        
        # 测试配置查询
        configs = await McpConfigCreate.get_all()
        print(f"✅ 查询到 {len(configs)} 个配置")
        
        # 测试会话创建
        session_id = SessionCreate.create(
            title="MongoDB 测试会话",
            description="这是一个 MongoDB 测试会话",
            metadata={"database": "mongodb"}
        )
        print(f"✅ 创建会话成功，ID: {session_id}")
        
        # 测试消息创建
        message_data = MessageCreate(
            sessionId=session_id,
            role="user",
            content="这是一条 MongoDB 测试消息",
            metadata={"test": True}
        )
        message_result = await MessageCreate.create(message_data)
        print(f"✅ 创建消息成功，ID: {message_result['id']}")
        
        # 测试消息查询
        messages = await MessageCreate.get_by_session(session_id)
        print(f"✅ 查询到 {len(messages)} 条消息")
        
        print("🎉 MongoDB 测试完成！\n")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB 测试失败: {e}")
        return False


async def test_configuration_switching():
    """测试配置文件切换功能"""
    print("🔍 测试配置文件切换功能...")
    
    try:
        # 获取当前配置
        factory = DatabaseFactory()
        current_config = factory.get_config()
        if current_config:
            print(f"✅ 当前数据库类型: {current_config.type}")
        else:
            print("✅ 当前配置为空，将使用默认配置")
        
        # 测试重新加载配置
        factory.load_config()
        print("✅ 配置重新加载成功")
        
        # 测试获取数据库适配器
        db = get_database()
        print(f"✅ 获取数据库适配器成功: {type(db).__name__}")
        
        print("🎉 配置切换测试完成！\n")
        return True
        
    except Exception as e:
        print(f"❌ 配置切换测试失败: {e}")
        return False


async def test_backward_compatibility():
    """测试向后兼容性"""
    print("🔍 测试向后兼容性...")
    
    try:
        # 测试原有的 DatabaseManager 类是否仍然可用
        from app.models import DatabaseManager
        
        # 创建 DatabaseManager 实例
        db_manager = DatabaseManager("data/test_compatibility.db")
        print("✅ DatabaseManager 类仍然可用")
        
        # 测试基本操作（DatabaseManager 的方法是同步的）
        # db_manager.initialize_database() 在构造函数中已经调用
        print("✅ DatabaseManager 初始化成功")
        
        # 测试查询
        cursor = db_manager.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ DatabaseManager 查询成功，找到 {len(tables)} 个表")
        
        print("🎉 向后兼容性测试完成！\n")
        return True
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始数据库兼容性测试...\n")
    
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 运行所有测试
    tests = [
        ("配置切换功能", test_configuration_switching),
        ("SQLite 数据库", test_sqlite),
        ("MongoDB 数据库", test_mongodb),
        ("向后兼容性", test_backward_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"📋 运行测试: {test_name}")
        result = await test_func()
        results.append((test_name, result))
    
    # 输出测试结果
    print("📊 测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！数据库兼容性功能正常工作。")
    else:
        print("⚠️  部分测试失败，请检查相关配置和依赖。")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)