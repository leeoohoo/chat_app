#!/usr/bin/env python3
"""
修复现有配置中空的 user_id
"""

import sqlite3

# 默认的 user_id，用于修复现有的空值
DEFAULT_USER_ID = "default-user"

def fix_existing_user_ids():
    """修复现有配置中空的 user_id"""
    
    print("🔧 开始修复现有配置的空 user_id...")
    
    try:
        # 连接数据库
        conn = sqlite3.connect('chat_app.db')
        cursor = conn.cursor()
        
        # 1. 修复 MCP 配置
        print("\n1. 修复 MCP 配置...")
        cursor.execute("SELECT id, name, user_id FROM mcp_configs WHERE user_id IS NULL OR user_id = ''")
        empty_mcp_configs = cursor.fetchall()
        
        if empty_mcp_configs:
            print(f"发现 {len(empty_mcp_configs)} 个 MCP 配置的 user_id 为空")
            for config in empty_mcp_configs:
                config_id, name, user_id = config
                print(f"  - 修复配置: {name} (ID: {config_id})")
                cursor.execute("UPDATE mcp_configs SET user_id = ? WHERE id = ?", (DEFAULT_USER_ID, config_id))
            
            print(f"✅ 已将 {len(empty_mcp_configs)} 个 MCP 配置的 user_id 设置为: {DEFAULT_USER_ID}")
        else:
            print("✅ 所有 MCP 配置的 user_id 都已设置")
        
        # 2. 修复 AI 模型配置
        print("\n2. 修复 AI 模型配置...")
        cursor.execute("SELECT id, name, user_id FROM ai_model_configs WHERE user_id IS NULL OR user_id = ''")
        empty_ai_configs = cursor.fetchall()
        
        if empty_ai_configs:
            print(f"发现 {len(empty_ai_configs)} 个 AI 模型配置的 user_id 为空")
            for config in empty_ai_configs:
                config_id, name, user_id = config
                print(f"  - 修复配置: {name} (ID: {config_id})")
                cursor.execute("UPDATE ai_model_configs SET user_id = ? WHERE id = ?", (DEFAULT_USER_ID, config_id))
            
            print(f"✅ 已将 {len(empty_ai_configs)} 个 AI 模型配置的 user_id 设置为: {DEFAULT_USER_ID}")
        else:
            print("✅ 所有 AI 模型配置的 user_id 都已设置")
        
        # 3. 修复系统上下文配置
        print("\n3. 修复系统上下文配置...")
        cursor.execute("SELECT id, name, user_id FROM system_contexts WHERE user_id IS NULL OR user_id = ''")
        empty_context_configs = cursor.fetchall()
        
        if empty_context_configs:
            print(f"发现 {len(empty_context_configs)} 个系统上下文配置的 user_id 为空")
            for config in empty_context_configs:
                config_id, name, user_id = config
                print(f"  - 修复配置: {name} (ID: {config_id})")
                cursor.execute("UPDATE system_contexts SET user_id = ? WHERE id = ?", (DEFAULT_USER_ID, config_id))
            
            print(f"✅ 已将 {len(empty_context_configs)} 个系统上下文配置的 user_id 设置为: {DEFAULT_USER_ID}")
        else:
            print("✅ 所有系统上下文配置的 user_id 都已设置")
        
        # 提交更改
        conn.commit()
        
        # 4. 验证修复结果
        print("\n4. 验证修复结果...")
        
        # 检查 MCP 配置
        cursor.execute("SELECT COUNT(*) FROM mcp_configs WHERE user_id IS NULL OR user_id = ''")
        empty_mcp_count = cursor.fetchone()[0]
        print(f"MCP 配置中 user_id 为空的数量: {empty_mcp_count}")
        
        # 检查 AI 模型配置
        cursor.execute("SELECT COUNT(*) FROM ai_model_configs WHERE user_id IS NULL OR user_id = ''")
        empty_ai_count = cursor.fetchone()[0]
        print(f"AI 模型配置中 user_id 为空的数量: {empty_ai_count}")
        
        # 检查系统上下文配置
        cursor.execute("SELECT COUNT(*) FROM system_contexts WHERE user_id IS NULL OR user_id = ''")
        empty_context_count = cursor.fetchone()[0]
        print(f"系统上下文配置中 user_id 为空的数量: {empty_context_count}")
        
        if empty_mcp_count == 0 and empty_ai_count == 0 and empty_context_count == 0:
            print("🎉 所有配置的 user_id 都已正确设置！")
        else:
            print("⚠️ 仍有配置的 user_id 为空，请检查")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    fix_existing_user_ids()