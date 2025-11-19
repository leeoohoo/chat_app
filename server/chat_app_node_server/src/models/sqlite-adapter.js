/**
 * SQLite 数据库适配器 - 带并发控制和 WAL 优化
 * 复刻自 Python: app/models/sqlite_adapter.py
 */

import Database from 'better-sqlite3';
import { AbstractDatabaseAdapter } from './database-interface.js';
import path from 'path';
import fs from 'fs';

export class SQLiteAdapter extends AbstractDatabaseAdapter {
  constructor(config) {
    super();
    this.config = config;
    this.db = null;
    this.writeQueue = Promise.resolve();
  }

  /**
   * 初始化数据库
   */
  async initDatabase() {
    // 确保数据目录存在
    const dbDir = path.dirname(this.config.db_path);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }

    // 创建数据库连接
    this.db = new Database(this.config.db_path, {
      timeout: this.config.timeout || 30000
    });

    // 优化 SQLite 设置
    this._optimizeDatabase();

    // 创建表
    await this._createTables();

    console.log(`[SQLite] 数据库初始化完成: ${this.config.db_path}`);
  }

  /**
   * 优化数据库设置
   */
  _optimizeDatabase() {
    // WAL 模式 - 允许并发读写
    this.db.pragma('journal_mode = WAL');

    // 正常同步模式 - 平衡性能和安全
    this.db.pragma('synchronous = NORMAL');

    // 启用外键约束
    this.db.pragma('foreign_keys = ON');

    // 忙等待超时
    this.db.pragma(`busy_timeout = ${this.config.busyTimeout || 30000}`);

    console.log('[SQLite] 数据库优化设置已应用');
  }

  /**
   * 创建所有表
   */
  async _createTables() {
    // 会话表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        metadata TEXT,
        user_id TEXT,
        project_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // 消息表
    await this.execute(`
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
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
      )
    `);

    // MCP 配置表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS mcp_configs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        command TEXT NOT NULL,
        type TEXT DEFAULT 'stdio',
        args TEXT,
        env TEXT,
        cwd TEXT,
        user_id TEXT,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // MCP 激活档案表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS mcp_config_profiles (
        id TEXT PRIMARY KEY,
        mcp_config_id TEXT NOT NULL,
        name TEXT NOT NULL,
        args TEXT,
        env TEXT,
        cwd TEXT,
        enabled INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs(id) ON DELETE CASCADE
      )
    `);

    // AI 模型配置表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS ai_model_configs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        provider TEXT DEFAULT 'openai',
        model TEXT NOT NULL,
        api_key TEXT,
        base_url TEXT,
        user_id TEXT,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // 系统上下文表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS system_contexts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        content TEXT,
        user_id TEXT NOT NULL,
        is_active INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // 智能体表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        ai_model_config_id TEXT NOT NULL,
        system_context_id TEXT,
        description TEXT,
        user_id TEXT,
        mcp_config_ids TEXT,
        callable_agent_ids TEXT,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ai_model_config_id) REFERENCES ai_model_configs(id),
        FOREIGN KEY (system_context_id) REFERENCES system_contexts(id)
      )
    `);

    // 迁移：为已有 agents 表添加缺失的列
    try {
      const cols = this.db.prepare('PRAGMA table_info(agents)').all();
      const colNames = new Set(cols.map(c => c.name));
      if (!colNames.has('mcp_config_ids')) {
        await this.execute(`ALTER TABLE agents ADD COLUMN mcp_config_ids TEXT`);
      }
      if (!colNames.has('callable_agent_ids')) {
        await this.execute(`ALTER TABLE agents ADD COLUMN callable_agent_ids TEXT`);
      }
    } catch (e) {}

    // 应用表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        description TEXT,
        user_id TEXT,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // MCP 配置与应用关联表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS mcp_config_applications (
        id TEXT PRIMARY KEY,
        mcp_config_id TEXT NOT NULL,
        application_id TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs(id) ON DELETE CASCADE,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
      )
    `);

    // 系统上下文与应用关联表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS system_context_applications (
        id TEXT PRIMARY KEY,
        system_context_id TEXT NOT NULL,
        application_id TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (system_context_id) REFERENCES system_contexts(id) ON DELETE CASCADE,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
      )
    `);

    // 智能体与应用关联表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS agent_applications (
        id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        application_id TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
      )
    `);

    // 会话 MCP 服务器关联表
    await this.execute(`
      CREATE TABLE IF NOT EXISTS session_mcp_servers (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        mcp_server_name TEXT,
        mcp_config_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs(id)
      )
    `);

    // 创建索引
    await this._createIndexes();
  }

  /**
   * 创建索引
   */
  async _createIndexes() {
    const indexes = [
      'CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)',
      'CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)',
      'CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)',
      'CREATE INDEX IF NOT EXISTS idx_mcp_configs_user_id ON mcp_configs(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_mcp_configs_enabled ON mcp_configs(enabled)',
      'CREATE INDEX IF NOT EXISTS idx_ai_model_configs_user_id ON ai_model_configs(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_system_contexts_user_id ON system_contexts(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_session_mcp_servers_session_id ON session_mcp_servers(session_id)',
      'CREATE INDEX IF NOT EXISTS idx_mcp_config_profiles_mcp_config_id ON mcp_config_profiles(mcp_config_id)',
      'CREATE INDEX IF NOT EXISTS idx_mcp_config_applications_mcp_config_id ON mcp_config_applications(mcp_config_id)',
      'CREATE INDEX IF NOT EXISTS idx_system_context_applications_context_id ON system_context_applications(system_context_id)',
      'CREATE INDEX IF NOT EXISTS idx_agent_applications_agent_id ON agent_applications(agent_id)'
    ];

    for (const indexSql of indexes) {
      await this.execute(indexSql);
    }
  }

  /**
   * 关闭数据库连接
   */
  async close() {
    if (this.db) {
      this.db.close();
      this.db = null;
      console.log('[SQLite] 数据库连接已关闭');
    }
  }

  /**
   * 序列化写操作（解决并发锁定问题）
   */
  _serializeWrite(fn) {
    this.writeQueue = this.writeQueue.then(fn, fn);
    return this.writeQueue;
  }

  /**
   * 执行 SQL 查询（异步）
   */
  async execute(query, params = []) {
    // 如果是写操作，序列化执行
    const isWriteOp = /^\s*(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)/i.test(query);

    if (isWriteOp) {
      return this._serializeWrite(() => {
        const stmt = this.db.prepare(query);
        return stmt.run(...params);
      });
    } else {
      const stmt = this.db.prepare(query);
      return stmt.run(...params);
    }
  }

  /**
   * 获取单行数据（异步）
   */
  async fetchone(query, params = []) {
    const stmt = this.db.prepare(query);
    return stmt.get(...params) || null;
  }

  /**
   * 获取所有行数据（异步）
   */
  async fetchall(query, params = []) {
    const stmt = this.db.prepare(query);
    return stmt.all(...params);
  }

  /**
   * 执行 SQL 查询（同步）
   */
  executeSync(query, params = []) {
    const stmt = this.db.prepare(query);
    return stmt.run(...params);
  }

  /**
   * 获取单行数据（同步）
   */
  fetchoneSync(query, params = []) {
    const stmt = this.db.prepare(query);
    return stmt.get(...params) || null;
  }

  /**
   * 获取所有行数据（同步）
   */
  fetchallSync(query, params = []) {
    const stmt = this.db.prepare(query);
    return stmt.all(...params);
  }

  /**
   * 批量执行 SQL 查询（异步）
   */
  async executeMany(query, paramsList) {
    return this._serializeWrite(() => {
      const stmt = this.db.prepare(query);
      const transaction = this.db.transaction((params) => {
        for (const p of params) {
          stmt.run(...p);
        }
      });
      return transaction(paramsList);
    });
  }

  /**
   * 检查表是否存在（异步）
   */
  async tableExists(tableName) {
    const result = await this.fetchone(
      `SELECT name FROM sqlite_master WHERE type='table' AND name=?`,
      [tableName]
    );
    return result !== null;
  }

  /**
   * 创建表（异步）
   */
  async createTable(tableName, schema) {
    const sql = `CREATE TABLE IF NOT EXISTS ${tableName} (${schema})`;
    await this.execute(sql);
  }

  /**
   * 删除表（异步）
   */
  async dropTable(tableName) {
    await this.execute(`DROP TABLE IF EXISTS ${tableName}`);
  }

  /**
   * 开始事务（异步）
   */
  async beginTransaction() {
    await this.execute('BEGIN TRANSACTION');
  }

  /**
   * 提交事务（异步）
   */
  async commitTransaction() {
    await this.execute('COMMIT');
  }

  /**
   * 回滚事务（异步）
   */
  async rollbackTransaction() {
    await this.execute('ROLLBACK');
  }

  /**
   * 创建索引（异步）
   */
  async createIndex(tableName, indexName, fields) {
    const fieldsStr = fields.join(', ');
    const sql = `CREATE INDEX IF NOT EXISTS ${indexName} ON ${tableName}(${fieldsStr})`;
    await this.execute(sql);
  }
}
