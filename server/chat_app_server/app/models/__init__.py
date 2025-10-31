# 数据模型模块
# 包含数据库连接管理和所有数据模型

import aiosqlite
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 使用项目根目录的数据库文件
            project_root = Path(__file__).parent.parent.parent
            self.db_path = str(project_root / "chat_app.db")
        else:
            self.db_path = db_path
        self.connection = None

    async def init_database(self):
        """初始化数据库连接和表结构"""
        try:
            # 创建数据库目录
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            self.connection = await aiosqlite.connect(self.db_path)
            
            # 设置row_factory以返回Row对象
            self.connection.row_factory = aiosqlite.Row
            
            # 创建表结构
            await self._create_tables()
            
            # 检查并添加新字段（如果不存在）
            await self._migrate_tables()
            
            logger.info('数据库初始化成功')
        except Exception as error:
            logger.error(f'数据库初始化失败: {error}')
            raise

    async def _create_tables(self):
        """创建所有必需的表"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            user_id TEXT,
            project_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            tool_calls TEXT,
            tool_call_id TEXT,
            reasoning TEXT,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS mcp_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            type TEXT DEFAULT 'stdio',
            args TEXT,
            env TEXT,
            user_id TEXT,
            enabled BOOLEAN DEFAULT true,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS ai_model_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            api_key TEXT,
            base_url TEXT,
            user_id TEXT,
            enabled BOOLEAN DEFAULT true,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS session_mcp_servers (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            mcp_config_id TEXT NOT NULL,
            enabled BOOLEAN DEFAULT true,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs (id) ON DELETE CASCADE,
            UNIQUE(session_id, mcp_config_id)
        );
        
        CREATE TABLE IF NOT EXISTS system_contexts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            content TEXT,
            user_id TEXT,
            is_active BOOLEAN DEFAULT false,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        await self.connection.executescript(create_tables_sql)
        await self.connection.commit()

    async def _migrate_tables(self):
        """检查并添加新字段（如果不存在）"""
        try:
            # 检查 sessions 表字段
            cursor = await self.connection.execute("PRAGMA table_info(sessions)")
            sessions_columns = await cursor.fetchall()
            column_names = [col[1] for col in sessions_columns]
            
            if 'user_id' not in column_names:
                await self.connection.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
                logger.info('已为sessions表添加user_id字段')
            
            if 'project_id' not in column_names:
                await self.connection.execute("ALTER TABLE sessions ADD COLUMN project_id TEXT")
                logger.info('已为sessions表添加project_id字段')
            
            await self.connection.commit()
            
        except Exception as error:
            logger.info(f'字段迁移处理: {error}')

    async def close(self):
        """关闭数据库连接"""
        if self.connection:
            await self.connection.close()

    async def execute(self, query: str, params: tuple = None):
        """执行SQL查询"""
        if params is None:
            params = ()
        cursor = await self.connection.execute(query, params)
        await self.connection.commit()
        return cursor

    async def fetchone(self, query: str, params: tuple = None):
        """获取单行数据"""
        if params is None:
            params = ()
        cursor = await self.connection.execute(query, params)
        return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = None):
        """获取所有数据"""
        if params is None:
            params = ()
        cursor = await self.connection.execute(query, params)
        return await cursor.fetchall()

    def execute_sync(self, query: str, params: tuple = None):
        """同步执行SQL语句"""
        if params is None:
            params = ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor

    def fetchone_sync(self, query: str, params: tuple = None):
        """同步获取单行数据"""
        if params is None:
            params = ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def fetchall_sync(self, query: str, params: tuple = None):
        """同步获取所有数据"""
        if params is None:
            params = ()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            cursor = conn.execute(query, params)
            return cursor.fetchall()

# 全局数据库管理器实例
db = DatabaseManager()

# 导出列表
__all__ = ['db', 'DatabaseManager']