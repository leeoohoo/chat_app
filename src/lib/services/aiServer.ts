

import { conversationsApi, apiClient } from '../api/client';
// import http from '../utils/http';
import AiClient from "./aiClient";
import McpToolsExecute from "./mcpToolExecute";
import { MessageManager } from './messageManager';
import type { Message, AiModelConfig } from '../../types';

type CallbackType = 'chunk' | 'tool_call' | 'tool_result' | 'tool_stream_chunk' | 'conversation_complete' | 'error' | 'complete';

interface Conversation {
    id: string;
    global_prompt?: string;
}

// interface Assistant {
//     id: string;
//     system_prompt?: string;
//     model_config: any;
// }

interface McpServer {
    id: string;
    name: string;
    url: string;
    config: any;
}

// 请求线程接口
interface RequestThread {
    id: string;
    aiClient: AiClient;
    abortController: AbortController;
    isRunning: boolean;
    startTime: number;
}

class AiServer {
    private conversationId: string;
    private userId: string;
    private conversation: Conversation | null;
    private mcpServers: McpServer[];
    private messages: Message[];
    private tools: any[];
    private mcpToolsExecute: McpToolsExecute | null;
    private modelConfig: AiModelConfig | null;
    private currentThread: RequestThread | null;  // 当前活动线程
    private isAborted: boolean;
    private messageManager: MessageManager;
    private baseUrl: string;
    private sessionId: string; // 添加sessionId属性

    constructor(conversation_id: string, userId: string, messageManager: MessageManager, customModelConfig: AiModelConfig | null = null, baseUrl?: string, sessionId?: string){
        this.conversationId = conversation_id
        this.userId = userId;
        this.conversation = null;
        this.mcpServers = []
        this.messages = []
        this.tools = []
        this.mcpToolsExecute= null
        this.modelConfig = customModelConfig;
        this.messageManager = messageManager;
        this.baseUrl = baseUrl || 'http://localhost:3001/api'; // 默认值作为后备
        this.sessionId = sessionId || conversation_id; // 使用sessionId或conversationId作为默认值
        // 添加中止控制
        this.currentThread = null;
        this.isAborted = false;
    }

    async init(): Promise<void> {
        try {
            // 1. 根据conversationId 获取会话详细信息（包括全局提示词）
            const conversationResponse = await conversationsApi.getDetails(this.conversationId);
            this.conversation = conversationResponse.data.conversation;
            

            console.log('AiServer - Conversation:', this.conversation);
            console.log('AiServer - API Key:', this.modelConfig?.api_key ? 'Present' : 'Missing');

            // 4. 获取用户的MCP配置
            const mcpResponse = await apiClient.getMcpConfigs(this.userId);
            console.log("mcpResponse", mcpResponse)

            // 转换数据格式以匹配McpServer接口
            const rawServers = Array.isArray(mcpResponse) ? mcpResponse : [];
            // 只使用启用的MCP服务器
            const enabledServers = rawServers.filter((config: any) => config.enabled);
            this.mcpServers = enabledServers.map((server: any, index: number) => ({
                id: server.id || `mcp-server-${index}`,
                name: server.name,
                url: server.command, // getMcpConfigs 使用 command 字段存储URL
                config: server.config || {}
            }));
            // 5. 根据mcpServices 获取tools 列表
            this.mcpToolsExecute = new McpToolsExecute(this.mcpServers!);
            await this.mcpToolsExecute.init();
            this.tools = this.mcpToolsExecute.getTools();
            // messages 在发送消息的时候 动态获取 所以不在init 中
        } catch (error) {
            console.error('AiServer init failed:', error);
            throw error;
        }
    }



    /**
     * 回调函数，用于处理AI响应过程中的各种事件
     * @param {string} type - 事件类型 ('chunk', 'tool_call', 'error', 'complete')
     * @param {any} data - 事件数据
     */
    callback(type: CallbackType, data?: any): void {
        switch (type) {
            case 'chunk':
                // 处理流式响应的文本块
                console.log('Received chunk:', data);
                break;
            case 'tool_call':
                // 处理工具调用
                console.log('Tool call:', data);
                break;
            case 'error':
                // 处理错误
                console.error('AI Client error:', data);
                break;
            case 'complete':
                // 处理完成事件
                console.log('AI response complete:', data);
                break;
            default:
                console.log('Unknown callback type:', type, data);
        }
    }

    async sendMessage(userMessage: string): Promise<void> {
        try {
            console.log('AiServer sendMessage called with:', userMessage);
            console.log('Message type:', typeof userMessage);
            console.log('Message length:', userMessage?.length);

            // 如果没有初始化，跳过后端API调用，直接使用前端消息
            if (!this.conversation) {
                return this.sendMessageDirect(userMessage);
            }

            // 用户消息已经在store中保存了，这里不需要重复保存
            console.log('Processing user message:', userMessage);

            //2. 获取历史消息
            const messagesResponse = await conversationsApi.getMessages(this.conversationId);
            const rawMessages = messagesResponse.data.messages || [];

            // 确保消息按时间顺序排列（最早的在前面，最新的在后面）
            const sortedMessages = rawMessages.sort((a: any, b: any) => {
                const timeA = new Date(a.created_at || a.timestamp || 0);
                const timeB = new Date(b.created_at || b.timestamp || 0);
                
                // 处理无效日期
                const validTimeA = isNaN(timeA.getTime()) ? 0 : timeA.getTime();
                const validTimeB = isNaN(timeB.getTime()) ? 0 : timeB.getTime();
                
                return validTimeA - validTimeB;
            });

            // 构建完整的消息历史，包含系统提示词
            this.messages = [];
            
            // 获取系统提示词 - 从激活的 system_context 获取
            let systemPrompt = '';
            try {
                const response = await fetch(`/api/system-context/active?userId=${this.userId}`);
                if (response.ok) {
                    const data = await response.json();
                    systemPrompt = data.content || '';
                }
            } catch (error) {
                console.log('Failed to load system context:', error);
            }

            // 如果会话有全局提示词，拼接到系统提示词中
            if (this.conversation && this.conversation.global_prompt) {
                if (systemPrompt) {
                    systemPrompt = this.conversation.global_prompt + '\n\n' + systemPrompt;
                } else {
                    systemPrompt = this.conversation.global_prompt;
                }
                console.log('Added global prompt to system prompt:', this.conversation.global_prompt.substring(0, 100) + '...');
            }
            
            // 如果有系统提示词，添加到消息历史开头

            if (systemPrompt) {
                this.messages.push({
                role: 'system',
                content: systemPrompt
            } as any);
                console.log('Final system prompt added to messages:', systemPrompt.substring(0, 100) + '...');
            }
            
            // 添加历史消息（限制为最近2条：1条用户消息 + 1条助手回复）
            const recentMessages = sortedMessages.slice(-2); // 取最后2条消息
            this.messages.push(...recentMessages);

            console.log('Messages prepared for AI:', this.messages.map(m => ({
                role: m.role,
                content: (m.content || (m as any).message || '').substring(0, 50) + '...',
                created_at: (m as any).created_at
            })));
            // 创建请求线程
            const threadId = `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            const threadAbortController = new AbortController();
            const aiClient = new AiClient(this.messages, this.conversationId, this.tools, this.modelConfig!, (type: any, data?: any) => this.callback(type, data), this.mcpToolsExecute, this.messageManager, this.baseUrl, threadAbortController, this.sessionId);
            
            // 创建线程对象
            const requestThread: RequestThread = {
                id: threadId,
                aiClient: aiClient,
                abortController: threadAbortController,
                isRunning: true,
                startTime: Date.now()
            };
            
            this.currentThread = requestThread;
            console.log(`AiServer: Created request thread ${threadId}`);

            try {
                // 检查线程是否被中止
                if (this.isAborted || !requestThread.isRunning) {
                    console.log(`AiServer: Thread ${threadId} was aborted before start`);
                    return;
                }
                
                await aiClient.start();
                console.log(`AiServer: Thread ${threadId} completed successfully`);
            } catch (error: any) {
                if (this.isAborted || !requestThread.isRunning) {
                    console.log(`AiServer: Thread ${threadId} was aborted during execution`);
                    return;
                }
                // 检查是否是用户中断错误
                if (error.message === 'Stream aborted by user' || error.name === 'AbortError') {
                    console.log(`AiServer: Thread ${threadId} aborted by user`);
                    return;
                }
                console.error(`AiServer: Thread ${threadId} failed:`, error);
                throw error;
            } finally {
                // 清理线程
                if (this.currentThread?.id === threadId) {
                    this.currentThread.isRunning = false;
                    this.currentThread = null;
                    console.log(`AiServer: Thread ${threadId} cleaned up`);
                }
            }
        } catch (error: any) {
            // 检查是否是用户中断错误
            if (error.message === 'Stream aborted by user' || error.name === 'AbortError' || this.isAborted) {
                console.log('sendMessage aborted by user');
                return;
            }
            console.error('sendMessage failed:', error);
            console.error('Error details:', error.response?.data);
            this.callback('error', error);
            throw error;
        }
    }





    /**
     * 获取会话消息
     * @param {Object} params - 分页参数 {page, limit}
     * @returns {Promise}
     */

    // 直接发送消息，不依赖后端API
    async sendMessageDirect(userMessage: string): Promise<void> {
        try {
            console.log('AiServer sendMessageDirect called with:', userMessage);
            
            // 构建简单的消息历史
            this.messages = [
                {
                    role: 'user',
                    content: userMessage
                } as any
            ];
            
            console.log('Messages prepared for AI:', this.messages);
            
            // 创建简单线程（不使用工具）
            const threadId = `direct_thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            const threadAbortController = new AbortController();
            const aiClient = new AiClient(this.messages, this.conversationId, [], this.modelConfig!, (type: any, data?: any) => this.callback(type, data), null, this.messageManager, this.baseUrl, threadAbortController, this.sessionId);
            
            const requestThread: RequestThread = {
                id: threadId,
                aiClient: aiClient,
                abortController: threadAbortController,
                isRunning: true,
                startTime: Date.now()
            };
            
            this.currentThread = requestThread;
            console.log(`AiServer: Created direct thread ${threadId}`);
            
            try {
                if (this.isAborted || !requestThread.isRunning) {
                    console.log(`AiServer: Direct thread ${threadId} was aborted before start`);
                    return;
                }
                
                await aiClient.start();
                console.log(`AiServer: Direct thread ${threadId} completed successfully`);
            } catch (error) {
                if (this.isAborted || !requestThread.isRunning) {
                    console.log(`AiServer: Direct thread ${threadId} was aborted during execution`);
                    return;
                }
                console.error(`AiServer: Direct thread ${threadId} failed:`, error);
                throw error;
            } finally {
                if (this.currentThread?.id === threadId) {
                    this.currentThread.isRunning = false;
                    this.currentThread = null;
                    console.log(`AiServer: Direct thread ${threadId} cleaned up`);
                }
            }
        } catch (error: any) {
            console.error('sendMessageDirect failed:', error);
            this.callback('error', error);
            throw error;
        }
    }

    async getMessages(params: any = {}): Promise<any> {
        try {
            const response = await conversationsApi.getMessages(this.conversationId, params);
            this.messages = response.data.messages || [];
            return response.data;
        } catch (error: any) {
            console.error('getMessages failed:', error);
            throw error;
        }
    }

    /**
     * 添加消息到会话
     * @param {string} message - 消息内容
     * @param {string} role - 消息角色 ('user' | 'assistant')
     * @returns {Promise}
     */
    async addMessage(message: string, role: string = 'user'): Promise<any> {
        try {
            // 使用统一的消息管理器保存消息
            const savedMessage = await this.messageManager.saveMessage({
                content: message,
                role,
                sessionId: this.conversationId,
                createdAt: new Date()
            } as Message);
            return { message: savedMessage };
        } catch (error: any) {
            console.error('addMessage failed:', error);
            throw error;
        }
    }





    /**
     * 中止当前请求线程
     */
    abort(): void {
        console.log('AiServer: Abort called');
        this.isAborted = true;
        debugger
        if (this.currentThread) {
            console.log(`AiServer: Aborting thread ${this.currentThread.id}`);
            
            // 标记线程为非运行状态
            this.currentThread.isRunning = false;
            
            // 中止AbortController - 这会触发aiClient中的监听器
            if (!this.currentThread.abortController.signal.aborted) {
                this.currentThread.abortController.abort();
                console.log(`AiServer: Thread ${this.currentThread.id} AbortController aborted`);
            }
            
            // 直接中止AI客户端（双重保险）
            if (this.currentThread.aiClient) {
                this.currentThread.aiClient.abort();
                console.log(`AiServer: Thread ${this.currentThread.id} AI client aborted`);
            }
            
            // 清理线程引用
            this.currentThread = null;
            console.log('AiServer: Thread reference cleared');
        } else {
            console.log('AiServer: No active thread to abort');
        }
    }

    /**
     * 检查是否已被中止
     * @returns {boolean}
     */
    isRequestAborted(): boolean {
        return this.isAborted;
    }

    /**
     * 重置中止状态
     */
    resetAbortState(): void {
        this.isAborted = false;
        if (this.currentThread) {
            this.currentThread.isRunning = false;
            this.currentThread = null;
        }
    }
}

export default AiServer;