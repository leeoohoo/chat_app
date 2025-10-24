#!/usr/bin/env python3
"""
测试v2目录中更新后的实现
验证所有组件是否正确使用models中的数据库操作方法
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.v2 import (
    MessageManager,
    AiRequestHandler, 
    ToolResultProcessor,
    McpToolExecute,
    AiClient,
    AiServer,
    ChatService
)
from app.models import DatabaseManager
from app.mcp_manager import McpManager

def test_message_manager():
    """测试MessageManager"""
    print("🧪 测试 MessageManager...")
    
    try:
        # 初始化MessageManager
        message_manager = MessageManager()
        
        # 测试保存用户消息
        user_message = message_manager.save_user_message(
            session_id="test_session_1",
            content="Hello, this is a test message"
        )
        print(f"✅ 用户消息保存成功: {user_message.get('id')}")
        
        # 测试保存助手消息
        assistant_message = message_manager.save_assistant_message(
            session_id="test_session_1",
            content="Hello! How can I help you today?",
            metadata={"model": "gpt-4"}
        )
        print(f"✅ 助手消息保存成功: {assistant_message.get('id')}")
        
        # 测试保存工具消息
        tool_message = message_manager.save_tool_message(
            session_id="test_session_1",
            content="Tool execution result",
            tool_call_id="call_123",
            metadata={"toolName": "test_tool", "toolCallId": "call_123"}
        )
        print(f"✅ 工具消息保存成功: {tool_message.get('id')}")
        
        # 测试获取会话消息
        messages = message_manager.get_session_messages("test_session_1")
        print(f"✅ 获取会话消息成功，共 {len(messages)} 条消息")
        
        # 测试缓存统计
        cache_stats = message_manager.get_stats()
        print(f"✅ 缓存统计: {cache_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ MessageManager 测试失败: {str(e)}")
        return False

def test_database_operations():
    """测试数据库操作"""
    print("\n🧪 测试数据库操作...")
    
    try:
        # 测试数据库连接
        db = DatabaseManager()
        
        # 测试同步查询
        result = db.fetchall_sync("SELECT COUNT(*) as count FROM messages")
        print(f"✅ 数据库查询成功，消息总数: {result[0]['count'] if result else 0}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库操作测试失败: {str(e)}")
        return False

def test_chat_service_integration():
    """测试ChatService集成"""
    print("\n🧪 测试 ChatService 集成...")
    
    try:
        # 检查环境变量
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("⚠️  警告: 未设置 OPENAI_API_KEY，跳过 ChatService 测试")
            return True
        
        # 初始化MCP管理器
        mcp_manager = McpManager()
        
        # 初始化ChatService
        chat_service = ChatService(
            openai_api_key=openai_api_key,
            mcp_client=mcp_manager,
            default_model="gpt-3.5-turbo",
            default_temperature=0.7
        )
        
        # 测试服务状态
        status = chat_service.get_service_status()
        print(f"✅ ChatService 状态: {status.get('status')}")
        
        # 测试健康检查
        health = chat_service.health_check()
        print(f"✅ 健康检查: {health.get('status')}")
        
        # 测试创建会话
        session_result = chat_service.create_session(
            session_id="test_integration_session",
            config={"model": "gpt-3.5-turbo", "temperature": 0.5}
        )
        print(f"✅ 会话创建: {session_result.get('success')}")
        
        # 测试获取可用工具
        tools = chat_service.get_available_tools()
        print(f"✅ 可用工具数量: {len(tools.get('tools', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ ChatService 集成测试失败: {str(e)}")
        return False

def test_imports():
    """测试所有模块导入"""
    print("\n🧪 测试模块导入...")
    
    try:
        # 测试v2模块导入
        from app.services.v2 import (
            MessageManager,
            AiRequestHandler,
            ToolResultProcessor, 
            McpToolExecute,
            AiClient,
            AiServer,
            ChatService
        )
        print("✅ v2 模块导入成功")
        
        # 测试models模块导入
        from app.models.message import MessageCreate
        from app.models.session import SessionCreate
        from app.models import DatabaseManager
        print("✅ models 模块导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 模块导入测试失败: {str(e)}")
        return False

def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    
    try:
        from app.models.message import MessageCreate
        from app.models.session import SessionCreate
        
        # 删除测试会话的消息
        MessageCreate.delete_by_session_sync("test_session_1")
        MessageCreate.delete_by_session_sync("test_integration_session")
        
        # 删除测试会话
        SessionCreate.delete_sync("test_session_1")
        SessionCreate.delete_sync("test_integration_session")
        
        print("✅ 测试数据清理完成")
        return True
        
    except Exception as e:
        print(f"⚠️  测试数据清理失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试 v2 实现...")
    print("=" * 50)
    
    test_results = []
    
    # 运行所有测试
    test_results.append(("模块导入", test_imports()))
    test_results.append(("数据库操作", test_database_operations()))
    test_results.append(("MessageManager", test_message_manager()))
    test_results.append(("ChatService集成", test_chat_service_integration()))
    
    # 清理测试数据
    cleanup_test_data()
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！v2 实现更新成功！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)