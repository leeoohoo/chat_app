/**
 * 数据库工厂 - 单例模式管理数据库适配器
 * 复刻自 Python: app/models/database_factory.py
 */

import { DatabaseConfig, DatabaseType } from './database-config.js';
import { SQLiteAdapter } from './sqlite-adapter.js';
import { MongoDBAdapter } from './mongodb-adapter.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * 数据库工厂类 - 单例模式
 */
class DatabaseFactory {
  constructor() {
    this._adapter = null;
    this._config = null;
  }

  /**
   * 从配置文件加载数据库配置
   */
  loadConfig(configPath = null) {
    if (!configPath) {
      configPath = path.join(__dirname, '../../config/database.json');
    }

    if (!fs.existsSync(configPath)) {
      console.warn(`[DatabaseFactory] 配置文件不存在: ${configPath}, 使用默认 SQLite 配置`);
      return new DatabaseConfig();
    }

    const configData = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    return new DatabaseConfig(configData);
  }

  /**
   * 创建数据库适配器
   */
  createAdapter(config) {
    if (config.type === DatabaseType.SQLITE) {
      return new SQLiteAdapter(config.sqlite);
    } else if (config.type === DatabaseType.MONGODB) {
      return new MongoDBAdapter(config.mongodb);
    } else {
      throw new Error(`Unsupported database type: ${config.type}`);
    }
  }

  /**
   * 获取数据库适配器（延迟初始化）
   */
  async getAdapter() {
    if (!this._adapter) {
      this._config = this.loadConfig();
      this._adapter = this.createAdapter(this._config);
      await this._adapter.initDatabase();
    }
    return this._adapter;
  }

  /**
   * 获取数据库适配器（同步，用于已初始化的情况）
   */
  getAdapterSync() {
    if (!this._adapter) {
      throw new Error('Database adapter not initialized. Call getAdapter() first.');
    }
    return this._adapter;
  }

  /**
   * 切换数据库
   */
  async switchDatabase(newConfig) {
    // 关闭现有连接
    if (this._adapter) {
      await this._adapter.close();
    }

    // 创建新适配器
    this._config = newConfig;
    this._adapter = this.createAdapter(newConfig);
    await this._adapter.initDatabase();

    return this._adapter;
  }

  /**
   * 切换到 SQLite
   */
  async switchToSQLite(dbPath = 'data/chat_app.db') {
    const config = new DatabaseConfig({
      type: DatabaseType.SQLITE,
      sqlite: { db_path: dbPath }
    });
    return await this.switchDatabase(config);
  }

  /**
   * 切换到 MongoDB
   */
  async switchToMongoDB(host = 'localhost', port = 27017, database = 'chat_app') {
    const config = new DatabaseConfig({
      type: DatabaseType.MONGODB,
      mongodb: { host, port, database }
    });
    return await this.switchDatabase(config);
  }

  /**
   * 重置工厂（测试用）
   */
  async reset() {
    if (this._adapter) {
      await this._adapter.close();
    }
    this._adapter = null;
    this._config = null;
  }
}

// 导出单例实例
export const databaseFactory = new DatabaseFactory();

// 便捷方法
export async function getDatabase() {
  return await databaseFactory.getAdapter();
}

export function getDatabaseSync() {
  return databaseFactory.getAdapterSync();
}

export async function switchToSQLite(dbPath) {
  return await databaseFactory.switchToSQLite(dbPath);
}

export async function switchToMongoDB(host, port, database) {
  return await databaseFactory.switchToMongoDB(host, port, database);
}
