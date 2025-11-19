/**
 * MongoDB 数据库适配器 - 带连接池管理
 * 复刻自 Python: app/models/mongodb_adapter.py
 */

import { MongoClient } from 'mongodb';
import { AbstractDatabaseAdapter } from './database-interface.js';

export class MongoDBAdapter extends AbstractDatabaseAdapter {
  constructor(config) {
    super();
    this.config = config;
    this.client = null;
    this.db = null;
  }

  /**
   * 初始化数据库
   */
  async initDatabase() {
    const connectionString = this.config.getConnectionString();

    // 创建 MongoDB 客户端
    this.client = new MongoClient(connectionString, {
      maxPoolSize: this.config.max_pool_size,
      minPoolSize: this.config.min_pool_size,
      serverSelectionTimeoutMS: this.config.server_selection_timeout_ms,
      connectTimeoutMS: this.config.connect_timeout_ms,
      socketTimeoutMS: this.config.socket_timeout_ms
    });

    // 连接到数据库
    await this.client.connect();
    this.db = this.client.db(this.config.database);

    // 创建集合和索引
    await this._createCollections();
    await this._createIndexes();

    console.log(`[MongoDB] 数据库初始化完成: ${this.config.database}`);
  }

  /**
   * 创建集合
   */
  async _createCollections() {
    const collections = ['sessions', 'messages', 'mcp_configs', 'mcp_config_profiles'];

    for (const collName of collections) {
      const exists = await this.db.listCollections({ name: collName }).hasNext();
      if (!exists) {
        await this.db.createCollection(collName);
      }
    }
  }

  /**
   * 创建索引
   */
  async _createIndexes() {
    // Sessions 索引
    await this.db.collection('sessions').createIndexes([
      { key: { user_id: 1 } },
      { key: { project_id: 1 } },
      { key: { created_at: -1 } }
    ]);

    // Messages 索引
    await this.db.collection('messages').createIndexes([
      { key: { session_id: 1 } },
      { key: { created_at: -1 } }
    ]);

    // MCP Configs 索引
    await this.db.collection('mcp_configs').createIndexes([
      { key: { name: 1 }, unique: true },
      { key: { user_id: 1 } },
      { key: { enabled: 1 } }
    ]);

    // MCP Config Profiles 索引
    await this.db.collection('mcp_config_profiles').createIndexes([
      { key: { mcp_config_id: 1 } },
      { key: { is_active: 1 } }
    ]);
  }

  /**
   * 关闭数据库连接
   */
  async close() {
    if (this.client) {
      await this.client.close();
      this.client = null;
      this.db = null;
      console.log('[MongoDB] 数据库连接已关闭');
    }
  }

  /**
   * 执行查询（MongoDB 风格）
   * 注意：MongoDB 不使用 SQL，这里提供一个包装方法
   */
  async execute(operation, collectionName, ...args) {
    const collection = this.db.collection(collectionName);
    return await collection[operation](...args);
  }

  /**
   * 获取单个文档
   */
  async fetchone(collectionName, filter = {}) {
    return await this.db.collection(collectionName).findOne(filter);
  }

  /**
   * 获取所有文档
   */
  async fetchall(collectionName, filter = {}, options = {}) {
    return await this.db.collection(collectionName).find(filter, options).toArray();
  }

  /**
   * 同步方法（MongoDB 不支持，抛出错误）
   */
  executeSync() {
    throw new Error('MongoDB adapter does not support synchronous operations');
  }

  fetchoneSync() {
    throw new Error('MongoDB adapter does not support synchronous operations');
  }

  fetchallSync() {
    throw new Error('MongoDB adapter does not support synchronous operations');
  }

  /**
   * 批量插入
   */
  async executeMany(collectionName, documents) {
    return await this.db.collection(collectionName).insertMany(documents);
  }

  /**
   * 检查集合是否存在
   */
  async tableExists(collectionName) {
    const collections = await this.db.listCollections({ name: collectionName }).toArray();
    return collections.length > 0;
  }

  /**
   * 创建集合
   */
  async createTable(collectionName) {
    await this.db.createCollection(collectionName);
  }

  /**
   * 删除集合
   */
  async dropTable(collectionName) {
    await this.db.collection(collectionName).drop();
  }

  /**
   * 开始事务
   */
  async beginTransaction() {
    this.session = this.client.startSession();
    this.session.startTransaction();
  }

  /**
   * 提交事务
   */
  async commitTransaction() {
    if (this.session) {
      await this.session.commitTransaction();
      this.session.endSession();
      this.session = null;
    }
  }

  /**
   * 回滚事务
   */
  async rollbackTransaction() {
    if (this.session) {
      await this.session.abortTransaction();
      this.session.endSession();
      this.session = null;
    }
  }

  /**
   * 创建索引
   */
  async createIndex(collectionName, indexName, fields) {
    const indexSpec = {};
    for (const field of fields) {
      indexSpec[field] = 1;
    }
    await this.db.collection(collectionName).createIndex(indexSpec, { name: indexName });
  }

  /**
   * MongoDB 特定方法：获取集合
   */
  getCollection(name) {
    return this.db.collection(name);
  }
}
