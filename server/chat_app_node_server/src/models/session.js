/**
 * Session 数据模型 - 会话管理
 * 复刻自 Python: app/models/session.py
 */

import { v4 as uuidv4 } from 'uuid';
import { getDatabaseSync } from './database-factory.js';

/**
 * Session 模型类
 */
export class Session {
  constructor(data) {
    this.id = data.id || uuidv4();
    this.title = data.title;
    this.description = data.description || null;
    this.metadata = data.metadata || null;
    this.user_id = data.user_id || null;
    this.project_id = data.project_id || null;
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at || new Date().toISOString();
  }

  /**
   * 转换为数据库格式
   */
  toDb() {
    return {
      id: this.id,
      title: this.title,
      description: this.description,
      metadata: this.metadata ? JSON.stringify(this.metadata) : null,
      user_id: this.user_id,
      project_id: this.project_id,
      created_at: this.created_at,
      updated_at: this.updated_at
    };
  }

  /**
   * 从数据库行创建实例
   */
  static fromDb(row) {
    if (!row) return null;
    return new Session({
      ...row,
      metadata: row.metadata ? JSON.parse(row.metadata) : null
    });
  }
}

/**
 * Session 服务类
 */
export class SessionService {
  /**
   * 创建会话（异步）
   */
  static async create(sessionData) {
    const session = new Session(sessionData);
    const db = getDatabaseSync();
    const dbData = session.toDb();

    await db.execute(
      `INSERT INTO sessions (id, title, description, metadata, user_id, project_id, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        dbData.id,
        dbData.title,
        dbData.description,
        dbData.metadata,
        dbData.user_id,
        dbData.project_id,
        dbData.created_at,
        dbData.updated_at
      ]
    );

    return session.id;
  }

  /**
   * 创建会话（同步）
   */
  static createSync(sessionData) {
    const session = new Session(sessionData);
    const db = getDatabaseSync();
    const dbData = session.toDb();

    db.executeSync(
      `INSERT INTO sessions (id, title, description, metadata, user_id, project_id, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        dbData.id,
        dbData.title,
        dbData.description,
        dbData.metadata,
        dbData.user_id,
        dbData.project_id,
        dbData.created_at,
        dbData.updated_at
      ]
    );

    return session.id;
  }

  /**
   * 根据 ID 获取会话（异步）
   */
  static async getById(sessionId) {
    const db = getDatabaseSync();
    const row = await db.fetchone('SELECT * FROM sessions WHERE id = ?', [sessionId]);
    return Session.fromDb(row);
  }

  /**
   * 获取所有会话（异步）
   */
  static async getAll() {
    const db = getDatabaseSync();
    const rows = await db.fetchall('SELECT * FROM sessions ORDER BY created_at DESC');
    return rows.map(row => Session.fromDb(row));
  }

  /**
   * 根据用户和项目获取会话（异步）
   */
  static async getByUserProject(userId = null, projectId = null) {
    const db = getDatabaseSync();
    let query = 'SELECT * FROM sessions WHERE 1=1';
    const params = [];

    if (userId) {
      query += ' AND user_id = ?';
      params.push(userId);
    }

    if (projectId) {
      query += ' AND project_id = ?';
      params.push(projectId);
    }

    query += ' ORDER BY created_at DESC';

    const rows = await db.fetchall(query, params);
    return rows.map(row => Session.fromDb(row));
  }

  /**
   * 删除会话（异步）
   */
  static async delete(sessionId) {
    const db = getDatabaseSync();
    await db.execute('DELETE FROM sessions WHERE id = ?', [sessionId]);
  }

  /**
   * 更新会话（异步）
   */
  static async update(sessionId, updates) {
    const db = getDatabaseSync();
    const setClause = [];
    const params = [];

    if (updates.title !== undefined) {
      setClause.push('title = ?');
      params.push(updates.title);
    }

    if (updates.description !== undefined) {
      setClause.push('description = ?');
      params.push(updates.description);
    }

    if (updates.metadata !== undefined) {
      setClause.push('metadata = ?');
      params.push(JSON.stringify(updates.metadata));
    }

    setClause.push('updated_at = ?');
    params.push(new Date().toISOString());

    params.push(sessionId);

    const query = `UPDATE sessions SET ${setClause.join(', ')} WHERE id = ?`;
    await db.execute(query, params);
  }
}
