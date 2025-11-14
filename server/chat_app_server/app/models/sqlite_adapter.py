# SQLite数据库适配器
# 包装现有的DatabaseManager，实现抽象数据库接口

import aiosqlite
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
import asyncio
import threading
import time

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
        
        # 统一路径解析：缺省或相对路径都基于项目根目录
        project_root = Path(__file__).parent.parent.parent
        if self.db_path is None:
            # 默认放到 data 目录
            self.db_path = str(project_root / "data/chat_app.db")
        else:
            db_path_obj = Path(self.db_path)
            if not db_path_obj.is_absolute():
                self.db_path = str(project_root / db_path_obj)
        
        self._connection = None
        self._sync_connection = None
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        # 全局写入锁：跨异步/同步连接统一串行化写操作，避免database is locked
        self._global_write_lock = threading.RLock()
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

            # 应用性能与并发相关 PRAGMA（异步连接）
            try:
                await self._connection.execute("PRAGMA journal_mode=WAL;")
                await self._connection.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)};")
                await self._connection.execute("PRAGMA synchronous=NORMAL;")
                await self._connection.execute("PRAGMA foreign_keys=ON;")
                await self._connection.commit()
            except Exception as e:
                logger.warning(f"设置异步连接 PRAGMA 失败: {e}")
            
            # 创建同步连接（用于同步方法）
            self._sync_connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=self.check_same_thread
            )
            self._sync_connection.row_factory = sqlite3.Row

            # 应用性能与并发相关 PRAGMA（同步连接）
            try:
                self._sync_connection.execute("PRAGMA journal_mode=WAL;")
                self._sync_connection.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)};")
                self._sync_connection.execute("PRAGMA synchronous=NORMAL;")
                self._sync_connection.execute("PRAGMA foreign_keys=ON;")
                self._sync_connection.commit()
            except Exception as e:
                logger.warning(f"设置同步连接 PRAGMA 失败: {e}")
            
            # 创建表结构
            await self._create_tables()

            # 检查并添加新字段（如果不存在）
            if self.config.get("auto_migrate", True):
                await self._migrate_tables()

            # 针对可能由旧版本生成的库，安全创建依赖特定列的索引
            await self._create_indexes_safe()
            
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

        # 简易重试以缓解偶发的 SQLITE_BUSY（database is locked）
        attempts = 3
        for attempt in range(attempts):
            try:
                async with self._lock:
                    if not self._connection:
                        await self.init_database()

                    # 若为写操作，则跨连接统一加锁，避免异步/同步写入竞争
                    acquired_global = False
                    try:
                        if self._is_write_query(query):
                            # 在异步线程中非阻塞尝试获取全局写锁，避免跨线程释放问题
                            while True:
                                acquired_global = self._global_write_lock.acquire(blocking=False)
                                if acquired_global:
                                    break
                                # 轻微等待后重试，避免阻塞事件循环
                                await asyncio.sleep(0.01)

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
                    finally:
                        if acquired_global:
                            # 释放全局写锁
                            self._global_write_lock.release()
            except Exception as e:
                msg = str(e).lower()
                if "database is locked" in msg and attempt < attempts - 1:
                    # 渐进退避等待后重试
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue
                # 其他错误或最后一次尝试失败：抛出
                raise
    
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
        """同步执行SQL语句（统一走异步连接以避免双连接写竞争）"""
        self.log_query(query, params)

        def _run(coro):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(coro, loop)
                    return future.result()
                return asyncio.run(coro)
            except RuntimeError:
                # 无事件循环时直接运行
                return asyncio.run(coro)

        # 将同步调用委派到异步 execute，从而使用同一 aiosqlite 连接与全局写锁
        return _run(self.execute(query, params))

    def _is_write_query(self, query: str) -> bool:
        """判断是否为写操作（需要全局写锁）"""
        if not query:
            return False
        q = query.strip().lower()
        # 以常见写操作关键字开头的语句
        write_prefixes = (
            "insert", "update", "delete", "replace",
            "create", "alter", "drop", "pragma",
        )
        return q.startswith(write_prefixes)
    
    def fetchone_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> Optional[DatabaseRow]:
        """同步获取单行数据（统一走异步连接）"""
        self.log_query(query, params)

        def _run(coro):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return asyncio.run_coroutine_threadsafe(coro, loop).result()
                return asyncio.run(coro)
            except RuntimeError:
                return asyncio.run(coro)

        return _run(self.fetchone(query, params))
    
    def fetchall_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[DatabaseRow]:
        """同步获取所有数据（统一走异步连接）"""
        self.log_query(query, params)

        def _run(coro):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    return asyncio.run_coroutine_threadsafe(coro, loop).result()
                return asyncio.run(coro)
            except RuntimeError:
                return asyncio.run(coro)

        return _run(self.fetchall(query, params))
    
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

        # 应用性能与并发相关 PRAGMA（同步连接）
        try:
            self._sync_connection.execute("PRAGMA journal_mode=WAL;")
            self._sync_connection.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)};")
            self._sync_connection.execute("PRAGMA synchronous=NORMAL;")
            self._sync_connection.execute("PRAGMA foreign_keys=ON;")
            self._sync_connection.commit()
        except Exception as e:
            logger.warning(f"设置同步连接 PRAGMA 失败: {e}")
    
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

        -- 常用索引以加速筛选与排序
        CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at);

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

        -- 加速按会话查询与时间排序
        CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);

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

        -- idx_mcp_configs_user_id 依赖 user_id 字段，迁移后再创建

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

        CREATE INDEX IF NOT EXISTS idx_session_mcp_servers_session_id ON session_mcp_servers(session_id);

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

        -- MCP 与应用的关联表
        CREATE TABLE IF NOT EXISTS mcp_config_applications (
            id TEXT PRIMARY KEY,
            mcp_config_id TEXT NOT NULL,
            application_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs (id) ON DELETE CASCADE,
            FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_mcp_config_app_mcp ON mcp_config_applications(mcp_config_id);
        CREATE INDEX IF NOT EXISTS idx_mcp_config_app_app ON mcp_config_applications(application_id);

        -- 应用（Application）表
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            icon_url TEXT,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # 分割并执行每个CREATE TABLE语句
        statements = [stmt.strip() for stmt in create_tables_sql.split(';') if stmt.strip()]
        for statement in statements:
            await self.execute(statement)
    
    async def _migrate_tables(self):
        """检查并添加新字段（如果不存在）"""
        # 若旧库缺列较多，仅逐列补加会长期不一致。
        # 在执行逐列补加前，优先进行一次“表重建对齐”，确保结构完全一致。
        try:
            await self._reconcile_tables()
        except Exception as e:
            logger.warning(f"自动重建表以对齐最新结构失败，将尝试逐列补加: {e}")

        migrations = [
            # 为system_contexts添加content字段（如果不存在）
            {
                'table': 'system_contexts',
                'column': 'content',
                'definition': 'TEXT'
            },
            # 为mcp_configs添加command字段（如果不存在）
            {
                'table': 'mcp_configs',
                'column': 'command',
                'definition': 'TEXT'
            },
            # 为ai_model_configs添加provider字段（如果不存在）
            {
                'table': 'ai_model_configs',
                'column': 'provider',
                'definition': 'TEXT'
            },
            # 为ai_model_configs添加model字段（如果不存在）
            {
                'table': 'ai_model_configs',
                'column': 'model',
                'definition': 'TEXT'
            },
            # 为ai_model_configs添加enabled字段（如果不存在）
            {
                'table': 'ai_model_configs',
                'column': 'enabled',
                'definition': 'BOOLEAN DEFAULT 1'
            },
            # 为sessions表添加user_id字段（如果不存在）
            {
                'table': 'sessions',
                'column': 'user_id',
                'definition': 'TEXT'
            },
            # 为sessions表添加project_id字段（如果不存在）
            {
                'table': 'sessions',
                'column': 'project_id',
                'definition': 'TEXT'
            },
            # 为mcp_configs添加user_id字段（如果不存在）
            {
                'table': 'mcp_configs',
                'column': 'user_id',
                'definition': 'TEXT'
            },
            # 为messages表添加status字段（如果不存在）
            {
                'table': 'messages',
                'column': 'status',
                'definition': 'TEXT DEFAULT "completed"'
            },
            # 为messages表添加tool_calls字段（如果不存在）
            {
                'table': 'messages',
                'column': 'tool_calls',
                'definition': 'TEXT'
            },
            # 为messages表添加tool_call_id字段（如果不存在）
            {
                'table': 'messages',
                'column': 'tool_call_id',
                'definition': 'TEXT'
            },
            # 为messages表添加summary字段（如果不存在）
            {
                'table': 'messages',
                'column': 'summary',
                'definition': 'TEXT'
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
            # 为ai_model_configs添加user_id字段（如果不存在）
            {
                'table': 'ai_model_configs',
                'column': 'user_id',
                'definition': 'TEXT'
            },
            # 为system_contexts添加user_id字段（如果不存在）
            {
                'table': 'system_contexts',
                'column': 'user_id',
                'definition': 'TEXT'
            },
            # 为agents添加callable_agent_ids字段（如果不存在）
            {
                'table': 'agents',
                'column': 'callable_agent_ids',
                'definition': 'TEXT'
            },
            # 为agents添加user_id字段（如果不存在）
            {
                'table': 'agents',
                'column': 'user_id',
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

    async def _create_indexes_safe(self):
        """在确认列存在的情况下创建索引，避免旧库初始化失败"""
        try:
            sessions_schema = await self.get_table_schema('sessions')
            if sessions_schema and 'user_id' in sessions_schema and 'project_id' in sessions_schema:
                await self.create_index('sessions', 'idx_sessions_user_project', ['user_id', 'project_id'])
        except Exception as e:
            logger.warning(f"创建 sessions 复合索引失败: {e}")

        try:
            mcp_schema = await self.get_table_schema('mcp_configs')
            if mcp_schema and 'user_id' in mcp_schema:
                await self.create_index('mcp_configs', 'idx_mcp_configs_user_id', ['user_id'])
        except Exception as e:
            logger.warning(f"创建 mcp_configs 索引失败: {e}")

        # 为旧库创建 messages 的复合索引（列存在时）
        try:
            messages_schema = await self.get_table_schema('messages')
            if messages_schema and 'session_id' in messages_schema and 'created_at' in messages_schema:
                await self.create_index('messages', 'idx_messages_session_created', ['session_id', 'created_at'])
        except Exception as e:
            logger.warning(f"创建 messages 复合索引失败: {e}")

        # 为 applications 创建按用户筛选索引（列存在时）
        try:
            apps_schema = await self.get_table_schema('applications')
            if apps_schema and 'user_id' in apps_schema:
                await self.create_index('applications', 'idx_applications_user_id', ['user_id'])
        except Exception as e:
            logger.warning(f"创建 applications 索引失败: {e}")

    async def _reconcile_tables(self):
        """对关键业务表进行强一致对齐：如发现缺列则重建表并迁移数据。
        注意：仅在列缺失时触发，尽量保持数据不丢失。
        """
        expected = self._get_expected_schemas()
        for table_name, columns in expected.items():
            try:
                schema = await self.get_table_schema(table_name)
                expected_names = [name for name, _ in columns]
                if not schema:
                    # 表不存在，创建即可（_create_tables 已处理）
                    continue
                missing = [name for name in expected_names if name not in schema]
                # 缺列或关键类型不匹配则重建
                need_rebuild = False
                if missing:
                    need_rebuild = True
                else:
                    # 针对 messages 表，若 id 类型或主键属性与期望不一致，则重建
                    if table_name == 'messages':
                        try:
                            existing_id_info = schema.get('id', {}) or {}
                            existing_id_type = str(existing_id_info.get('type', '')).upper()
                            existing_id_pk = bool(existing_id_info.get('primary_key', False))

                            expected_id_def = next((defn for name, defn in columns if name == 'id'), '')
                            expected_id_def_upper = expected_id_def.upper()
                            # 解析期望的类型与主键属性
                            expected_id_type = expected_id_def_upper.split()[0] if expected_id_def_upper else ''
                            expected_id_pk = 'PRIMARY KEY' in expected_id_def_upper

                            if existing_id_type != expected_id_type or existing_id_pk != expected_id_pk:
                                need_rebuild = True
                        except Exception as parse_error:
                            # 解析失败时，保守起见进行重建
                            logger.warning(f"解析现有 messages.id 列定义失败，将执行重建: {parse_error}")
                            need_rebuild = True

                if need_rebuild:
                    if missing:
                        logger.info(f"检测到旧表 {table_name} 缺少列 {missing}，执行重建对齐")
                    else:
                        logger.info(f"检测到旧表 {table_name} 关键类型不匹配，执行重建对齐")
                    await self._rebuild_table_with_schema(table_name, columns)
                else:
                    # 完全匹配，无需处理
                    continue
            except Exception as e:
                logger.warning(f"对齐表 {table_name} 结构失败: {e}")

    def _get_expected_schemas(self):
        """返回期望的关键表结构定义，用于重建对齐。"""
        # 仅对本次问题涉及的三张表进行重建对齐，避免影响含外键的表
        return {
            'mcp_configs': [
                ('id', 'TEXT PRIMARY KEY'),
                ('name', 'TEXT NOT NULL'),
                ('command', 'TEXT NOT NULL'),
                ('type', "TEXT DEFAULT 'stdio'"),
                ('args', 'TEXT'),
                ('env', 'TEXT'),
                ('cwd', 'TEXT'),
                ('user_id', 'TEXT'),
                ('enabled', 'BOOLEAN DEFAULT 1'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ],
            'ai_model_configs': [
                ('id', 'TEXT PRIMARY KEY'),
                ('name', 'TEXT NOT NULL'),
                ('provider', 'TEXT NOT NULL'),
                ('model', 'TEXT NOT NULL'),
                ('api_key', 'TEXT'),
                ('base_url', 'TEXT'),
                ('user_id', 'TEXT'),
                ('enabled', 'BOOLEAN DEFAULT 1'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ],
            'system_contexts': [
                ('id', 'TEXT PRIMARY KEY'),
                ('name', 'TEXT NOT NULL'),
                ('content', 'TEXT'),
                ('user_id', 'TEXT'),
                ('is_active', 'BOOLEAN DEFAULT 0'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ],
            'messages': [
                ('id', 'TEXT PRIMARY KEY'),
                ('session_id', 'TEXT NOT NULL'),
                ('role', 'TEXT NOT NULL'),
                ('content', 'TEXT NOT NULL'),
                ('summary', 'TEXT'),
                ('tool_calls', 'TEXT'),
                ('tool_call_id', 'TEXT'),
                ('reasoning', 'TEXT'),
                ('metadata', 'TEXT'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('status', "TEXT DEFAULT 'completed'"),
            ],
            'applications': [
                ('id', 'TEXT PRIMARY KEY'),
                ('name', 'TEXT NOT NULL'),
                ('url', 'TEXT NOT NULL'),
                ('icon_url', 'TEXT'),
                ('user_id', 'TEXT'),
                ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ],
        }

    async def _rebuild_table_with_schema(self, table_name: str, columns):
        """使用期望列定义重建表，并迁移旧数据的可交集列。"""
        new_table = f"{table_name}__new"
        col_defs_sql = ", ".join([f"{name} {definition}" for name, definition in columns])
        create_sql = f"CREATE TABLE {new_table} ({col_defs_sql})"
        await self.execute(create_sql)

        # 读取旧表列
        old_schema = await self.get_table_schema(table_name)
        old_cols = list(old_schema.keys()) if old_schema else []
        expected_names = [name for name, _ in columns]
        common_cols = [name for name in expected_names if name in old_cols]

        if common_cols:
            cols_csv = ", ".join(common_cols)
            copy_sql = f"INSERT INTO {new_table} ({cols_csv}) SELECT {cols_csv} FROM {table_name}"
            await self.execute(copy_sql)

        # 删除旧表并重命名新表
        await self.execute(f"DROP TABLE {table_name}")
        await self.execute(f"ALTER TABLE {new_table} RENAME TO {table_name}")
        logger.info(f"重建完成并对齐表结构: {table_name}")