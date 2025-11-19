# 数据库配置模型
# 支持SQLite和MongoDB两种数据库类型的配置

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from enum import Enum

class DatabaseType(str, Enum):
    """数据库类型枚举"""
    SQLITE = "sqlite"
    MONGODB = "mongodb"

class SQLiteConfig(BaseModel):
    """SQLite数据库配置"""
    db_path: Optional[str] = Field(
        default=None,
        description="SQLite数据库文件路径，如果为None则使用默认路径"
    )
    timeout: float = Field(
        default=30.0,
        description="数据库连接超时时间（秒）"
    )
    check_same_thread: bool = Field(
        default=False,
        description="是否检查同一线程访问"
    )

class MongoDBConfig(BaseModel):
    """MongoDB数据库配置"""
    host: str = Field(
        default="localhost",
        description="MongoDB服务器地址"
    )
    port: int = Field(
        default=27017,
        description="MongoDB服务器端口"
    )
    database: str = Field(
        default="chat_app",
        description="数据库名称"
    )
    username: Optional[str] = Field(
        default=None,
        description="用户名"
    )
    password: Optional[str] = Field(
        default=None,
        description="密码"
    )
    auth_source: str = Field(
        default="admin",
        description="认证数据库"
    )
    connection_string: Optional[str] = Field(
        default=None,
        description="完整的MongoDB连接字符串，如果提供则忽略其他连接参数"
    )
    max_pool_size: int = Field(
        default=100,
        description="连接池最大连接数"
    )
    min_pool_size: int = Field(
        default=0,
        description="连接池最小连接数"
    )
    server_selection_timeout_ms: int = Field(
        default=30000,
        description="服务器选择超时时间（毫秒）"
    )
    connect_timeout_ms: int = Field(
        default=20000,
        description="连接超时时间（毫秒）"
    )
    socket_timeout_ms: int = Field(
        default=20000,
        description="套接字超时时间（毫秒）"
    )

    def get_connection_string(self) -> str:
        """获取MongoDB连接字符串"""
        if self.connection_string:
            return self.connection_string
        
        # 构建连接字符串
        if self.username and self.password:
            auth_part = f"{self.username}:{self.password}@"
        else:
            auth_part = ""
        
        connection_string = f"mongodb://{auth_part}{self.host}:{self.port}/{self.database}"
        
        # 添加认证源
        if self.username and self.auth_source != self.database:
            connection_string += f"?authSource={self.auth_source}"
        
        return connection_string

class DatabaseConfig(BaseModel):
    """数据库配置主类"""
    type: DatabaseType = Field(
        default=DatabaseType.SQLITE,
        description="数据库类型"
    )
    sqlite: SQLiteConfig = Field(
        default_factory=SQLiteConfig,
        description="SQLite配置"
    )
    mongodb: MongoDBConfig = Field(
        default_factory=MongoDBConfig,
        description="MongoDB配置"
    )
    
    # 通用配置
    auto_migrate: bool = Field(
        default=True,
        description="是否自动执行数据库迁移"
    )
    debug: bool = Field(
        default=False,
        description="是否启用数据库调试模式"
    )
    
    def get_active_config(self) -> Dict[str, Any]:
        """获取当前激活的数据库配置"""
        if self.type == DatabaseType.SQLITE:
            return {
                "type": self.type,
                "config": self.sqlite.model_dump(),
                "auto_migrate": self.auto_migrate,
                "debug": self.debug
            }
        elif self.type == DatabaseType.MONGODB:
            return {
                "type": self.type,
                "config": self.mongodb.model_dump(),
                "auto_migrate": self.auto_migrate,
                "debug": self.debug
            }
        else:
            raise ValueError(f"不支持的数据库类型: {self.type}")

    @classmethod
    def create_sqlite_config(
        cls,
        db_path: Optional[str] = None,
        timeout: float = 30.0,
        auto_migrate: bool = True,
        debug: bool = False
    ) -> "DatabaseConfig":
        """创建SQLite配置"""
        return cls(
            type=DatabaseType.SQLITE,
            sqlite=SQLiteConfig(
                db_path=db_path,
                timeout=timeout
            ),
            auto_migrate=auto_migrate,
            debug=debug
        )

    @classmethod
    def create_mongodb_config(
        cls,
        host: str = "localhost",
        port: int = 27017,
        database: str = "chat_app",
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None,
        auto_migrate: bool = True,
        debug: bool = False,
        **kwargs
    ) -> "DatabaseConfig":
        """创建MongoDB配置"""
        mongodb_config = MongoDBConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            connection_string=connection_string,
            **kwargs
        )
        
        return cls(
            type=DatabaseType.MONGODB,
            mongodb=mongodb_config,
            auto_migrate=auto_migrate,
            debug=debug
        )

# 默认配置实例
DEFAULT_DATABASE_CONFIG = DatabaseConfig.create_sqlite_config()

# 配置示例
EXAMPLE_CONFIGS = {
    "sqlite_default": DatabaseConfig.create_sqlite_config(),
    "sqlite_custom": DatabaseConfig.create_sqlite_config(
        db_path="/custom/path/chat_app.db",
        timeout=60.0,
        debug=True
    ),
    "mongodb_local": DatabaseConfig.create_mongodb_config(
        host="localhost",
        port=27017,
        database="chat_app_dev"
    ),
    "mongodb_auth": DatabaseConfig.create_mongodb_config(
        host="localhost",
        port=27017,
        database="chat_app_prod",
        username="chat_user",
        password="secure_password",
        auth_source="admin"
    ),
    "mongodb_connection_string": DatabaseConfig.create_mongodb_config(
        connection_string="mongodb://user:pass@localhost:27017/chat_app?authSource=admin"
    )
}