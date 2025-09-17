// 数据库适配器 - 根据环境自动选择HTTP API或直接数据库调用
import { apiClient } from '../api/client';
import { sharedDatabaseService, type Session, type Message, type McpConfig, type AiModelConfig } from './shared-service';

// 环境检测
const isServer = typeof window === 'undefined';
const isElectron = typeof window !== 'undefined' && (window as any).electronAPI;

// 统一的数据库接口
export interface DatabaseAdapter {
  // 会话相关
  getAllSessions(): Promise<Session[]>;
  createSession(id: string, title: string): Promise<Session>;
  getSession(id: string): Promise<Session | null>;
  deleteSession(id: string): Promise<void>;
  
  // 消息相关
  getSessionMessages(sessionId: string): Promise<Message[]>;
  createMessage(messageData: Omit<Message, 'created_at'>): Promise<Message>;
  
  // MCP配置相关
  getMcpConfigs(): Promise<McpConfig[]>;
  createMcpConfig(config: Omit<McpConfig, 'created_at'>): Promise<McpConfig>;
  updateMcpConfig(id: string, updates: Partial<McpConfig>): Promise<McpConfig>;
  deleteMcpConfig(id: string): Promise<void>;
  
  // AI模型配置相关
  getAiModelConfigs(): Promise<AiModelConfig[]>;
  createAiModelConfig(config: Omit<AiModelConfig, 'created_at'>): Promise<void>;
  updateAiModelConfig(id: string, updates: Partial<AiModelConfig>): Promise<void>;
  deleteAiModelConfig(id: string): Promise<void>;
  
  // 系统上下文相关
  getSystemContext(): Promise<{ content: string }>;
  updateSystemContext(content: string): Promise<void>;
}

// HTTP API 适配器实现
class HttpApiAdapter implements DatabaseAdapter {
  async getAllSessions(): Promise<Session[]> {
    const sessions = await apiClient.getSessions();
    return sessions.map(session => ({
      ...session,
      created_at: session.createdAt || session.created_at,
      updated_at: session.updatedAt || session.updated_at
    }));
  }

  async createSession(id: string, title: string): Promise<Session> {
    const session = await apiClient.createSession({ id, title });
    return {
      ...session,
      created_at: session.createdAt || session.created_at,
      updated_at: session.updatedAt || session.updated_at
    };
  }

  async getSession(id: string): Promise<Session | null> {
    try {
      const session = await apiClient.getSession(id);
      return {
        ...session,
        created_at: session.createdAt || session.created_at,
        updated_at: session.updatedAt || session.updated_at
      };
    } catch (error) {
      return null;
    }
  }

  async deleteSession(id: string): Promise<void> {
    await apiClient.deleteSession(id);
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    const messages = await apiClient.getSessionMessages(sessionId);
    return messages.map(message => ({
      ...message,
      created_at: message.createdAt || message.created_at
    }));
  }

  async createMessage(messageData: Omit<Message, 'created_at'>): Promise<Message> {
    const message = await apiClient.createMessage({
      id: messageData.id,
      sessionId: messageData.session_id,
      role: messageData.role,
      content: messageData.content,
      toolCalls: messageData.tool_calls ? JSON.parse(messageData.tool_calls) : undefined,
      metadata: messageData.metadata ? JSON.parse(messageData.metadata) : undefined
    });
    return {
      ...message,
      session_id: message.sessionId || messageData.session_id,
      tool_calls: message.toolCalls ? JSON.stringify(message.toolCalls) : null,
      tool_call_id: message.toolCallId || null,
      metadata: message.metadata ? JSON.stringify(message.metadata) : null,
      created_at: message.createdAt || message.created_at
    };
  }

  async getMcpConfigs(): Promise<McpConfig[]> {
    const configs = await apiClient.getMcpConfigs();
    return configs as McpConfig[];
  }

  async createMcpConfig(config: Omit<McpConfig, 'created_at'>): Promise<McpConfig> {
    const result = await apiClient.createMcpConfig(config);
    return result as McpConfig;
  }

  async updateMcpConfig(id: string, updates: Partial<McpConfig>): Promise<McpConfig> {
    const result = await apiClient.updateMcpConfig(id, updates);
    return result as McpConfig;
  }

  async deleteMcpConfig(id: string): Promise<void> {
    await apiClient.deleteMcpConfig(id);
  }

  async getAiModelConfigs(): Promise<AiModelConfig[]> {
    // 注意：apiClient 目前没有 AI 模型配置相关的方法
    // 这里返回空数组，实际使用时需要添加对应的 API
    console.warn('AI模型配置API尚未在apiClient中实现');
    return [];
  }

  async createAiModelConfig(config: Omit<AiModelConfig, 'created_at'>): Promise<void> {
    console.warn('AI模型配置API尚未在apiClient中实现');
    // 实际实现需要在 apiClient 中添加对应方法
  }

  async updateAiModelConfig(id: string, updates: Partial<AiModelConfig>): Promise<void> {
    console.warn('AI模型配置API尚未在apiClient中实现');
    // 实际实现需要在 apiClient 中添加对应方法
  }

  async deleteAiModelConfig(id: string): Promise<void> {
    console.warn('AI模型配置API尚未在apiClient中实现');
    // 实际实现需要在 apiClient 中添加对应方法
  }

  async getSystemContext(): Promise<{ content: string }> {
    return await apiClient.getSystemContext();
  }

  async updateSystemContext(content: string): Promise<void> {
    await apiClient.updateSystemContext(content);
  }
}

// 直接数据库适配器实现
class DirectDatabaseAdapter implements DatabaseAdapter {
  private initialized = false;

  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await sharedDatabaseService.init();
      this.initialized = true;
    }
  }

  async getAllSessions(): Promise<Session[]> {
    await this.ensureInitialized();
    return await sharedDatabaseService.getAllSessions();
  }

  async createSession(id: string, title: string): Promise<Session> {
    await this.ensureInitialized();
    return await sharedDatabaseService.createSession(id, title);
  }

  async getSession(id: string): Promise<Session | null> {
    await this.ensureInitialized();
    return await sharedDatabaseService.getSession(id);
  }

  async deleteSession(id: string): Promise<void> {
    await this.ensureInitialized();
    await sharedDatabaseService.deleteSession(id);
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    await this.ensureInitialized();
    return await sharedDatabaseService.getSessionMessages(sessionId);
  }

  async createMessage(messageData: Omit<Message, 'created_at'>): Promise<Message> {
    await this.ensureInitialized();
    return await sharedDatabaseService.createMessage(messageData);
  }

  async getMcpConfigs(): Promise<McpConfig[]> {
    await this.ensureInitialized();
    return await sharedDatabaseService.getMcpConfigs();
  }

  async createMcpConfig(config: Omit<McpConfig, 'created_at'>): Promise<McpConfig> {
    await this.ensureInitialized();
    return await sharedDatabaseService.createMcpConfig(config);
  }

  async updateMcpConfig(id: string, updates: Partial<McpConfig>): Promise<McpConfig> {
    await this.ensureInitialized();
    return await sharedDatabaseService.updateMcpConfig(id, updates);
  }

  async deleteMcpConfig(id: string): Promise<void> {
    await this.ensureInitialized();
    await sharedDatabaseService.deleteMcpConfig(id);
  }

  async getAiModelConfigs(): Promise<AiModelConfig[]> {
    await this.ensureInitialized();
    return await sharedDatabaseService.getAiModelConfigs();
  }

  async createAiModelConfig(config: Omit<AiModelConfig, 'created_at'>): Promise<void> {
    await this.ensureInitialized();
    await sharedDatabaseService.createAiModelConfig(config);
  }

  async updateAiModelConfig(id: string, updates: Partial<AiModelConfig>): Promise<void> {
    await this.ensureInitialized();
    await sharedDatabaseService.updateAiModelConfig(id, updates);
  }

  async deleteAiModelConfig(id: string): Promise<void> {
    await this.ensureInitialized();
    await sharedDatabaseService.deleteAiModelConfig(id);
  }

  async getSystemContext(): Promise<{ content: string }> {
    await this.ensureInitialized();
    return await sharedDatabaseService.getSystemContext();
  }

  async updateSystemContext(content: string): Promise<void> {
    await this.ensureInitialized();
    await sharedDatabaseService.updateSystemContext(content);
  }
}

// 根据环境自动选择适配器
function createDatabaseAdapter(): DatabaseAdapter {
  // 在服务器端或Electron环境中使用直接数据库访问
  if (isServer || isElectron) {
    console.log('使用直接数据库访问模式');
    return new DirectDatabaseAdapter();
  }
  
  // 在浏览器环境中使用HTTP API
  console.log('使用HTTP API访问模式');
  return new HttpApiAdapter();
}

// 导出适配器实例
export const databaseAdapter = createDatabaseAdapter();

// 导出类型和工厂函数
export { HttpApiAdapter, DirectDatabaseAdapter, createDatabaseAdapter };