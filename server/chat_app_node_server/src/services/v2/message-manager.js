/**
 * 消息管理器 - 负责处理聊天消息的保存、检索和管理
 * 复刻自 Python: app/services/v2/message_manager.py
 */

import { MessageService } from '../../models/message.js';
import { logger } from '../../utils/logger.js';

export class MessageManager {
  constructor() {
    // 缓存最近保存的消息
    this.recentMessages = new Map();

    // 待保存的消息队列
    this.pendingSaves = [];

    // 统计信息
    this.stats = {
      messages_saved: 0,
      messages_retrieved: 0,
      cache_hits: 0,
      cache_misses: 0
    };
  }

  /**
   * 保存用户消息
   */
  saveUserMessage(sessionId, content, messageId = null) {
    try {
      // 创建并保存消息
      const savedMessage = MessageService.createSync({
        id: messageId,
        sessionId,
        role: 'user',
        content
      });

      // 缓存消息
      if (savedMessage) {
        this._cacheMessage(savedMessage);
        this.stats.messages_saved += 1;
      }

      return {
        success: true,
        message: savedMessage,
        message_id: savedMessage?.id
      };
    } catch (error) {
      const errorMessage = `保存用户消息失败: ${error.message}`;
      logger.error(errorMessage, error);
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 保存助手消息
   */
  saveAssistantMessage(sessionId, content, options = {}) {
    try {
      const {
        messageId = null,
        summary = null,
        reasoning = null,
        metadata = null,
        toolCalls = null
      } = options;

      // 创建并保存消息
      const savedMessage = MessageService.createSync({
        id: messageId,
        sessionId,
        role: 'assistant',
        content,
        summary,
        reasoning,
        metadata,
        toolCalls
      });

      // 缓存消息
      if (savedMessage) {
        this._cacheMessage(savedMessage);
        this.stats.messages_saved += 1;
      }

      return {
        success: true,
        message: savedMessage,
        message_id: savedMessage?.id
      };
    } catch (error) {
      const errorMessage = `保存助手消息失败: ${error.message}`;
      logger.error(errorMessage, error);
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 保存工具消息
   */
  saveToolMessage(sessionId, content, toolCallId, options = {}) {
    try {
      const { messageId = null, metadata = null } = options;

      // 创建并保存消息
      const savedMessage = MessageService.createSync({
        id: messageId,
        sessionId,
        role: 'tool',
        content,
        tool_call_id: toolCallId,
        metadata
      });

      // 缓存消息
      if (savedMessage) {
        this._cacheMessage(savedMessage);
        this.stats.messages_saved += 1;
      }

      return {
        success: true,
        message: savedMessage,
        message_id: savedMessage?.id
      };
    } catch (error) {
      const errorMessage = `保存工具消息失败: ${error.message}`;
      logger.error(errorMessage, error);
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 获取会话消息（异步）
   */
  async getSessionMessages(sessionId, limit = null) {
    try {
      const messages = await MessageService.getBySession(sessionId, limit);
      this.stats.messages_retrieved += messages.length;
      return messages;
    } catch (error) {
      logger.error(`获取会话消息失败: ${error.message}`, error);
      return [];
    }
  }

  /**
   * 获取会话消息（同步） - 用于与 Python 版本对齐
   */
  getSessionMessagesSync(sessionId, limit = null) {
    try {
      const db = require('../../models/database-factory.js').getDatabaseSync();
      let query = 'SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC';
      const params = [sessionId];

      if (limit) {
        query += ' LIMIT ?';
        params.push(limit);
      }

      const rows = db.fetchallSync(query, params);
      const messages = rows.map(row => {
        return {
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
        };
      });

      this.stats.messages_retrieved += messages.length;
      return messages;
    } catch (error) {
      logger.error(`获取会话消息失败: ${error.message}`, error);
      return [];
    }
  }

  /**
   * 根据 ID 获取消息
   */
  async getMessageById(messageId) {
    try {
      // 先检查缓存
      if (this.recentMessages.has(messageId)) {
        this.stats.cache_hits += 1;
        return this.recentMessages.get(messageId);
      }

      // 从数据库获取
      const message = await MessageService.getById(messageId);

      if (message) {
        this._cacheMessage(message);
        this.stats.cache_misses += 1;
        this.stats.messages_retrieved += 1;
      }

      return message;
    } catch (error) {
      logger.error(`获取消息失败: ${error.message}`, error);
      return null;
    }
  }

  /**
   * 处理待保存的消息
   */
  processPendingSaves() {
    try {
      if (this.pendingSaves.length === 0) {
        return {
          success: true,
          processed_count: 0,
          message: '没有待保存的消息'
        };
      }

      let processedCount = 0;
      const errors = [];

      // 处理所有待保存的消息
      for (const messageData of this.pendingSaves) {
        try {
          const savedMessage = MessageService.createSync(messageData);
          if (savedMessage) {
            this._cacheMessage(savedMessage);
            processedCount += 1;
            this.stats.messages_saved += 1;
          }
        } catch (error) {
          errors.push(`保存消息失败: ${error.message}`);
        }
      }

      // 清空待保存队列
      this.pendingSaves = [];

      return {
        success: errors.length === 0,
        processed_count: processedCount,
        errors
      };
    } catch (error) {
      const errorMessage = `处理待保存消息失败: ${error.message}`;
      logger.error(errorMessage, error);
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 缓存消息
   */
  _cacheMessage(message) {
    if (message && message.id) {
      // 限制缓存大小
      if (this.recentMessages.size >= 100) {
        // 移除最旧的消息（Map 的第一个键）
        const firstKey = this.recentMessages.keys().next().value;
        this.recentMessages.delete(firstKey);
      }

      this.recentMessages.set(message.id, message);
    }
  }

  /**
   * 清空缓存
   */
  clearCache() {
    this.recentMessages.clear();
  }

  /**
   * 清空指定会话的缓存消息
   */
  clearCacheForSession(sessionId) {
    try {
      if (this.recentMessages.size === 0) {
        return;
      }

      // 找出属于该会话的消息 ID
      const toDelete = [];
      for (const [messageId, message] of this.recentMessages.entries()) {
        if (message.sessionId === sessionId) {
          toDelete.push(messageId);
        }
      }

      // 删除这些消息
      for (const messageId of toDelete) {
        this.recentMessages.delete(messageId);
      }
    } catch (error) {
      logger.error(`清空会话缓存失败: ${error.message}`, error);
    }
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return {
      stats: { ...this.stats },
      cache_size: this.recentMessages.size,
      pending_saves: this.pendingSaves.length
    };
  }

  /**
   * 获取缓存统计信息（与 AiClient 接口对齐）
   */
  getCacheStats() {
    const sessionCounts = {};

    for (const message of this.recentMessages.values()) {
      const sessionId = message.sessionId;
      if (sessionId) {
        sessionCounts[sessionId] = (sessionCounts[sessionId] || 0) + 1;
      }
    }

    return {
      cache_size: this.recentMessages.size,
      by_session: sessionCounts
    };
  }
}
