// API客户端，用于连接后端服务
// 使用相对路径，让浏览器自动处理协议和域名
const API_BASE_URL = '/api';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 检查响应是否有内容
      const text = await response.text();
      if (!text) {
        return {} as T; // 返回空对象而不是尝试解析空字符串
      }
      
      try {
        return JSON.parse(text);
      } catch (parseError) {
        console.error(`JSON parse error for ${endpoint}:`, parseError, 'Response text:', text);
        throw new Error(`Invalid JSON response: ${text}`);
      }
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // 会话相关API
  async getSessions(userId?: string, projectId?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (userId) params.append('userId', userId);
    if (projectId) params.append('projectId', projectId);
    const queryString = params.toString();
    console.log('🔍 getSessions API调用:', { userId, projectId, queryString });
    return this.request<any[]>(`/sessions${queryString ? `?${queryString}` : ''}`);
  }

  async createSession(data: { id: string; title: string; userId: string; projectId: string }): Promise<any> {
    console.log('🔍 createSession API调用:', data);
    return this.request<any>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getSession(id: string): Promise<any> {
    return this.request<any>(`/sessions/${id}`);
  }

  async deleteSession(id: string): Promise<any> {
    return this.request<any>(`/sessions/${id}`, {
      method: 'DELETE',
    });
  }

  async getSessionMessages(sessionId: string): Promise<any[]> {
    return this.request<any[]>(`/sessions/${sessionId}/messages`);
  }

  // 消息相关API
  async createMessage(data: {
    id: string;
    sessionId: string;
    role: string;
    content: string;
    metadata?: any;
    toolCalls?: any[];
    createdAt?: Date;
    status?: string;
  }): Promise<any> {
    const requestData = {
      ...data,
      createdAt: data.createdAt ? data.createdAt.toISOString() : undefined
    };
    return this.request<any>('/messages', {
      method: 'POST',
      body: JSON.stringify(requestData),
    });
  }

  // MCP配置相关API
  async getMcpConfigs(userId?: string) {
    const params = userId ? `?userId=${encodeURIComponent(userId)}` : '';
    console.log('🔍 getMcpConfigs API调用:', { userId, params });
    return this.request(`/mcp-configs${params}`);
  }

  async createMcpConfig(data: {
    id: string;
    name: string;
    command: string;
    args?: any;
    env?: any;
    enabled: boolean;
    userId?: string;
  }) {
    console.log('🔍 API client createMcpConfig 调用:', data);
    return this.request('/mcp-configs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMcpConfig(id: string, data: any) {
    console.log('🔍 API client updateMcpConfig 调用:', { id, data });
    return this.request(`/mcp-configs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMcpConfig(id: string) {
    return this.request(`/mcp-configs/${id}`, {
      method: 'DELETE',
    });
  }

  // AI模型配置相关API
  async getAiModelConfigs(userId?: string) {
    const params = userId ? `?userId=${encodeURIComponent(userId)}` : '';
    console.log('🔍 getAiModelConfigs API调用:', { userId, params });
    return this.request(`/ai-model-configs${params}`);
  }

  async createAiModelConfig(data: {
    id: string;
    name: string;
    provider: string;
    model: string;
    apiKey: string;
    baseUrl: string;
    userId?: string;
    enabled: boolean;
  }) {
    return this.request('/ai-model-configs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAiModelConfig(id: string, data: any) {
    return this.request(`/ai-model-configs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteAiModelConfig(id: string) {
    return this.request(`/ai-model-configs/${id}`, {
      method: 'DELETE',
    });
  }

  // 系统上下文相关API
  async getSystemContexts(userId: string): Promise<any[]> {
    return this.request<any[]>(`/system-contexts?userId=${userId}`);
  }

  async getActiveSystemContext(userId: string): Promise<{ content: string; context: any }> {
    return this.request<{ content: string; context: any }>(`/system-context/active?userId=${userId}`);
  }

  async createSystemContext(data: {
    name: string;
    content: string;
    userId: string;
  }): Promise<any> {
    return this.request<any>('/system-contexts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSystemContext(id: string, data: {
    name: string;
    content: string;
  }): Promise<any> {
    return this.request<any>(`/system-contexts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSystemContext(id: string): Promise<void> {
    return this.request<void>(`/system-contexts/${id}`, {
      method: 'DELETE',
    });
  }

  async activateSystemContext(id: string, userId: string): Promise<any> {
    return this.request<any>(`/system-contexts/${id}/activate`, {
      method: 'POST',
      body: JSON.stringify({ userId }),
    });
  }

  // 会话详情和助手相关API (从index.ts合并)
  async getConversationDetails(conversationId: string) {
    try {
      const session = await this.request<any>(`/sessions/${conversationId}`);
      return {
        data: {
          conversation: {
            id: session.id,
            title: session.title,
            created_at: session.created_at,
            updated_at: session.updated_at
          }
        }
      };
    } catch (error) {
      console.error('Failed to get conversation details:', error);
      // 返回默认值以保持兼容性
      return {
        data: {
          conversation: {
            id: conversationId,
            title: 'Default Conversation',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
        }
      };
    }
  }

  async getAssistant(_conversationId: string) {
    try {
      // 获取AI模型配置
      const configs = await this.request<any[]>('/ai-model-configs');
      const defaultConfig = configs.find((config: any) => config.enabled) || configs[0];
      
      if (!defaultConfig) {
        throw new Error('No AI model configuration found');
      }

      return {
        data: {
          assistant: {
            id: defaultConfig.id,
            name: defaultConfig.name,
            model_config: {
              model_name: defaultConfig.model_name,
              temperature: 0.7,
              max_tokens: 4000,
              api_key: defaultConfig.api_key,
              base_url: defaultConfig.base_url
            }
          }
        }
      };
    } catch (error) {
      console.error('Failed to get assistant:', error);
      // 返回默认值以保持兼容性
      return {
        data: {
          assistant: {
            id: 'default-assistant',
            name: 'AI Assistant',
            model_config: {
              model_name: 'gpt-3.5-turbo',
              temperature: 0.7,
              max_tokens: 4000,
              api_key: import.meta.env.VITE_OPENAI_API_KEY || '',
              base_url: 'https://api.openai.com/v1'
            }
          }
        }
      };
    }
  }

  async getMcpServers(_conversationId?: string) {
    try {
      // 直接获取全局MCP配置，而不是基于会话的配置
      const mcpConfigs = await this.request<any[]>('/mcp-configs');
      // 只返回启用的MCP服务器，并转换数据格式
      const enabledServers = mcpConfigs
        .filter((config: any) => config.enabled)
        .map((config: any) => ({
          name: config.name,
          url: config.command // 后端使用command字段存储URL
        }));
      return {
        data: {
          mcp_servers: enabledServers
        }
      };
    } catch (error) {
      console.error('Failed to get MCP servers:', error);
      return {
        data: {
          mcp_servers: []
        }
      };
    }
  }

  async saveMessage(conversationId: string, message: any) {
    try {
      // 生成唯一ID
      const messageId = message.id || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      const savedMessage = await this.request<any>(`/messages`, {
        method: 'POST',
        body: JSON.stringify({
          id: messageId,
          sessionId: conversationId,
          role: message.role,
          content: message.content,
          toolCalls: message.tool_calls || null,
          toolCallId: message.tool_call_id || null,
          reasoning: message.reasoning || null,
          metadata: message.metadata || null
        })
      });
      
      return {
        data: {
          message: savedMessage
        }
      };
    } catch (error) {
      console.error('Failed to save message:', error);
      // 返回模拟数据以保持兼容性
      return {
        data: {
          message: {
            ...message,
            id: Date.now().toString(),
            created_at: new Date().toISOString()
          }
        }
      };
    }
  }

  async getMessages(conversationId: string, _params: any = {}) {
    try {
      const messages = await this.request<any[]>(`/sessions/${conversationId}/messages`);
      return {
        data: {
          messages: messages
        }
      };
    } catch (error) {
      console.error('Failed to get messages:', error);
      return {
        data: {
          messages: []
        }
      };
    }
  }

  async addMessage(conversationId: string, message: any) {
    return this.saveMessage(conversationId, message);
  }
}

// 导出单例实例
export const apiClient = new ApiClient();

// 为了保持向后兼容性，导出conversationsApi对象
export const conversationsApi = {
  getDetails: (conversationId: string) => apiClient.getConversationDetails(conversationId),
  getAssistant: (conversationId: string) => apiClient.getAssistant(conversationId),
  getMcpServers: (conversationId?: string) => apiClient.getMcpServers(conversationId),
  saveMessage: (conversationId: string, message: any) => apiClient.saveMessage(conversationId, message),
  getMessages: (conversationId: string, params?: any) => apiClient.getMessages(conversationId, params),
  addMessage: (conversationId: string, message: any) => apiClient.addMessage(conversationId, message)
};

export default ApiClient;