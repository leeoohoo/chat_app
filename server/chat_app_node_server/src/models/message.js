/**
 * Message 数据模型 - 消息管理
 * 复刻自 Python: app/models/message.py
 */

import { v4 as uuidv4 } from 'uuid';
import { getDatabaseSync } from './database-factory.js';

/**
 * Message 模型类
 */
export class Message {
  constructor(data) {
    this.id = data.id || uuidv4();
    this.sessionId = data.sessionId;
    this.role = data.role; // user, assistant, tool
    this.content = data.content;
    this.summary = data.summary || null;
    this.toolCalls = data.toolCalls || null;
    this.tool_call_id = data.tool_call_id || null;
    this.reasoning = data.reasoning || null;
    this.metadata = data.metadata || null;
    this.created_at = data.created_at || new Date().toISOString();
  }

  /**
   * 转换为数据库格式
   */
  toDb() {
    return {
      id: this.id,
      session_id: this.sessionId,
      role: this.role,
      content: this.content,
      summary: this.summary,
      tool_calls: this.toolCalls ? JSON.stringify(this.toolCalls) : null,
      tool_call_id: this.tool_call_id,
      reasoning: this.reasoning,
      metadata: this.metadata ? JSON.stringify(this.metadata) : null,
      created_at: this.created_at
    };
  }

  /**
   * 从数据库行创建实例
   */
  static fromDb(row) {
    if (!row) return null;
    return new Message({
      id: row.id,
      sessionId: row.session_id,
      role: row.role,
      content: row.content,
      summary: row.summary,
      toolCalls: row.tool_calls ? JSON.parse(row.tool_calls) : null,
      tool_call_id: row.tool_call_id,
      reasoning: row.reasoning,
      metadata: row.metadata ? JSON.parse(row.metadata) : null,
      created_at: row.created_at
    });
  }

  /**
   * 转换为 OpenAI API 格式
   */
  toOpenAI() {
    if (this.role === 'tool') {
      return {
        role: 'tool',
        tool_call_id: this.tool_call_id,
        content: this.content
      };
    }

    const message = {
      role: this.role,
      content: this.content
    };

    if (this.toolCalls && this.toolCalls.length > 0) {
      message.tool_calls = this.toolCalls;
    }

    return message;
  }
}

/**
 * Message 服务类
 */
export class MessageService {
  /**
   * 创建消息（异步）
   */
  static async create(messageData) {
    const message = new Message(messageData);
    const db = getDatabaseSync();
    const dbData = message.toDb();

    await db.execute(
      `INSERT INTO messages (id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        dbData.id,
        dbData.session_id,
        dbData.role,
        dbData.content,
        dbData.summary,
        dbData.tool_calls,
        dbData.tool_call_id,
        dbData.reasoning,
        dbData.metadata,
        dbData.created_at
      ]
    );

    return message;
  }

  /**
   * 创建消息（同步）
   */
  static createSync(messageData) {
    const message = new Message(messageData);
    const db = getDatabaseSync();
    const dbData = message.toDb();

    db.executeSync(
      `INSERT INTO messages (id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        dbData.id,
        dbData.session_id,
        dbData.role,
        dbData.content,
        dbData.summary,
        dbData.tool_calls,
        dbData.tool_call_id,
        dbData.reasoning,
        dbData.metadata,
        dbData.created_at
      ]
    );

    return message;
  }

  /**
   * 根据 ID 获取消息（异步）
   */
  static async getById(messageId) {
    const db = getDatabaseSync();
    const row = await db.fetchone('SELECT * FROM messages WHERE id = ?', [messageId]);
    return Message.fromDb(row);
  }

  /**
   * 获取会话的所有消息（异步）
   */
  static async getBySession(sessionId, limit = null, offset = 0) {
    const db = getDatabaseSync();
    let query = 'SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC';
    const params = [sessionId];

    if (limit) {
      query += ' LIMIT ? OFFSET ?';
      params.push(limit, offset);
    }

    const rows = await db.fetchall(query, params);
    return rows.map(row => Message.fromDb(row));
  }

  /**
   * 获取会话的最近 N 条消息（异步）
   */
  static async getRecentBySession(sessionId, limit = 10) {
    const db = getDatabaseSync();
    const rows = await db.fetchall(
      `SELECT * FROM messages
       WHERE session_id = ?
       ORDER BY created_at DESC
       LIMIT ?`,
      [sessionId, limit]
    );
    return rows.reverse().map(row => Message.fromDb(row));
  }

  /**
   * 获取会话的最近 N 条消息（支持偏移量，用于分页“加载更多”）
   * 语义：按 created_at DESC 做分页，再反转为 ASC 返回
   */
  static async getRecentPageBySession(sessionId, limit = 10, offset = 0) {
    const db = getDatabaseSync();
    const rows = await db.fetchall(
      `SELECT * FROM messages
       WHERE session_id = ?
       ORDER BY created_at DESC
       LIMIT ? OFFSET ?`,
      [sessionId, limit, offset]
    );
    return rows.reverse().map(row => Message.fromDb(row));
  }

  /**
   * 删除消息（异步）
   */
  static async delete(messageId) {
    const db = getDatabaseSync();
    await db.execute('DELETE FROM messages WHERE id = ?', [messageId]);
  }

  /**
   * 删除会话的所有消息（异步）
   */
  static async deleteBySession(sessionId) {
    const db = getDatabaseSync();
    await db.execute('DELETE FROM messages WHERE session_id = ?', [sessionId]);
  }

  /**
   * 统计会话的消息数量（异步）
   */
  static async countBySession(sessionId) {
    const db = getDatabaseSync();
    const result = await db.fetchone(
      'SELECT COUNT(*) as count FROM messages WHERE session_id = ?',
      [sessionId]
    );
    return result.count;
  }

  /**
   * 将消息列表转换为 OpenAI API 格式
   */
  static toOpenAIFormat(messages) {
    return messages.map(msg => msg.toOpenAI());
  }
}
