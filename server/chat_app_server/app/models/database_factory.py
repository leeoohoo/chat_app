#!/usr/bin/env python3
"""
数据库工厂类
根据配置选择数据库实现（SQLite或MongoDB）
"""
import os
import json
from typing import Optional, Dict, Any
from .database_config import DatabaseConfig, DatabaseType
from .database_interface import AbstractDatabaseAdapter
from .sqlite_adapter import SQLiteAdapter
from .mongodb_adapter import MongoDBAdapter


class DatabaseFactory:
    """数据库工厂类，根据配置创建相应的数据库适配器"""
    
    _instance: Optional['DatabaseFactory'] = None
    _adapter: Optional[AbstractDatabaseAdapter] = None
    _config: Optional[DatabaseConfig] = None
    
    def __new__(cls) -> 'DatabaseFactory':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'DatabaseFactory':
        """获取工厂实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_config(self, config_path: Optional[str] = None) -> DatabaseConfig:
        """
        加载数据库配置
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
            
        Returns:
            DatabaseConfig: 数据库配置对象
        """
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config.json"
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 检查是否有数据库配置
            if 'database' not in config_data:
                # 如果没有数据库配置，使用默认SQLite配置
                config_data['database'] = {
                    'type': 'sqlite',
                    'sqlite': {
                        'database_path': 'data/chat_app.db'
                    }
                }
            
            self._config = DatabaseConfig(**config_data['database'])
            return self._config
            
        except FileNotFoundError:
            # 如果配置文件不存在，创建默认配置
            default_config = DatabaseConfig.create_sqlite_config()
            self._config = default_config
            return default_config
            
        except Exception as e:
            print(f"加载数据库配置失败: {e}")
            # 使用默认SQLite配置
            default_config = DatabaseConfig.create_sqlite_config()
            self._config = default_config
            return default_config
    
    def create_adapter(self, config: Optional[DatabaseConfig] = None) -> AbstractDatabaseAdapter:
        """
        创建数据库适配器
        
        Args:
            config: 数据库配置，如果为None则使用已加载的配置
            
        Returns:
            AbstractDatabaseAdapter: 数据库适配器实例
        """
        if config is None:
            if self._config is None:
                config = self.load_config()
            else:
                config = self._config
        
        if config.type == DatabaseType.SQLITE:
            return SQLiteAdapter(config.sqlite)
        elif config.type == DatabaseType.MONGODB:
            return MongoDBAdapter(config.mongodb)
        else:
            raise ValueError(f"不支持的数据库类型: {config.type}")
    
    def get_adapter(self, force_reload: bool = False) -> AbstractDatabaseAdapter:
        """
        获取数据库适配器（单例模式）
        
        Args:
            force_reload: 是否强制重新加载配置和创建适配器
            
        Returns:
            AbstractDatabaseAdapter: 数据库适配器实例
        """
        if self._adapter is None or force_reload:
            if self._config is None or force_reload:
                self.load_config()
            self._adapter = self.create_adapter(self._config)
        
        return self._adapter
    
    def switch_database(self, new_config: DatabaseConfig) -> AbstractDatabaseAdapter:
        """
        切换数据库
        
        Args:
            new_config: 新的数据库配置
            
        Returns:
            AbstractDatabaseAdapter: 新的数据库适配器实例
        """
        # 关闭当前适配器
        if self._adapter is not None:
            try:
                self._adapter.close()
            except Exception as e:
                print(f"关闭当前数据库连接时出错: {e}")
        
        # 更新配置和适配器
        self._config = new_config
        self._adapter = self.create_adapter(new_config)
        
        return self._adapter
    
    def get_config(self) -> Optional[DatabaseConfig]:
        """获取当前数据库配置"""
        return self._config
    
    def close(self):
        """关闭数据库连接"""
        if self._adapter is not None:
            try:
                self._adapter.close()
            except Exception as e:
                print(f"关闭数据库连接时出错: {e}")
            finally:
                self._adapter = None


# 全局工厂实例
database_factory = DatabaseFactory.get_instance()


def get_database() -> AbstractDatabaseAdapter:
    """
    获取数据库适配器的便捷函数
    
    Returns:
        AbstractDatabaseAdapter: 数据库适配器实例
    """
    return database_factory.get_adapter()


def get_database_config() -> Optional[DatabaseConfig]:
    """
    获取数据库配置的便捷函数
    
    Returns:
        DatabaseConfig: 数据库配置对象
    """
    return database_factory.get_config()


def reload_database(config_path: Optional[str] = None) -> AbstractDatabaseAdapter:
    """
    重新加载数据库配置和适配器
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        AbstractDatabaseAdapter: 新的数据库适配器实例
    """
    if config_path:
        config = database_factory.load_config(config_path)
    else:
        config = database_factory.load_config()
    
    return database_factory.switch_database(config)


def switch_to_sqlite(database_path: str = "data/chat_app.db") -> AbstractDatabaseAdapter:
    """
    切换到SQLite数据库
    
    Args:
        database_path: SQLite数据库文件路径
        
    Returns:
        AbstractDatabaseAdapter: SQLite适配器实例
    """
    config = DatabaseConfig.create_sqlite_config(database_path)
    return database_factory.switch_database(config)


def switch_to_mongodb(
    host: str = "localhost",
    port: int = 27017,
    database: str = "chat_app",
    username: Optional[str] = None,
    password: Optional[str] = None
) -> AbstractDatabaseAdapter:
    """
    切换到MongoDB数据库
    
    Args:
        host: MongoDB主机地址
        port: MongoDB端口
        database: 数据库名称
        username: 用户名
        password: 密码
        
    Returns:
        AbstractDatabaseAdapter: MongoDB适配器实例
    """
    config = DatabaseConfig.create_mongodb_config(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )
    return database_factory.switch_database(config)


# 初始化数据库（在模块导入时执行）
def initialize_database():
    """初始化数据库连接"""
    try:
        adapter = get_database()
        # 注意：这里不能调用 initialize()，因为它是异步方法
        # 数据库适配器会在第一次使用时自动初始化
        print(f"数据库适配器创建成功，类型: {adapter.__class__.__name__}")
    except Exception as e:
        print(f"数据库初始化失败: {e}")


# 在模块导入时自动初始化
if __name__ != "__main__":
    try:
        initialize_database()
    except Exception as e:
        print(f"自动初始化数据库失败: {e}")