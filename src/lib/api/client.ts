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
    if (userId) params.append('user_id', userId);  // 修复：使用user_id匹配后端参数名
    if (projectId) params.append('project_id', projectId);  // 修复：使用project_id匹配后端参数名
    const queryString = params.toString();
    console.log('🔍 getSessions API调用:', { userId, projectId, queryString });
    return this.request<any[]>(`/sessions${queryString ? `?${queryString}` : ''}`);
  }

  async createSession(data: { id: string; title: string; user_id: string; project_id: string }): Promise<any> {
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
    return this.request<any>(`/sessions/${data.sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify(requestData),
    });
  }

  // MCP配置相关API
  async getMcpConfigs(userId?: string) {
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    console.log('🔍 getMcpConfigs API调用:', { userId, params });
    return this.request(`/mcp-configs${params}`);
  }

  async createMcpConfig(data: {
    id: string;
    name: string;
    command: string;
    type: 'http' | 'stdio';
    args?: string[] | null;
    env?: Record<string, string> | null;
    cwd?: string | null;
    enabled: boolean;
    user_id?: string;
  }) {
    console.log('🔍 API client createMcpConfig 调用:', data);
    return this.request('/mcp-configs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMcpConfig(id: string, data: {
    id?: string;
    name?: string;
    command?: string;
    type?: 'http' | 'stdio';
    args?: string[] | null;
    env?: Record<string, string> | null;
    cwd?: string | null;
    enabled?: boolean;
    userId?: string;
  }) {
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
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    console.log('🔍 getAiModelConfigs API调用:', { userId, params });
    return this.request(`/ai-model-configs${params}`);
  }

  async createAiModelConfig(data: {
    id: string;
    name: string;
    provider: string;
    model: string;
    api_key: string;
    base_url: string;
    user_id?: string;
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
    return this.request<any[]>(`/system-contexts?user_id=${userId}`);
  }

  async getActiveSystemContext(userId: string): Promise<{ content: string; context: any }> {
    return this.request<{ content: string; context: any }>(`/system-context/active?user_id=${userId}`);
  }

  async createSystemContext(data: {
    name: string;
    content: string;
    user_id: string;
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
      body: JSON.stringify({ user_id: userId, is_active: true }),
    });
  }

  // 应用（Application）相关API
  async getApplications(userId?: string): Promise<any[]> {
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    return this.request<any[]>(`/applications${params}`);
  }

  async createApplication(data: {
    name: string;
    url: string;
    icon_url?: string | null;
    user_id?: string;
  }): Promise<any> {
    return this.request<any>('/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateApplication(id: string, data: {
    name?: string;
    url?: string;
    icon_url?: string | null;
  }): Promise<any> {
    return this.request<any>(`/applications/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteApplication(id: string): Promise<any> {
    return this.request<any>(`/applications/${id}`, {
      method: 'DELETE',
    });
  }

  // 智能体（Agent）相关API
  async getAgents(userId?: string): Promise<any[]> {
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    return this.request<any[]>(`/agents${params}`);
  }

  async createAgent(data: {
    name: string;
    description?: string;
    ai_model_config_id: string;
    mcp_config_ids?: string[];
    callable_agent_ids?: string[];
    system_context_id?: string;
    user_id?: string;
    enabled?: boolean;
  }): Promise<any> {
    return this.request<any>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAgent(agentId: string, data: {
    name?: string;
    description?: string;
    ai_model_config_id?: string;
    mcp_config_ids?: string[];
    callable_agent_ids?: string[];
    system_context_id?: string;
    enabled?: boolean;
  }): Promise<any> {
    return this.request<any>(`/agents/${agentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteAgent(agentId: string): Promise<any> {
    return this.request<any>(`/agents/${agentId}`, {
      method: 'DELETE',
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

  async getMcpConfigResource(configId: string): Promise<{ success: boolean; config: any; alias?: string }> {
    try {
      const res = await this.request<any>(`/mcp-configs/${configId}/resource/config`);
      return res;
    } catch (error) {
      console.error('Failed to get MCP config resource:', error);
      return { success: false, config: null } as any;
    }
  }

  async getMcpConfigResourceByCommand(data: {
    type: 'stdio' | 'http';
    command: string;
    args?: string[] | null;
    env?: Record<string, string> | null;
    cwd?: string | null;
    alias?: string | null;
  }): Promise<{ success: boolean; config: any; alias?: string }> {
    try {
      const res = await this.request<any>(`/mcp-configs/resource/config`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return res;
    } catch (error) {
      console.error('Failed to get MCP config resource by command:', error);
      return { success: false, config: null } as any;
    }
  }
  // MCP配置档案（Profiles）相关API
  async getMcpConfigProfiles(configId: string): Promise<any[]> {
    const res = await this.request<any>(`/mcp-configs/${configId}/profiles`);
    // 后端返回结构为 { items: [...] }，此处兼容纯数组与对象包裹两种形式
    if (Array.isArray(res)) {
      return res as any[];
    }
    if (res && typeof res === 'object' && Array.isArray(res.items)) {
      return res.items as any[];
    }
    return [];
  }

  async createMcpConfigProfile(configId: string, data: {
    name: string;
    args?: string[] | null;
    env?: Record<string, string> | null;
    cwd?: string | null;
    enabled?: boolean;
  }): Promise<any> {
    return this.request<any>(`/mcp-configs/${configId}/profiles`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMcpConfigProfile(configId: string, profileId: string, data: {
    name?: string;
    args?: string[] | null;
    env?: Record<string, string> | null;
    cwd?: string | null;
    enabled?: boolean;
  }): Promise<any> {
    return this.request<any>(`/mcp-configs/${configId}/profiles/${profileId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMcpConfigProfile(configId: string, profileId: string): Promise<any> {
    return this.request<any>(`/mcp-configs/${configId}/profiles/${profileId}`, {
      method: 'DELETE',
    });
  }

  async activateMcpConfigProfile(configId: string, profileId: string): Promise<any> {
    return this.request<any>(`/mcp-configs/${configId}/profiles/${profileId}/activate`, {
      method: 'POST',
      body: JSON.stringify({ is_active: true }),
    });
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

  // 流式聊天接口
  async streamChat(sessionId: string, content: string, modelConfig: any, userId?: string): Promise<ReadableStream> {
    const url = `${this.baseUrl}/agent_v2/chat/stream`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        content: content,
        user_id: userId,
        ai_model_config: {
          model_name: modelConfig.model_name,
          temperature: modelConfig.temperature || 0.7,
          max_tokens: modelConfig.max_tokens || 1000,
          api_key: modelConfig.api_key,
          base_url: modelConfig.base_url
        }
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    return response.body;
  }

  async streamAgentChat(sessionId: string, content: string, agentId: string, userId?: string): Promise<ReadableStream> {
    const url = `${this.baseUrl}/agents/chat/stream`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        session_id: sessionId,
        content: content,
        agent_id: agentId,
        user_id: userId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    return response.body;
  }

  // 停止聊天流
  async stopChat(sessionId: string): Promise<any> {
    return this.request<any>('/chat/stop', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId
      }),
    });
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