# 数据库抽象接口
# 定义统一的数据库操作方法，支持SQLite和MongoDB

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union, Tuple
import logging

logger = logging.getLogger(__name__)

class DatabaseRow:
    """数据库行的抽象表示，兼容SQLite Row和MongoDB文档"""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)
    
    def __setitem__(self, key: str, value: Any):
        self._data[key] = value
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return dict(self._data)

class DatabaseCursor:
    """数据库游标的抽象表示"""
    
    def __init__(self, rowcount: int = 0, lastrowid: Optional[str] = None):
        self.rowcount = rowcount
        self.lastrowid = lastrowid

class AbstractDatabaseAdapter(ABC):
    """抽象数据库适配器接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.debug = config.get("debug", False)
        self._connection = None
    
    @abstractmethod
    async def init_database(self) -> None:
        """初始化数据库连接和表结构"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭数据库连接"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> DatabaseCursor:
        """执行SQL/查询语句"""
        pass
    
    @abstractmethod
    async def fetchone(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> Optional[DatabaseRow]:
        """获取单行数据"""
        pass
    
    @abstractmethod
    async def fetchall(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[DatabaseRow]:
        """获取所有数据"""
        pass
    
    @abstractmethod
    def execute_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> DatabaseCursor:
        """同步执行SQL/查询语句"""
        pass
    
    @abstractmethod
    def fetchone_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> Optional[DatabaseRow]:
        """同步获取单行数据"""
        pass
    
    @abstractmethod
    def fetchall_sync(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> List[DatabaseRow]:
        """同步获取所有数据"""
        pass
    
    # 高级操作方法
    @abstractmethod
    async def create_table(self, table_name: str, schema: Dict[str, Any]) -> None:
        """创建表"""
        pass
    
    @abstractmethod
    async def drop_table(self, table_name: str) -> None:
        """删除表"""
        pass
    
    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        pass
    
    @abstractmethod
    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表结构"""
        pass
    
    # 事务支持
    @abstractmethod
    async def begin_transaction(self) -> None:
        """开始事务"""
        pass
    
    @abstractmethod
    async def commit_transaction(self) -> None:
        """提交事务"""
        pass
    
    @abstractmethod
    async def rollback_transaction(self) -> None:
        """回滚事务"""
        pass
    
    # 批量操作
    @abstractmethod
    async def execute_many(self, query: str, params_list: List[Union[Tuple, Dict[str, Any]]]) -> DatabaseCursor:
        """批量执行"""
        pass
    
    # 索引管理
    @abstractmethod
    async def create_index(self, table_name: str, index_name: str, fields: List[str], unique: bool = False) -> None:
        """创建索引"""
        pass
    
    @abstractmethod
    async def drop_index(self, table_name: str, index_name: str) -> None:
        """删除索引"""
        pass
    
    # 数据库信息
    @abstractmethod
    async def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        pass
    
    # 工具方法
    def log_query(self, query: str, params: Optional[Union[Tuple, Dict[str, Any]]] = None) -> None:
        """记录查询日志"""
        if self.debug:
            if params:
                logger.debug(f"执行查询: {query} | 参数: {params}")
            else:
                logger.debug(f"执行查询: {query}")
    
    def row_to_dict(self, row: Optional[DatabaseRow]) -> Optional[Dict[str, Any]]:
        """将数据库行转换为字典"""
        if row is None:
            return None
        return row.to_dict()
    
    def rows_to_dicts(self, rows: List[DatabaseRow]) -> List[Dict[str, Any]]:
        """将数据库行列表转换为字典列表"""
        return [row.to_dict() for row in rows]

class DatabaseTransaction:
    """数据库事务上下文管理器"""
    
    def __init__(self, adapter: AbstractDatabaseAdapter):
        self.adapter = adapter
        self._in_transaction = False
    
    async def __aenter__(self):
        await self.adapter.begin_transaction()
        self._in_transaction = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._in_transaction:
            if exc_type is None:
                await self.adapter.commit_transaction()
            else:
                await self.adapter.rollback_transaction()
            self._in_transaction = False

# 查询构建器辅助类
class QueryBuilder:
    """查询构建器，帮助构建跨数据库的查询"""
    
    def __init__(self, adapter_type: str):
        self.adapter_type = adapter_type.lower()
    
    def build_select(
        self,
        table: str,
        fields: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[str, Union[Tuple, Dict[str, Any]]]:
        """构建SELECT查询"""
        if self.adapter_type == "sqlite":
            return self._build_sqlite_select(table, fields, where, order_by, limit, offset)
        elif self.adapter_type == "mongodb":
            return self._build_mongodb_find(table, fields, where, order_by, limit, offset)
        else:
            raise ValueError(f"不支持的适配器类型: {self.adapter_type}")
    
    def build_insert(
        self,
        table: str,
        data: Dict[str, Any]
    ) -> Tuple[str, Union[Tuple, Dict[str, Any]]]:
        """构建INSERT查询"""
        if self.adapter_type == "sqlite":
            return self._build_sqlite_insert(table, data)
        elif self.adapter_type == "mongodb":
            return self._build_mongodb_insert(table, data)
        else:
            raise ValueError(f"不支持的适配器类型: {self.adapter_type}")
    
    def build_update(
        self,
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> Tuple[str, Union[Tuple, Dict[str, Any]]]:
        """构建UPDATE查询"""
        if self.adapter_type == "sqlite":
            return self._build_sqlite_update(table, data, where)
        elif self.adapter_type == "mongodb":
            return self._build_mongodb_update(table, data, where)
        else:
            raise ValueError(f"不支持的适配器类型: {self.adapter_type}")
    
    def build_delete(
        self,
        table: str,
        where: Dict[str, Any]
    ) -> Tuple[str, Union[Tuple, Dict[str, Any]]]:
        """构建DELETE查询"""
        if self.adapter_type == "sqlite":
            return self._build_sqlite_delete(table, where)
        elif self.adapter_type == "mongodb":
            return self._build_mongodb_delete(table, where)
        else:
            raise ValueError(f"不支持的适配器类型: {self.adapter_type}")
    
    def _build_sqlite_select(self, table, fields, where, order_by, limit, offset):
        """构建SQLite SELECT查询"""
        # 构建字段列表
        if fields:
            fields_str = ", ".join(fields)
        else:
            fields_str = "*"
        
        query = f"SELECT {fields_str} FROM {table}"
        params = []
        
        # 构建WHERE子句
        if where:
            where_clauses = []
            for key, value in where.items():
                where_clauses.append(f"{key} = ?")
                params.append(value)
            query += f" WHERE {' AND '.join(where_clauses)}"
        
        # 构建ORDER BY子句
        if order_by:
            query += f" ORDER BY {', '.join(order_by)}"
        
        # 构建LIMIT和OFFSET子句
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        return query, tuple(params)
    
    def _build_sqlite_insert(self, table, data):
        """构建SQLite INSERT查询"""
        fields = list(data.keys())
        placeholders = ", ".join(["?" for _ in fields])
        query = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})"
        params = tuple(data.values())
        return query, params
    
    def _build_sqlite_update(self, table, data, where):
        """构建SQLite UPDATE查询"""
        set_clauses = [f"{key} = ?" for key in data.keys()]
        where_clauses = [f"{key} = ?" for key in where.keys()]
        
        query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        params = tuple(list(data.values()) + list(where.values()))
        return query, params
    
    def _build_sqlite_delete(self, table, where):
        """构建SQLite DELETE查询"""
        where_clauses = [f"{key} = ?" for key in where.keys()]
        query = f"DELETE FROM {table} WHERE {' AND '.join(where_clauses)}"
        params = tuple(where.values())
        return query, params
    
    def _build_mongodb_find(self, collection, fields, where, order_by, limit, offset):
        """构建MongoDB查询"""
        # MongoDB使用不同的查询格式，这里返回查询参数
        query_params = {
            "collection": collection,
            "filter": where or {},
            "projection": {field: 1 for field in fields} if fields else None,
            "sort": [(field.lstrip('-'), -1 if field.startswith('-') else 1) for field in order_by] if order_by else None,
            "limit": limit,
            "skip": offset
        }
        return "find", query_params
    
    def _build_mongodb_insert(self, collection, data):
        """构建MongoDB插入操作"""
        return "insert_one", {"collection": collection, "document": data}
    
    def _build_mongodb_update(self, collection, data, where):
        """构建MongoDB更新操作"""
        return "update_one", {
            "collection": collection,
            "filter": where,
            "update": {"$set": data}
        }
    
    def _build_mongodb_delete(self, collection, where):
        """构建MongoDB删除操作"""
        return "delete_one", {
            "collection": collection,
            "filter": where
        }