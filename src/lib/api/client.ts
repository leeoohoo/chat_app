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
      
      return await response.json();
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
    return this.request('/mcp-configs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMcpConfig(id: string, data: any) {
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
  async getSystemContext(): Promise<{ content: string }> {
    return this.request<{ content: string }>('/system-context');
  }

  async updateSystemContext(content: string): Promise<void> {
    return this.request<void>('/system-context', {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }
}

// 导出单例实例
export const apiClient = new ApiClient();
export default ApiClient;