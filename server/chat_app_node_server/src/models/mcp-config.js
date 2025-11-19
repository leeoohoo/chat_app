/**
 * MCP Config 数据模型 - MCP 配置管理
 * 复刻自 Python: app/models/config.py
 */

import { v4 as uuidv4 } from 'uuid';
import { getDatabaseSync } from './database-factory.js';

/**
 * MCP Config 模型类
 */
export class McpConfig {
  constructor(data) {
    this.id = data.id || uuidv4();
    this.name = data.name;
    this.command = data.command;
    this.type = data.type || 'stdio'; // stdio or http
    this.args = data.args || null;
    this.env = data.env || null;
    this.cwd = data.cwd || null;
    this.user_id = data.user_id || null;
    this.enabled = data.enabled !== undefined ? data.enabled : true;
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at || new Date().toISOString();
  }

  /**
   * 转换为数据库格式
   */
  toDb() {
    return {
      id: this.id,
      name: this.name,
      command: this.command,
      type: this.type,
      args: this.args ? JSON.stringify(this.args) : null,
      env: this.env ? JSON.stringify(this.env) : null,
      cwd: this.cwd,
      user_id: this.user_id,
      enabled: this.enabled ? 1 : 0,
      created_at: this.created_at,
      updated_at: this.updated_at
    };
  }

  /**
   * 从数据库行创建实例
   */
  static fromDb(row) {
    if (!row) return null;
    return new McpConfig({
      ...row,
      args: row.args ? JSON.parse(row.args) : null,
      env: row.env ? JSON.parse(row.env) : null,
      enabled: Boolean(row.enabled)
    });
  }
}

/**
 * MCP Config 服务类
 */
export class McpConfigService {
  /**
   * 创建 MCP 配置（异步）
   */
  static async create(configData) {
    const config = new McpConfig(configData);
    const db = getDatabaseSync();
    const dbData = config.toDb();

    await db.execute(
      `INSERT INTO mcp_configs (id, name, command, type, args, env, cwd, user_id, enabled, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        dbData.id,
        dbData.name,
        dbData.command,
        dbData.type,
        dbData.args,
        dbData.env,
        dbData.cwd,
        dbData.user_id,
        dbData.enabled,
        dbData.created_at,
        dbData.updated_at
      ]
    );

    return config;
  }

  /**
   * 根据 ID 获取配置（异步）
   */
  static async getById(configId) {
    const db = getDatabaseSync();
    const row = await db.fetchone('SELECT * FROM mcp_configs WHERE id = ?', [configId]);
    return McpConfig.fromDb(row);
  }

  /**
   * 获取所有配置（异步）
   */
  static async getAll(userId = null) {
    const db = getDatabaseSync();
    let query = 'SELECT * FROM mcp_configs WHERE 1=1';
    const params = [];

    if (userId) {
      query += ' AND user_id = ?';
      params.push(userId);
    }

    query += ' ORDER BY created_at DESC';

    const rows = await db.fetchall(query, params);
    return rows.map(row => McpConfig.fromDb(row));
  }

  /**
   * 获取已启用的配置（异步）
   */
  static async getEnabled(userId = null) {
    const db = getDatabaseSync();
    let query = 'SELECT * FROM mcp_configs WHERE enabled = 1';
    const params = [];

    if (userId) {
      query += ' AND user_id = ?';
      params.push(userId);
    }

    query += ' ORDER BY created_at DESC';

    const rows = await db.fetchall(query, params);
    return rows.map(row => McpConfig.fromDb(row));
  }

  /**
   * 更新配置（异步）
   */
  static async update(configId, updates) {
    const db = getDatabaseSync();
    const setClause = [];
    const params = [];

    const allowedFields = ['name', 'command', 'type', 'args', 'env', 'cwd', 'enabled'];

    for (const field of allowedFields) {
      if (updates[field] !== undefined) {
        setClause.push(`${field} = ?`);

        if (field === 'args' || field === 'env') {
          params.push(JSON.stringify(updates[field]));
        } else if (field === 'enabled') {
          params.push(updates[field] ? 1 : 0);
        } else {
          params.push(updates[field]);
        }
      }
    }

    setClause.push('updated_at = ?');
    params.push(new Date().toISOString());

    params.push(configId);

    const query = `UPDATE mcp_configs SET ${setClause.join(', ')} WHERE id = ?`;
    await db.execute(query, params);
  }

  /**
   * 删除配置（异步）
   */
  static async delete(configId) {
    const db = getDatabaseSync();
    await db.execute('DELETE FROM mcp_configs WHERE id = ?', [configId]);
  }
}
