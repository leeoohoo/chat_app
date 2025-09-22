import { DatabaseService } from '../database';
import type { McpConfig } from '../database/schema';

// import McpToolExecute from './mcpToolExecute';
import AiServer from './aiServer';
import { MessageManager } from './messageManager';

// 扩展DatabaseService以包含MCP相关方法
class ExtendedDatabaseService extends DatabaseService {
  constructor(userId: string, projectId: string) {
    super(userId, projectId);
  }

  async getAllMcpConfigs(): Promise<McpConfig[]> {
    // 实现获取所有MCP配置的逻辑
    return [];
  }

  async createMcpConfig(config: Omit<McpConfig, 'id' | 'createdAt' | 'updatedAt'>): Promise<McpConfig> {
    // 实现创建MCP配置的逻辑
    const newConfig: McpConfig = {
      ...config,
      id: Math.random().toString(36).substr(2, 9),
      createdAt: new Date(),
      updatedAt: new Date()
    };
    return newConfig;
  }



  async getUserConfig<T>(_key: string): Promise<T | null> {
    // 实现获取用户配置的逻辑
    return null;
  }
}

/**
 * 聊天配置接口
 */
export interface ChatConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  apiKey: string;
  baseUrl: string;
}

/**
 * 聊天服务回调类型
 */
export interface ChatServiceCallbacks {
  onChunk?: (data: { type: string; content: string; accumulated?: string }) => void;
  onToolCall?: (toolCalls: any[]) => void;
  onToolResult?: (results: any[]) => void;
  onToolStreamChunk?: (data: { toolCallId: string; chunk: string }) => void;
  onComplete?: (message: any) => void;
  onError?: (error: Error) => void;
}

/**
 * 聊天服务管理器
 */
export class ChatService {
  private currentAiClient: any = null;
  private currentSessionId: string | null = null; // 跟踪当前会话ID
  private dbService: ExtendedDatabaseService;
  private messageManager: MessageManager;
  private userId: string;
  private baseUrl: string;

  constructor(userId: string, projectId: string, messageManager: MessageManager, baseUrl?: string) {
    this.userId = userId;
    this.dbService = new ExtendedDatabaseService(userId, projectId);
    this.messageManager = messageManager;
    this.baseUrl = baseUrl || 'http://localhost:3001/api'; // 默认值作为后备
  }



  /**
   * 发送消息并处理AI响应
   */
  async sendMessage(
    sessionId: string,
    content: string,
    _attachments: any[] = [],
    callbacks: ChatServiceCallbacks = {},
    modelConfig?: {
      model_name: string;
      temperature: number;
      max_tokens: number;
      api_key: string;
      base_url: string;
    }
  ): Promise<void> {
    try {
      // 设置当前会话ID
      this.currentSessionId = sessionId;
      
      // 获取会话信息
      const session = await this.dbService.getSession(sessionId);
      if (!session) {
        throw new Error('Session not found');
      }


      let finalModelConfig;
      if (modelConfig) {
        finalModelConfig = modelConfig;
      } else {
        const chatConfig = await this.getChatConfig();
        finalModelConfig = {
          model_name: chatConfig.model,
          temperature: chatConfig.temperature,
          max_tokens: 16000,
          api_key: chatConfig.apiKey,
          base_url: chatConfig.baseUrl
        };
      }


      // 使用AiServer进行AI调用
      const aiServer = new AiServer(sessionId, this.userId, this.messageManager, finalModelConfig as any, this.baseUrl, sessionId);
      
      // 添加初始化重试机制
      let initRetries = 3;
      while (initRetries > 0) {
        try {
          await aiServer.init();
          // 初始化完成后设置外部获取的工具
          break;
        } catch (error) {
          initRetries--;
          if (initRetries === 0) {
            throw new Error(`AI服务初始化失败: ${error instanceof Error ? error.message : '未知错误'}`);
          }
          // 等待1秒后重试
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      
      // 设置回调函数处理AI响应
      aiServer.callback = (type: string, data: any) => {
        try {
          switch (type) {
            case 'chunk':
              // 处理chunk数据，确保提取正确的内容
              const chunkContent = typeof data === 'string' ? data : 
                                 (data.content || data.accumulated || '');
              callbacks.onChunk?.({
                type: 'text',
                content: chunkContent,
                accumulated: chunkContent
              });
              break;
            case 'summary_chunk':
              const summaryChunkContent = typeof data === 'string' ? data : 
                                 (data.content || data.accumulated || '');
              callbacks.onChunk?.({
                type: 'text',
                content: summaryChunkContent,
                accumulated: summaryChunkContent
              });
              break
            case 'tool_call':
              callbacks.onToolCall?.(data);
              break;
            case 'tool_result':
              callbacks.onToolResult?.(data);
              break;
            case 'tool_stream_chunk':
              callbacks.onToolStreamChunk?.(data);
              break;
            case 'complete':
              debugger

              break;
            case 'conversation_complete':
              
              // 不在这里保存助手消息，因为aiRequestHandler.js已经保存了
              // 直接调用完成回调
              callbacks.onComplete?.(data);
              break;
            case 'error':
              const errorMessage = data instanceof Error ? data.message : (typeof data === 'string' ? data : 'AI响应出错');
              callbacks.onError?.(new Error(errorMessage));
              break;
            default:
              console.warn('Unknown AI response type:', type);
          }
        } catch (callbackError) {
          console.error('Callback error:', callbackError);
          callbacks.onError?.(new Error(`处理AI响应时出错: ${callbackError instanceof Error ? callbackError.message : '未知错误'}`));
        }
      };
       this.currentAiClient = aiServer;
      // 发送消息给AI
      await aiServer.sendMessage(content);
      
      // 设置当前AI客户端引用
     

    } catch (error: any) {
      // 检查是否是用户中断错误
      if (error.message === 'Stream aborted by user' || error.name === 'AbortError') {
        console.log('Message sending aborted by user');
        return;
      }
      
      // 检查是否是网络连接错误
      if (error.message?.includes('ERR_INCOMPLETE_CHUNKED_ENCODING') || 
          error.message?.includes('net::ERR_') ||
          error.message?.includes('Failed to fetch')) {
        console.log('Network connection error during streaming:', error.message);
        callbacks.onError?.(new Error('网络连接中断，请检查网络状态后重试'));
        return;
      }
      
      console.error('Failed to send message:', error);
      callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
      throw error;
    }
  }

  /**
   * 中止当前对话
   */
  async abortCurrentConversation(): Promise<void> {
    console.log('🛑 ChatService: 中止当前对话');
    
    if (this.currentSessionId) {
      try {
        console.log(`🛑 ChatService: 调用服务端停止接口，会话ID: ${this.currentSessionId}`);
        
        // 调用服务端停止接口
        const response = await fetch(`${this.baseUrl}/chat/stop`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sessionId: this.currentSessionId
          })
        });
        
        const result = await response.json();
        
        if (result.success) {
          console.log(`✅ ChatService: 服务端停止成功 - ${result.message}`);
        } else {
          console.warn(`⚠️ ChatService: 服务端停止失败 - ${result.message || '未知错误'}`);
        }
        debugger
        // 清理本地状态
            // 如果服务端停止失败，尝试客户端停止作为备用方案
        if (this.currentAiClient) {
          console.log('🔄 ChatService: 尝试客户端停止作为备用方案');
          this.currentAiClient.abort();
        }
        this.currentAiClient = null;
        this.currentSessionId = null;
        
      } catch (error) {
        console.error('❌ ChatService: 调用服务端停止接口失败:', error);
        
        // 如果服务端停止失败，尝试客户端停止作为备用方案
        if (this.currentAiClient) {
          console.log('🔄 ChatService: 尝试客户端停止作为备用方案');
          this.currentAiClient.abort();
        }
        
        // 清理本地状态
        this.currentAiClient = null;
        this.currentSessionId = null;
      }
    } else {
      console.log('⚠️ ChatService: 没有活动的会话可以中止');
      
      // 如果没有会话ID但有AI客户端，仍然尝试停止
      if (this.currentAiClient) {
        console.log('🔄 ChatService: 尝试停止当前AI客户端');
        this.currentAiClient.abort();
        this.currentAiClient = null;
      }
    }
  }







  /**
   * 获取聊天配置
   */
  async getChatConfig(): Promise<ChatConfig> {
    const config = await this.dbService.getUserConfig<ChatConfig>('chatConfig');
    return config || {
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
      maxTokens: 4000,
      apiKey: '',
      baseUrl: 'https://api.openai.com/v1'
    };
  }



}

// 导出核心服务类
export { default as AiServer } from './aiServer';
export { MessageManager } from './messageManager';