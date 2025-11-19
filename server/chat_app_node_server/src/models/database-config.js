/**
 * 数据库配置模块 - 定义数据库类型和配置选项
 * 复刻自 Python: app/models/database_config.py
 */

export const DatabaseType = {
  SQLITE: 'sqlite',
  MONGODB: 'mongodb'
};

/**
 * SQLite 数据库配置
 */
export class SQLiteConfig {
  constructor(options = {}) {
    this.db_path = options.db_path || 'data/chat_app.db';
    this.timeout = options.timeout || 30000;
    this.busyTimeout = options.busyTimeout || 30000;
  }
}

/**
 * MongoDB 数据库配置
 */
export class MongoDBConfig {
  constructor(options = {}) {
    this.host = options.host || 'localhost';
    this.port = options.port || 27017;
    this.database = options.database || 'chat_app';
    this.username = options.username || null;
    this.password = options.password || null;
    this.connection_string = options.connection_string || null;
    this.max_pool_size = options.max_pool_size || 100;
    this.min_pool_size = options.min_pool_size || 0;
    this.server_selection_timeout_ms = options.server_selection_timeout_ms || 30000;
    this.connect_timeout_ms = options.connect_timeout_ms || 20000;
    this.socket_timeout_ms = options.socket_timeout_ms || 20000;
  }

  /**
   * 获取 MongoDB 连接字符串
   */
  getConnectionString() {
    if (this.connection_string) {
      return this.connection_string;
    }

    let auth = '';
    if (this.username && this.password) {
      auth = `${this.username}:${this.password}@`;
    }

    return `mongodb://${auth}${this.host}:${this.port}/${this.database}`;
  }
}

/**
 * 数据库配置主类
 */
export class DatabaseConfig {
  constructor(options = {}) {
    this.type = options.type || DatabaseType.SQLITE;
    this.sqlite = new SQLiteConfig(options.sqlite || {});
    this.mongodb = new MongoDBConfig(options.mongodb || {});
    this.auto_migrate = options.auto_migrate !== undefined ? options.auto_migrate : true;
    this.debug = options.debug || false;
  }

  /**
   * 获取当前激活的数据库配置
   */
  getActiveConfig() {
    if (this.type === DatabaseType.SQLITE) {
      return this.sqlite;
    } else if (this.type === DatabaseType.MONGODB) {
      return this.mongodb;
    }
    throw new Error(`Unknown database type: ${this.type}`);
  }
}
