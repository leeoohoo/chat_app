#!/usr/bin/env python3
"""
删除所有会话的脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import db

async def delete_all_sessions():
    """删除所有会话和相关消息"""
    try:
        # 初始化数据库
        await db.init_database()
        
        # 删除所有消息
        await db.execute("DELETE FROM messages")
        print("已删除所有消息")
        
        # 删除所有会话
        await db.execute("DELETE FROM sessions")
        print("已删除所有会话")
        
        # 获取剩余的会话数量进行验证
        sessions = await db.fetchall("SELECT COUNT(*) as count FROM sessions")
        messages = await db.fetchall("SELECT COUNT(*) as count FROM messages")
        
        print(f"剩余会话数量: {sessions[0]['count']}")
        print(f"剩余消息数量: {messages[0]['count']}")
        
        print("✅ 所有会话和消息已成功删除")
        
    except Exception as e:
        print(f"❌ 删除失败: {e}")
    finally:
        # 关闭数据库连接
        await db.close()

if __name__ == "__main__":
    asyncio.run(delete_all_sessions())