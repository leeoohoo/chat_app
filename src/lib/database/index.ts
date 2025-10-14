import { apiClient } from '../api/client';
import type { Session, Message } from './mock';

// 数据库初始化
export function initDatabase(): Promise<void> {
  console.log('API client initialized');
  return Promise.resolve();
}



// 关闭数据库连接
export function closeDatabase(): Promise<void> {
  console.log('Mock database closed');
  return Promise.resolve();
}

// 数据库服务类
export class DatabaseService {
  private userId: string;
  private projectId: string;

  constructor(userId: string, projectId: string) {
    this.userId = userId;
    this.projectId = projectId;
  }

  // 会话相关操作
  async createSession(data: Omit<Session, 'id'>): Promise<Session> {
    const sessionData = { id: crypto.randomUUID(), title: data.title, user_id: this.userId, project_id: this.projectId };
    const session = await apiClient.createSession(sessionData);
    return {
      id: session.id,
      title: session.title,
      createdAt: new Date(session.created_at),
      updatedAt: new Date(session.updated_at),
      messageCount: 0,
      tokenUsage: 0,
      pinned: false,
      archived: false,
      tags: null,
      metadata: null
    };
  }

  async getSession(id: string): Promise<Session | null> {
    try {
      const session = await apiClient.getSession(id);
      if (!session) return null;
      return {
        id: session.id,
        title: session.title,
        createdAt: new Date(session.created_at),
        updatedAt: new Date(session.updated_at),
        messageCount: 0,
        tokenUsage: 0,
        pinned: false,
        archived: false,
        tags: null,
        metadata: null
      };
    } catch (error) {
      return null;
    }
  }

  async getAllSessions(): Promise<Session[]> {
    console.log('🔍 DatabaseService.getAllSessions 调用:', { userId: this.userId, projectId: this.projectId });
    
    const sessions = await apiClient.getSessions(this.userId, this.projectId);
    console.log('🔍 API返回的会话数据:', sessions);
    
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    const formattedSessions = sessions.map((session: any) => ({
      id: session.id,
      title: session.title,
      createdAt: new Date(session.created_at || session.createdAt),
      updatedAt: new Date(session.updated_at || session.updatedAt),
      messageCount: 0, // 默认值，可以后续优化
      tokenUsage: 0, // 默认值，可以后续优化
      pinned: false, // 默认值
      archived: false, // 默认值
      tags: null,
      metadata: null
    }));
    
    console.log('🔍 格式化后的会话数据:', formattedSessions);
    return formattedSessions;
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
    const messageData = {
      id: crypto.randomUUID(),
      session_id: data.sessionId,
      role: data.role,
      content: data.content,
      summary: data.rawContent,
      tool_calls: data.metadata?.toolCalls ? JSON.stringify(data.metadata.toolCalls) : undefined,
      tool_call_id: data.toolCallId,
      reasoning: undefined,
      metadata: data.metadata ? JSON.stringify(data.metadata) : undefined
    };
    const messageRequestData = {
      id: messageData.id,
      sessionId: messageData.session_id,
      role: messageData.role,
      content: messageData.content,
      metadata: messageData.metadata ? (typeof messageData.metadata === 'string' ? JSON.parse(messageData.metadata) : messageData.metadata) : undefined,
      toolCalls: messageData.tool_calls ? (typeof messageData.tool_calls === 'string' ? JSON.parse(messageData.tool_calls) : messageData.tool_calls) : undefined
    };
    const result = await apiClient.createMessage(messageRequestData);
    return {
      id: result.id,
      sessionId: result.session_id,
      role: result.role as any,
      content: result.content,
      rawContent: result.summary,
      tokensUsed: data.tokensUsed,
      status: data.status || 'completed',
      createdAt: new Date(result.created_at),
      updatedAt: data.updatedAt,
      toolCallId: result.tool_call_id,
      metadata: result.metadata ? (typeof result.metadata === 'string' ? JSON.parse(result.metadata) : result.metadata) : data.metadata
    };
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const messages = await apiClient.getSessionMessages(sessionId);
    return messages.map(message => ({
      id: message.id,
      sessionId: message.session_id,
      role: message.role as any,
      content: message.content,
      rawContent: message.summary,
      tokensUsed: undefined,
      status: 'completed' as const,
      createdAt: new Date(message.created_at),
      updatedAt: undefined,
      toolCallId: message.tool_call_id,
      metadata: message.metadata ? (typeof message.metadata === 'string' ? JSON.parse(message.metadata) : message.metadata) : undefined
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

// 导出类型
export type { Session, Message };