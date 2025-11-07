# SQLite数据库适配器
# 包装现有的DatabaseManager，实现抽象数据库接口

import aiosqlite
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
import asyncio
import threading

from .database_interface import AbstractDatabaseAdapter, DatabaseRow, DatabaseCursor, QueryBuilder

logger = logging.getLogger(__name__)

class SQLiteAdapter(AbstractDatabaseAdapter):
    """SQLite数据库适配器"""
    
    def __init__(self, config):
        # 处理 SQLiteConfig 对象或字典
        if hasattr(config, 'db_path'):
            # SQLiteConfig 对象
            self.db_path = config.db_path
            self.timeout = config.timeout
            self.check_same_thread = config.check_same_thread
            # 为父类创建字典格式的配置
            dict_config = {
                "debug": getattr(config, 'debug', False),
                "db_path": config.db_path,
                "timeout": config.timeout,
                "check_same_thread": config.check_same_thread
            }
        else:
            # 字典格式（向后兼容）
            dict_config = config
            self.sqlite_config = config.get("config", {})
            self.db_path = self.sqlite_config.get("db_path")
            self.timeout = self.sqlite_config.get("timeout", 30.0)
            self.check_same_thread = self.sqlite_config.get("check_same_thread", False)
        
        # 调用父类构造函数，传递字典格式的配置
        super().__init__(dict_config)
        
        # 如果没有指定路径，使用默认路径
        if self.db_path is None:
            project_root = Path(__file__).parent.parent.parent
            self.db_path = str(project_root / "chat_app.db")
        
        self._connection = None
        self._sync_connection = None
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self.query_builder = QueryBuilder("sqlite")
    
    async def init_database(self) -> None:
        """初始化数据库连接和表结构"""
        try:
            # 创建数据库目录
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建异步连接
            self._connection = await aiosqlite.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=self.check_same_thread
            )
            
            # 设置row_factory以返回Row对象
            self._connection.row_factory = aiosqlite.Row
            
            # 创建同步连接（用于同步方法）
            self._sync_connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=self.check_same_thread
            )
            self._sync_connection.row_factory = sqlite3.Row
            
            # 创建表结构
            await self._create_tables()
            
            # 检查并添加新字段（如果不存在）
            if self.config.get("auto_migrate", True):
                await self._migrate_tables()
            
            logger.info(f'SQLite数据库初始化成功: {self.db_path}')
        except Exception as error:
            logger.error(f'SQLite数据库初始化失败: {error}')
            raise
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._connection:
            await self._connection.close()
            self._connection = None
        
        if self._sync_connection:
            self._sync_connection.close()
            self._sync_connection = None
    
    async def execute(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> DatabaseCursor:
        """执行SQL语句"""
        self.log_query(query, params)
        
        async with self._lock:
            if not self._connection:
                await self.init_database()
            
            # 转换参数格式
            if isinstance(params, dict):
                # 将字典参数转换为命名参数格式
                cursor = await self._connection.execute(query, params)
            else:
                cursor = await self._connection.execute(query, params or ())
            
            await self._connection.commit()
            
            return DatabaseCursor(
                rowcount=cursor.rowcount,
                lastrowid=str(cursor.lastrowid) if cursor.lastrowid else None
            )
    
    async def fetchone(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> Optional[DatabaseRow]:
        """获取单行数据"""
        self.log_query(query, params)
        
        async with self._lock:
            if not self._connection:
                await self.init_database()
            
            if isinstance(params, dict):
                cursor = await self._connection.execute(query, params)
            else:
                cursor = await self._connection.execute(query, params or ())
            
            row = await cursor.fetchone()
            await cursor.close()
            
            if row:
                # 将SQLite Row转换为DatabaseRow
                return DatabaseRow({key: row[key] for key in row.keys()})
            return None
    
    async def fetchall(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[DatabaseRow]:
        """获取所有数据"""
        self.log_query(query, params)
        
        async with self._lock:
            if not self._connection:
                await self.init_database()
            
            if isinstance(params, dict):
                cursor = await self._connection.execute(query, params)
            else:
                cursor = await self._connection.execute(query, params or ())
            
            rows = await cursor.fetchall()
            await cursor.close()
            
            # 将SQLite Row列表转换为DatabaseRow列表
            return [DatabaseRow({key: row[key] for key in row.keys()}) for row in rows]
    
    # 添加模型类需要的方法别名
    async def execute_query_async(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> DatabaseCursor:
        """执行查询的异步方法（别名）"""
        return await self.execute(query, params)
    
    def execute_query(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> DatabaseCursor:
        """执行查询的同步方法（别名）"""
        return self.execute_sync(query, params)
    
    async def fetch_all_async(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[DatabaseRow]:
        """获取所有数据的异步方法（别名）"""
        return await self.fetchall(query, params)
    
    async def fetch_one_async(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> Optional[DatabaseRow]:
        """获取单行数据的异步方法（别名）"""
        return await self.fetchone(query, params)
    
    def execute_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> DatabaseCursor:
        """同步执行SQL语句"""
        self.log_query(query, params)
        
        with self._sync_lock:
            if not self._sync_connection:
                # 同步初始化
                self._init_sync_connection()
            
            if isinstance(params, dict):
                cursor = self._sync_connection.execute(query, params)
            else:
                cursor = self._sync_connection.execute(query, params or ())
            
            self._sync_connection.commit()
            
            return DatabaseCursor(
                rowcount=cursor.rowcount,
                lastrowid=str(cursor.lastrowid) if cursor.lastrowid else None
            )
    
    def fetchone_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> Optional[DatabaseRow]:
        """同步获取单行数据"""
        self.log_query(query, params)
        
        with self._sync_lock:
            if not self._sync_connection:
                self._init_sync_connection()
            
            if isinstance(params, dict):
                cursor = self._sync_connection.execute(query, params)
            else:
                cursor = self._sync_connection.execute(query, params or ())
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return DatabaseRow({key: row[key] for key in row.keys()})
            return None
    
    def fetchall_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[DatabaseRow]:
        """同步获取所有数据"""
        self.log_query(query, params)
        
        with self._sync_lock:
            if not self._sync_connection:
                self._init_sync_connection()
            
            if isinstance(params, dict):
                cursor = self._sync_connection.execute(query, params)
            else:
                cursor = self._sync_connection.execute(query, params or ())
            
            rows = cursor.fetchall()
            cursor.close()
            
            return [DatabaseRow({key: row[key] for key in row.keys()}) for row in rows]
    
    def _init_sync_connection(self):
        """初始化同步连接"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self._sync_connection = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=self.check_same_thread
        )
        self._sync_connection.row_factory = sqlite3.Row
    
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> None:
        """创建表"""
        # 构建CREATE TABLE语句
        columns = []
        for column_name, column_def in schema.items():
            columns.append(f"{column_name} {column_def}")
        
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        await self.execute(query)
    
    async def drop_table(self, table_name: str) -> None:
        """删除表"""
        query = f"DROP TABLE IF EXISTS {table_name}"
        await self.execute(query)
    
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        row = await self.fetchone(query, (table_name,))
        return row is not None
    
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表结构"""
        query = f"PRAGMA table_info({table_name})"
        rows = await self.fetchall(query)
        
        if not rows:
            return None
        
        schema = {}
        for row in rows:
            column_name = row['name']
            column_type = row['type']
            not_null = bool(row['notnull'])
            default_value = row['dflt_value']
            primary_key = bool(row['pk'])
            
            schema[column_name] = {
                'type': column_type,
                'not_null': not_null,
                'default': default_value,
                'primary_key': primary_key
            }
        
        return schema
    
    async def begin_transaction(self) -> None:
        """开始事务"""
        await self.execute("BEGIN TRANSACTION")
    
    async def commit_transaction(self) -> None:
        """提交事务"""
        await self.execute("COMMIT")
    
    async def rollback_transaction(self) -> None:
        """回滚事务"""
        await self.execute("ROLLBACK")
    
    async def execute_many(self, query: str, params_list: List[Union[Tuple, Dict[str, Any]]]) -> DatabaseCursor:
        """批量执行"""
        self.log_query(query, f"批量执行 {len(params_list)} 条记录")
        
        async with self._lock:
            if not self._connection:
                await self.init_database()
            
            cursor = await self._connection.executemany(query, params_list)
            await self._connection.commit()
            
            return DatabaseCursor(
                rowcount=cursor.rowcount,
                lastrowid=str(cursor.lastrowid) if cursor.lastrowid else None
            )
    
    async def create_index(self, table_name: str, index_name: str, fields: List[str], unique: bool = False) -> None:
        """创建索引"""
        unique_keyword = "UNIQUE " if unique else ""
        fields_str = ", ".join(fields)
        query = f"CREATE {unique_keyword}INDEX IF NOT EXISTS {index_name} ON {table_name} ({fields_str})"
        await self.execute(query)
    
    async def drop_index(self, table_name: str, index_name: str) -> None:
        """删除索引"""
        query = f"DROP INDEX IF EXISTS {index_name}"
        await self.execute(query)
    
    async def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        # 获取数据库文件大小
        db_file = Path(self.db_path)
        file_size = db_file.stat().st_size if db_file.exists() else 0
        
        # 获取表列表
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        table_rows = await self.fetchall(tables_query)
        tables = [row['name'] for row in table_rows]
        
        # 获取SQLite版本
        version_query = "SELECT sqlite_version()"
        version_row = await self.fetchone(version_query)
        sqlite_version = version_row['sqlite_version()'] if version_row else "unknown"
        
        return {
            "type": "sqlite",
            "database_path": self.db_path,
            "file_size_bytes": file_size,
            "sqlite_version": sqlite_version,
            "tables": tables,
            "table_count": len(tables)
        }
    
    async def _create_tables(self):
        """创建所有必需的表"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            metadata TEXT,
            user_id TEXT,
            project_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS mcp_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            type TEXT DEFAULT 'stdio',
            args TEXT,
            env TEXT,
            cwd TEXT,
            user_id TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ai_model_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            api_key TEXT,
            base_url TEXT,
            user_id TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_contexts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            content TEXT,
            user_id TEXT,
            is_active BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS session_mcp_servers (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            mcp_config_id TEXT NOT NULL,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs (id) ON DELETE CASCADE
        );

        -- 每个 MCP 配置可拥有多个配置档案（profiles），仅允许一个启用
        CREATE TABLE IF NOT EXISTS mcp_config_profiles (
            id TEXT PRIMARY KEY,
            mcp_config_id TEXT NOT NULL,
            name TEXT NOT NULL,
            args TEXT,
            env TEXT,
            cwd TEXT,
            enabled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs (id) ON DELETE CASCADE
        );

        -- 约束：同一 mcp_config 仅允许一个 enabled=1 的配置档案
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mcp_config_profiles_active
        ON mcp_config_profiles (mcp_config_id)
        WHERE enabled = 1;

        -- 智能体（Agent）配置表
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            ai_model_config_id TEXT NOT NULL,
            mcp_config_ids TEXT, -- 存储为JSON数组字符串
            callable_agent_ids TEXT, -- 可调用的其他智能体ID列表(JSON数组)
            system_context_id TEXT,
            user_id TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ai_model_config_id) REFERENCES ai_model_configs (id) ON DELETE SET NULL,
            FOREIGN KEY (system_context_id) REFERENCES system_contexts (id) ON DELETE SET NULL
        );
        """
        
        # 分割并执行每个CREATE TABLE语句
        statements = [stmt.strip() for stmt in create_tables_sql.split(';') if stmt.strip()]
        for statement in statements:
            await self.execute(statement)
    
    async def _migrate_tables(self):
        """检查并添加新字段（如果不存在）"""
        migrations = [
            # 为sessions表添加project_id字段（如果不存在）
            {
                'table': 'sessions',
                'column': 'project_id',
                'definition': 'TEXT'
            },
            # 为messages表添加status字段（如果不存在）
            {
                'table': 'messages',
                'column': 'status',
                'definition': 'TEXT DEFAULT "completed"'
            },
            # 为messages表添加reasoning字段（如果不存在）
            {
                'table': 'messages',
                'column': 'reasoning',
                'definition': 'TEXT'
            },
            # 为mcp_configs添加cwd字段（如果不存在）
            {
                'table': 'mcp_configs',
                'column': 'cwd',
                'definition': 'TEXT'
            },
            # 为agents添加callable_agent_ids字段（如果不存在）
            {
                'table': 'agents',
                'column': 'callable_agent_ids',
                'definition': 'TEXT'
            }
        ]
        
        for migration in migrations:
            try:
                # 检查字段是否存在
                schema = await self.get_table_schema(migration['table'])
                if schema and migration['column'] not in schema:
                    # 添加字段
                    alter_query = f"ALTER TABLE {migration['table']} ADD COLUMN {migration['column']} {migration['definition']}"
                    await self.execute(alter_query)
                    logger.info(f"添加字段 {migration['table']}.{migration['column']}")
            except Exception as e:
                logger.warning(f"迁移字段 {migration['table']}.{migration['column']} 失败: {e}")