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
}

// 导出单例实例
export const apiClient = new ApiClient();
export default ApiClient;