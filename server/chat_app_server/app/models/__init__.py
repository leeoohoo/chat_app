#!/usr/bin/env python3
"""
数据模型包
"""
import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class DatabaseManager:
    """数据库管理器（保留用于向后兼容）"""
    
    def __init__(self, db_path: str = "data/chat_app.db"):
        """初始化数据库管理器"""
        self.db_path = db_path
        self.ensure_data_directory()
        self.initialize_database()
    
    def ensure_data_directory(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return conn
    
    def initialize_database(self):
        """初始化数据库，创建表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            # 创建MCP配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mcp_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    config_data TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建AI模型配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_model_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    model_type TEXT NOT NULL,
                    api_key TEXT,
                    base_url TEXT,
                    model_name TEXT NOT NULL,
                    max_tokens INTEGER,
                    temperature REAL,
                    config_data TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建系统上下文表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    context_data TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建会话MCP服务器关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_mcp_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    mcp_server_name TEXT NOT NULL,
                    config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            
            # 执行数据库迁移
            self.migrate_database(cursor)
    
    def migrate_database(self, cursor):
        """执行数据库迁移"""
        # 检查是否需要添加新列或修改表结构
        # 这里可以添加版本控制和迁移逻辑
        pass
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行查询"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """获取所有结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """获取单个结果"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def close(self):
        """关闭数据库连接（SQLite不需要显式关闭）"""
        pass


# 全局数据库实例（保留用于向后兼容）
db_manager = DatabaseManager()


# 导入数据库抽象层
from .database_config import DatabaseConfig, DatabaseType
from .database_interface import AbstractDatabaseAdapter
from .database_factory import get_database, get_database_config, database_factory

# 导出模型类
from .config import McpConfigCreate, AiModelConfigCreate, SystemContextCreate
from .message import MessageCreate
from .session import SessionCreate, SessionMcpServerCreate

# 导出数据库相关类和函数
__all__ = [
    # 传统数据库管理器（向后兼容）
    'DatabaseManager',
    'db_manager',
    
    # 新的数据库抽象层
    'DatabaseConfig',
    'DatabaseType', 
    'AbstractDatabaseAdapter',
    'get_database',
    'get_database_config',
    'database_factory',
    
    # 模型类
    'McpConfigCreate',
    'AiModelConfigCreate',
    'SystemContextCreate',
    'MessageCreate',
    'SessionCreate',
    'SessionMcpServerCreate',
]