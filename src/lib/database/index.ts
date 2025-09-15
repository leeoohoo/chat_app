import { apiClient } from '../api/client';
import type { Session, Message } from './mock';

// 数据库初始化
export function initDatabase(): Promise<void> {
  console.log('API client initialized');
  return Promise.resolve();
}

// 获取数据库实例
export function getDatabase() {
  return apiClient;
}

// 关闭数据库连接
export function closeDatabase(): Promise<void> {
  console.log('Mock database closed');
  return Promise.resolve();
}

// 数据库服务类
export class DatabaseService {
  constructor() {}

  // 会话相关操作
  async createSession(data: Omit<Session, 'id'>): Promise<Session> {
    const id = Math.random().toString(36).substr(2, 9);
    const sessionData = { id, ...data };
    return await apiClient.createSession(sessionData);
  }

  async getSession(id: string): Promise<Session | null> {
    try {
      const session = await apiClient.getSession(id);
      // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
      return {
        ...session,
        createdAt: session.created_at,
        updatedAt: session.updated_at
      };
    } catch (error) {
      return null;
    }
  }

  async getAllSessions(): Promise<Session[]> {
    const sessions = await apiClient.getSessions();
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    return sessions.map(session => ({
      ...session,
      createdAt: session.created_at,
      updatedAt: session.updated_at
    }));
  }

  async updateSession(_id: string, _updates: Partial<Session>): Promise<Session | null> {
    // TODO: 实现更新会话API
    console.warn('updateSession not implemented yet');
    return null;
  }

  async deleteSession(id: string): Promise<boolean> {
    try {
      await apiClient.deleteSession(id);
      return true;
    } catch (error) {
      return false;
    }
  }

  // 消息相关操作
  async createMessage(data: Omit<Message, 'id'>): Promise<Message> {
    const id = Math.random().toString(36).substr(2, 9);
    const messageData = { id, ...data };
    const result = await apiClient.createMessage(messageData);
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    return {
      ...result,
      createdAt: new Date(result.created_at || result.createdAt),
      updatedAt: result.updated_at ? new Date(result.updated_at) : (result.updatedAt ? new Date(result.updatedAt) : undefined)
    };
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const messages = await apiClient.getSessionMessages(sessionId);
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    return messages.map(message => ({
      ...message,
      createdAt: new Date(message.created_at || message.createdAt),
      updatedAt: message.updated_at ? new Date(message.updated_at) : (message.updatedAt ? new Date(message.updatedAt) : undefined)
    }));
  }

  async updateMessage(_id: string, _updates: Partial<Message>): Promise<Message | null> {
    // TODO: 实现更新消息API
    console.warn('updateMessage not implemented yet');
    return null;
  }

  async deleteMessage(_id: string): Promise<boolean> {
    // TODO: 实现删除消息API
    console.warn('deleteMessage not implemented yet');
    return false;
  }

  // 私有方法：更新会话统计
  // private async updateSessionStats(_sessionId: string): Promise<void> {
  //   const messages = await this.getSessionMessages(_sessionId);
  //   const messageCount = messages.length;
  //   
  //   await this.updateSession(_sessionId, {
  //     messageCount,
  //     updatedAt: new Date()
  //   });
  // }
}

// 导出默认实例
export const databaseService = new DatabaseService();

// 导出类型
export type { Session, Message };