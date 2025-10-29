import {create} from 'zustand';
import {subscribeWithSelector} from 'zustand/middleware';
import {immer} from 'zustand/middleware/immer';
import {persist} from 'zustand/middleware';
import type {Message, Session, ChatConfig, Theme, McpConfig, AiModelConfig, SystemContext} from '../../types';
import {DatabaseService} from '../database';
import {apiClient} from '../api/client';
import {ChatService, MessageManager} from '../services';
import type ApiClient from '../api/client';

// 聊天状态接口
interface ChatState {
    // 会话相关
    sessions: Session[];
    currentSessionId: string | null;
    currentSession: Session | null;

    // 消息相关
    messages: Message[];
    isLoading: boolean;
    isStreaming: boolean;
    streamingMessageId: string | null;

    // UI状态
    sidebarOpen: boolean;
    theme: Theme;

    // 配置相关
    chatConfig: ChatConfig;
    mcpConfigs: McpConfig[];
    aiModelConfigs: AiModelConfig[];
    selectedModelId: string | null;
    systemContexts: SystemContext[];
    activeSystemContext: SystemContext | null;

    // 错误处理
    error: string | null;
}

// 聊天操作接口
interface ChatActions {
    // 会话操作
    loadSessions: () => Promise<void>;
    createSession: (title?: string) => Promise<string>;
    selectSession: (sessionId: string) => Promise<void>;
    updateSession: (sessionId: string, updates: Partial<Session>) => Promise<void>;
    deleteSession: (sessionId: string) => Promise<void>;

    // 消息操作
    loadMessages: (sessionId: string) => Promise<void>;
    sendMessage: (content: string, attachments?: any[]) => Promise<void>;
    updateMessage: (messageId: string, updates: Partial<Message>) => Promise<void>;
    deleteMessage: (messageId: string) => Promise<void>;

    // 流式消息处理
    startStreaming: (messageId: string) => void;
    updateStreamingMessage: (content: string) => void;
    stopStreaming: () => void;
    abortCurrentConversation: () => void;

    // UI操作
    toggleSidebar: () => void;
    setTheme: (theme: Theme) => void;

    // 配置操作
    updateChatConfig: (config: Partial<ChatConfig>) => Promise<void>;
    loadMcpConfigs: () => Promise<void>;
    updateMcpConfig: (config: McpConfig) => Promise<void>;
    deleteMcpConfig: (id: string) => Promise<void>;
    loadAiModelConfigs: () => Promise<void>;
    updateAiModelConfig: (config: AiModelConfig) => Promise<void>;
    deleteAiModelConfig: (id: string) => Promise<void>;
    setSelectedModel: (modelId: string | null) => void;
    loadSystemContexts: () => Promise<void>;
    createSystemContext: (name: string, content: string) => Promise<void>;
    updateSystemContext: (id: string, name: string, content: string) => Promise<void>;
    deleteSystemContext: (id: string) => Promise<void>;
    activateSystemContext: (id: string) => Promise<void>;

    // 错误处理
    setError: (error: string | null) => void;
    clearError: () => void;
}

// 自定义配置接口
interface ChatStoreConfig {
    userId?: string;
    projectId?: string;
    configUrl?: string;
}

/**
 * 创建聊天store的工厂函数（使用后端API版本）
 * @param customApiClient 自定义的API客户端实例，如果不提供则使用默认的apiClient
 * @param config 自定义配置，包含userId和projectId
 * @returns 聊天store hook
 */
export function createChatStoreWithBackend(customApiClient?: ApiClient, config?: ChatStoreConfig) {
    const client = customApiClient || apiClient;
    const customUserId = config?.userId;
    const customProjectId = config?.projectId;
    const customConfigUrl = config?.configUrl;
    
    // 使用传入的参数或默认值
    const userId = customUserId || 'default-user';
    const projectId = customProjectId || 'default-project';
    const configUrl = customConfigUrl || '/api';
    
    // 获取userId的统一函数
    const getUserIdParam = () => userId;
    
    // 获取会话相关参数的统一函数
    const getSessionParams = () => {
        return { userId, projectId };
    };
    
    // 创建DatabaseService实例
    const databaseService = new DatabaseService(userId, projectId);
    
    // 创建MessageManager和ChatService实例
    const messageManager = new MessageManager(databaseService);
    const chatService = new ChatService(userId, projectId, messageManager, configUrl);
    console.log("chatService:", chatService)
    
    return create<ChatState & ChatActions>()
    (subscribeWithSelector(
        immer(
            persist(
                (set, get) => ({
                    // 初始状态
                    sessions: [],
                    currentSessionId: null,
                    currentSession: null,
                    messages: [],
                    isLoading: false,
                    isStreaming: false,
                    streamingMessageId: null,
                    sidebarOpen: true,
                    theme: 'light',
                    chatConfig: {
                        model: 'gpt-4',
                        temperature: 0.7,
                        maxTokens: 2048,
                        systemPrompt: '',
                        enableMcp: true,
                    },
                    mcpConfigs: [],
                    aiModelConfigs: [],
                    selectedModelId: null,
                    systemContexts: [],
                    activeSystemContext: null,
                    error: null,

                    // 会话操作
                    loadSessions: async () => {
                        try {
                            console.log('🔍 loadSessions 被调用');
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });
                            console.log('🔍 loadSessions isLoading 设置为 true');

                            // 使用统一的参数获取逻辑
                            const { userId, projectId } = getSessionParams();
                            
                            console.log('🔍 loadSessions 调用 client.getSessions', { userId, projectId, customUserId, customProjectId });
                            const sessions = await client.getSessions(userId, projectId);
                            console.log('🔍 loadSessions 返回结果:', sessions);

                            set((state) => {
                                state.sessions = sessions;
                                state.isLoading = false;
                            });

                            // 会话持久化逻辑：自动选择上次使用的会话或最新的会话
                            const currentState = get();
                            if (sessions.length > 0 && !currentState.currentSessionId) {
                                // 尝试从 localStorage 获取上次使用的会话ID
                                const lastSessionId = localStorage.getItem(`lastSessionId_${userId}_${projectId}`);
                                let sessionToSelect = null;

                                if (lastSessionId) {
                                    // 检查上次使用的会话是否仍然存在
                                    sessionToSelect = sessions.find(s => s.id === lastSessionId);
                                }

                                // 如果上次的会话不存在，选择最新的会话（按创建时间排序）
                                if (!sessionToSelect) {
                                    sessionToSelect = [...sessions].sort((a, b) => 
                                        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
                                    )[0];
                                }

                                if (sessionToSelect) {
                                    console.log('🔍 自动选择会话:', sessionToSelect.id);
                                    // 异步选择会话，不阻塞 loadSessions 的完成
                                    setTimeout(() => {
                                        get().selectSession(sessionToSelect.id);
                                    }, 0);
                                }
                            }

                            console.log('🔍 loadSessions 完成');
                        } catch (error) {
                            console.error('🔍 loadSessions 错误:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to load sessions';
                                state.isLoading = false;
                            });
                        }
                    },

                    createSession: async (title = 'New Chat') => {
                        try {
                            // 使用统一的参数获取逻辑
                            const { userId, projectId } = getSessionParams();
                    
                            console.log('🔍 createSession 使用参数:', { userId, projectId, title });
                            console.log('🔍 createSession 自定义参数:', { customUserId, customProjectId });
                            console.log('🔍 createSession 最终使用的参数:', { 
                                userId: userId, 
                                projectId: projectId,
                                isCustomUserId: !!customUserId,
                                isCustomProjectId: !!customProjectId
                            });
                            
                            // 直接调用API客户端创建会话
                            const sessionData = {
                                id: crypto.randomUUID(),
                                title,
                                user_id: userId,
                                project_id: projectId
                            };
                            
                            const session = await client.createSession(sessionData);
                            console.log('✅ createSession API调用成功:', session);
                            
                            // 转换为前端格式
                            const formattedSession = {
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

                            set((state) => {
                                state.sessions.unshift(formattedSession);
                                state.currentSessionId = formattedSession.id;
                                state.currentSession = formattedSession;
                                state.messages = [];
                                state.error = null;
                            });

                            // 保存新创建的会话ID到 localStorage 以实现持久化
                            localStorage.setItem(`lastSessionId_${userId}_${projectId}`, formattedSession.id);
                            console.log('🔍 保存新创建的会话ID到 localStorage:', formattedSession.id);

                            return formattedSession.id;
                        } catch (error) {
                            console.error('❌ createSession 失败:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to create session';
                            });
                            throw error;
                        }
                    },

                    selectSession: async (sessionId: string) => {
                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            const session = await databaseService.getSession(sessionId);
                            const messages = await databaseService.getSessionMessages(sessionId);
                            
                            set((state) => {
                            state.currentSessionId = sessionId;
                            (state as any).currentSession = session; // Type assertion to handle immer WritableDraft issue
                            state.messages = messages;
                            state.isLoading = false;
                            if (!session) {
                                state.error = 'Session not found';
                            }
                        });

                            // 保存当前会话ID到 localStorage 以实现持久化
                            if (session) {
                                const { userId, projectId } = getSessionParams();
                                localStorage.setItem(`lastSessionId_${userId}_${projectId}`, sessionId);
                                console.log('🔍 保存会话ID到 localStorage:', sessionId);
                            }
                        } catch (error) {
                            console.error('Failed to select session:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to select session';
                                state.isLoading = false;
                            });
                        }
                    },

                    updateSession: async (sessionId: string, updates: Partial<Session>) => {
                        try {
                            const updatedSession = await databaseService.updateSession(sessionId, updates);
                            
                            set((state) => {
                                const index = state.sessions.findIndex(s => s.id === sessionId);
                                if (index !== -1 && updatedSession) {
                                    state.sessions[index] = updatedSession;
                                }
                                if (state.currentSessionId === sessionId) {
                                    state.currentSession = updatedSession;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to update session:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to update session';
                            });
                        }
                    },

                    deleteSession: async (sessionId: string) => {
                        try {
                            await databaseService.deleteSession(sessionId);
                            
                            set((state) => {
                                state.sessions = state.sessions.filter(s => s.id !== sessionId);
                                if (state.currentSessionId === sessionId) {
                                    state.currentSessionId = null;
                                    state.currentSession = null;
                                    state.messages = [];
                                }
                            });
                        } catch (error) {
                            console.error('Failed to delete session:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to delete session';
                            });
                        }
                    },

                    // 消息操作
                    loadMessages: async (sessionId: string) => {
                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            const messages = await databaseService.getSessionMessages(sessionId);
                            
                            set((state) => {
                                state.messages = messages;
                                state.isLoading = false;
                            });
                        } catch (error) {
                            console.error('Failed to load messages:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to load messages';
                                state.isLoading = false;
                            });
                        }
                    },

                    sendMessage: async (content: string, attachments = []) => {
                        const { currentSessionId, selectedModelId, aiModelConfigs, chatConfig, isLoading, isStreaming, activeSystemContext } = get();

                        if (!currentSessionId) {
                            throw new Error('No active session');
                        }

                        // 检查是否已经在发送消息，防止重复发送
                        if (isLoading || isStreaming) {
                            console.log('Message sending already in progress, ignoring duplicate request');
                            return;
                        }

                        if (!selectedModelId) {
                            throw new Error('请先选择一个AI模型');
                        }

                        const selectedModel = aiModelConfigs.find(model => model.id === selectedModelId);
                        if (!selectedModel || !selectedModel.enabled) {
                            throw new Error('选择的模型不可用');
                        }

                        try {
                            // 创建用户消息（仅前端展示，不立即保存数据库）
                            const userMessageTime = new Date();
                            const userMessage: Message = {
                                id: `temp_user_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
                                sessionId: currentSessionId,
                                role: 'user',
                                content,
                                status: 'completed',
                                createdAt: userMessageTime,
                                metadata: {
                                    ...(attachments.length > 0 ? { attachments } : {}),
                                    model: selectedModel.model_name,
                                    modelConfig: {
                                        id: selectedModel.id,
                                        name: selectedModel.name,
                                        base_url: selectedModel.base_url,
                                        model_name: selectedModel.model_name,
                                    }
                                },
                            };

                            set((state) => {
                                state.messages.push(userMessage);
                                state.isLoading = true;
                                state.isStreaming = true;
                            });

                            // 创建临时的助手消息用于UI显示，但不保存到数据库
                            const assistantMessageTime = new Date(userMessageTime.getTime() + 1);
                            const tempAssistantMessage = {
                                id: `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                                sessionId: currentSessionId,
                                role: 'assistant' as const,
                                content: '',
                                status: 'streaming' as const,
                                createdAt: assistantMessageTime,
                                metadata: {
                                    model: selectedModel.model_name,
                                    modelConfig: {
                                        id: selectedModel.id,
                                        name: selectedModel.name,
                                        base_url: selectedModel.base_url,
                                        model_name: selectedModel.model_name,
                                    },
                                    toolCalls: [], // 初始化工具调用数组
                                    contentSegments: [{ content: '', type: 'text' as const }], // 初始化内容分段
                                    currentSegmentIndex: 0 // 当前正在写入的分段索引
                                },
                            };

                            set((state) => {
                                state.messages.push(tempAssistantMessage);
                                state.streamingMessageId = tempAssistantMessage.id;
                            });

                            // 准备聊天请求数据
                            const chatRequest = {
                                session_id: currentSessionId,
                                message: content,
                                model_config: {
                                    model: selectedModel.model_name,
                                    base_url: selectedModel.base_url,
                                    api_key: selectedModel.api_key || '',
                                    temperature: chatConfig.temperature,
                                    max_tokens: chatConfig.maxTokens,
                                },
                                system_context: activeSystemContext?.content || chatConfig.systemPrompt || '',
                                attachments: attachments || []
                            };

                            console.log('🚀 开始调用后端流式聊天API:', chatRequest);

                            // 使用后端API进行流式聊天
                            const response = await client.streamChat(
                                currentSessionId, 
                                content, 
                                selectedModel
                            );
                            
                            if (!response) {
                                throw new Error('No response received');
                            }

                            const reader = response.getReader();
                            const decoder = new TextDecoder();

                            try {
                                while (true) {
                                    const { done, value } = await reader.read();
                                    
                                    if (done) {
                                        console.log('✅ 流式响应完成');
                                        break;
                                    }

                                    const chunk = decoder.decode(value, { stream: true });
                                    const lines = chunk.split('\n');

                                    for (const line of lines) {
                                        if (line.trim() === '') continue;
                                        
                                        if (line.startsWith('data: ')) {
                                            const data = line.slice(6);
                                            
                                            if (data === '[DONE]') {
                                                console.log('✅ 收到完成信号');
                                                break;
                                            }

                                            try {
                                                const parsed = JSON.parse(data);

                                                // 处理后端发送的数据格式
                                                if (parsed.type === 'chunk') {
                                                    // 后端发送格式: {type: 'chunk', content: '...', accumulated: '...'}
                                                    if (parsed.content) {
                                                        // 更新UI中的流式消息，使用分段管理
                                                        set((state) => {
                                                            const message = state.messages.find(m => m.id === tempAssistantMessage.id);
                                                            if (message && message.metadata) {
                                                                // 确保parsed.content是字符串
                                                                const content = typeof parsed.content === 'string' ? parsed.content :
                                                                    (typeof parsed === 'string' ? parsed :
                                                                        (parsed.content || ''));
                                                                
                                                                // 获取当前分段索引
                                                                const currentIndex = message.metadata.currentSegmentIndex || 0;
                                                                const segments = message.metadata.contentSegments || [];
                                                                
                                                                // 确保当前分段存在且为文本类型
                                                                if (segments[currentIndex] && segments[currentIndex].type === 'text') {
                                                                    segments[currentIndex].content += content;
                                                                } else {
                                                                    // 如果当前分段不存在或不是文本类型，创建新的文本分段
                                                                    segments.push({ content, type: 'text' as const });
                                                                    message.metadata.currentSegmentIndex = segments.length - 1;
                                                                }
                                                                
                                                                // 更新完整内容用于向后兼容
                                                                message.content = segments.filter((s: any) => s.type === 'text').map((s: any) => s.content).join('');
                                                            }
                                                        });
                                                    }
                                                } else if (parsed.type === 'content') {
                                                    // 兼容旧格式: {type: 'content', content: '...'}
                                                    // 更新UI中的流式消息，使用分段管理
                                                    set((state) => {
                                                        const message = state.messages.find(m => m.id === tempAssistantMessage.id);
                                                        if (message && message.metadata) {
                                                            // 确保parsed.content是字符串
                                                            const content = typeof parsed.content === 'string' ? parsed.content :
                                                                (typeof parsed === 'string' ? parsed :
                                                                    (parsed.content || ''));
                                                            
                                                            // 获取当前分段索引
                                                            const currentIndex = message.metadata.currentSegmentIndex || 0;
                                                            const segments = message.metadata.contentSegments || [];
                                                            
                                                            // 确保当前分段存在且为文本类型
                                                            if (segments[currentIndex] && segments[currentIndex].type === 'text') {
                                                                segments[currentIndex].content += content;
                                                            } else {
                                                                // 如果当前分段不存在或不是文本类型，创建新的文本分段
                                                                segments.push({ content, type: 'text' as const });
                                                                message.metadata.currentSegmentIndex = segments.length - 1;
                                                            }
                                                            
                                                            // 更新完整内容用于向后兼容
                                                            message.content = segments.filter((s: any) => s.type === 'text').map((s: any) => s.content).join('');
                                                        }
                                                    });
                                                } else if (parsed.type === 'tools_start') {
                                                    // 处理工具调用事件
                                                    console.log('🔧 收到工具调用:', parsed.data);
                                                    console.log('🔧 工具调用数据类型:', typeof parsed.data, '是否为数组:', Array.isArray(parsed.data));
                                                    
                                                    // 数据转换函数：将后端格式转换为前端期望的格式
                                                    const convertToolCallData = (tc: any) => {
                                                        console.log('🔧 [DEBUG] 原始工具调用数据:', tc);
                                                        console.log('🔧 [DEBUG] tc.function:', tc.function);
                                                        console.log('🔧 [DEBUG] tc.function?.name:', tc.function?.name);
                                                        console.log('🔧 [DEBUG] tc.name:', tc.name);
                                                        
                                                        const toolCall = {
                                                            id: tc.id || tc.tool_call_id || `tool_${Date.now()}_${Math.random()}`, // 确保有ID
                                                            messageId: tempAssistantMessage.id, // 添加前端需要的messageId
                                                            name: tc.function?.name || tc.name || 'unknown_tool', // 兼容不同的name字段位置
                                                            arguments: tc.function?.arguments || tc.arguments || '{}', // 兼容不同的arguments字段位置
                                                            result: tc.result || '', // 初始化result字段
                                                            error: tc.error || undefined, // 可选的error字段
                                                            createdAt: tc.createdAt || tc.created_at || new Date() // 添加前端需要的createdAt，支持多种时间格式
                                                        };
                                                        
                                                        console.log('🔧 [DEBUG] 转换后的工具调用:', toolCall);
                                                        return toolCall;
                                                    };
                                                    
                                                    // 修复：从 parsed.data.tool_calls 中提取工具调用数组
                                                    console.log('🔧 [DEBUG] tools_start 原始数据:', parsed.data);
                                                    const rawToolCalls = parsed.data.tool_calls || parsed.data;
                                                    const toolCallsArray = Array.isArray(rawToolCalls) ? rawToolCalls : [rawToolCalls];
                                                    console.log('🔧 [DEBUG] 提取的工具调用数组:', toolCallsArray);
                                                    
                                                    set((state) => {
                                                        const messageIndex = state.messages.findIndex(m => m.id === tempAssistantMessage.id);
                                                        console.log('🔧 查找消息索引:', messageIndex, '消息ID:', tempAssistantMessage.id);
                                                        if (messageIndex !== -1) {
                                                            const message = state.messages[messageIndex];
                                                            console.log('🔧 找到消息，当前metadata:', message.metadata);
                                                            if (!message.metadata) {
                                                                message.metadata = {};
                                                            }
                                                            if (!message.metadata.toolCalls) {
                                                                message.metadata.toolCalls = [];
                                                            }
                                                            
                                                            const segments = message.metadata.contentSegments || [];
                                                            
                                                            // 处理所有工具调用
                                                            console.log('🔧 处理工具调用数组，长度:', toolCallsArray.length);
                                                            toolCallsArray.forEach((tc: any) => {
                                                                const toolCall = convertToolCallData(tc);
                                                                console.log('🔧 添加转换后的工具调用:', toolCall);
                                                                message.metadata!.toolCalls!.push(toolCall);
                                                                
                                                                // 添加工具调用分段
                                                                segments.push({
                                                                    content: '',
                                                                    type: 'tool_call' as const,
                                                                    toolCallId: toolCall.id
                                                                });
                                                            });
                                                            
                                                            // 为工具调用后的内容创建新的文本分段
                                                            segments.push({ content: '', type: 'text' as const });
                                                            message.metadata!.currentSegmentIndex = segments.length - 1;
                                                            console.log('🔧 更新后的toolCalls:', message.metadata.toolCalls);
                                                        } else {
                                                            console.log('🔧 ❌ 未找到对应的消息');
                                                        }
                                                    });
                                                } else if (parsed.type === 'tools_end') {
                                                    // 处理工具结果事件
                                                    console.log('🔧 收到工具结果:', parsed.data);
                                                    console.log('🔧 工具结果数据类型:', typeof parsed.data);
                                                    
                                                    // 统一处理数组和单个对象
                                                    const resultsArray = Array.isArray(parsed.data) ? parsed.data : [parsed.data];
                                                    
                                                    set((state) => {
                                                        const messageIndex = state.messages.findIndex(m => m.id === tempAssistantMessage.id);
                                                        if (messageIndex !== -1) {
                                                            const message = state.messages[messageIndex];
                                                            if (message.metadata && message.metadata.toolCalls) {
                                                                // 更新对应工具调用的结果
                                                                resultsArray.forEach((result: any) => {
                                                                    // 统一字段名称处理：支持 tool_call_id、id、toolCallId 等不同命名
                                                                    const toolCallId = result.tool_call_id || result.id || result.toolCallId;
                                                                    
                                                                    if (!toolCallId) {
                                                                        console.warn('⚠️ 工具结果缺少工具调用ID:', result);
                                                                        return;
                                                                    }
                                                                    
                                                                    console.log('🔍 查找工具调用:', toolCallId, '在消息中:', message.metadata?.toolCalls?.map(tc => tc.id));
                                                                    const toolCall = message.metadata!.toolCalls!.find((tc: any) => tc.id === toolCallId);
                                                                    
                                                                    if (toolCall) {
                                                                        console.log('✅ 找到工具调用，更新最终结果:', toolCall.id);
                                                                        
                                                                        // 根据后端数据格式处理最终结果
                                                                        // 支持多种结果字段名称：result、content、output
                                                                        const resultContent = result.result || result.content || result.output || '';
                                                                        
                                                                        // 检查执行状态
                                                                        if (result.success === false || result.is_error === true) {
                                                                            // 工具执行失败
                                                                            toolCall.error = result.error || resultContent || '工具执行失败';
                                                                            console.log('❌ 工具执行失败:', {
                                                                                id: toolCall.id,
                                                                                name: result.name || toolCall.name,
                                                                                error: toolCall.error,
                                                                                success: result.success,
                                                                                is_error: result.is_error
                                                                            });
                                                                        } else {
                                                                            // 工具执行成功，更新最终结果
                                                                            // 如果之前有流式内容，保留；否则使用最终结果
                                                                            if (!toolCall.result || toolCall.result.trim() === '') {
                                                                                toolCall.result = resultContent;
                                                                            }
                                                                            
                                                                            // 清除可能存在的错误状态
                                                                            if (toolCall.error) {
                                                                                delete toolCall.error;
                                                                            }
                                                                            
                                                                            console.log('✅ 工具执行成功，最终结果已更新:', {
                                                                                id: toolCall.id,
                                                                                name: result.name || toolCall.name,
                                                                                resultLength: toolCall.result.length,
                                                                                success: result.success,
                                                                                is_stream: result.is_stream
                                                                            });
                                                                        }
                                                                        
                                                                    } else {
                                                                        console.log('❌ 未找到对应的工具调用:', toolCallId);
                                                                        console.log('📋 当前可用的工具调用ID:', message.metadata?.toolCalls?.map(tc => tc.id));
                                                                    }
                                                                });
                                                                
                                                                // 强制触发消息更新以确保自动滚动
                                                                // 通过更新消息的 updatedAt 时间戳来触发 React 重新渲染
                                                                message.updatedAt = new Date();
                                                            }
                                                        }
                                                    });
                                                } else if (parsed.type === 'tools_stream') {
                                                    // 处理工具流式返回内容
                                                    console.log('🔧 收到工具流式数据:', parsed.data);
                                                    const data = parsed.data;
                                                    
                                                    set((state) => {
                                                        const messageIndex = state.messages.findIndex(m => m.id === tempAssistantMessage.id);
                                                        if (messageIndex !== -1) {
                                                            const message = state.messages[messageIndex];
                                                            if (message.metadata && message.metadata.toolCalls) {
                                                                // 统一字段名称处理：支持 toolCallId、tool_call_id、id 等不同命名
                                                                const toolCallId = data.toolCallId || data.tool_call_id || data.id;
                                                                
                                                                if (!toolCallId) {
                                                                    console.warn('⚠️ 工具流式数据缺少工具调用ID:', data);
                                                                    return;
                                                                }
                                                                
                                                                console.log('🔍 查找工具调用进行流式更新:', toolCallId);
                                                                const toolCall = message.metadata.toolCalls.find((tc: any) => tc.id === toolCallId);
                                                                
                                                                if (toolCall) {
                                                                    // 根据后端实际发送的数据格式处理
                                                                    // 后端发送: {tool_call_id, name, success, is_error, content, is_stream: true}
                                                                    const chunkContent = data.content || data.chunk || data.data || '';
                                                                    
                                                                    // 检查是否有错误
                                                                    if (data.is_error || !data.success) {
                                                                        // 如果是错误，标记工具调用失败
                                                                        toolCall.error = chunkContent || '工具执行出错';
                                                                        console.log('❌ 工具流式执行出错:', {
                                                                            id: toolCall.id,
                                                                            error: toolCall.error,
                                                                            success: data.success,
                                                                            is_error: data.is_error
                                                                        });
                                                                    } else {
                                                                        // 正常情况下累积内容
                                                                        toolCall.result = (toolCall.result || '') + chunkContent;
                                                                        console.log('🔧 工具流式数据已更新:', {
                                                                            id: toolCall.id,
                                                                            name: data.name,
                                                                            chunkLength: chunkContent.length,
                                                                            totalLength: toolCall.result.length,
                                                                            success: data.success,
                                                                            is_stream: data.is_stream
                                                                        });
                                                                    }
                                                                    
                                                                    // 强制触发UI更新
                                                                    message.updatedAt = new Date();
                                                                } else {
                                                                    console.log('❌ 未找到对应的工具调用进行流式更新:', toolCallId);
                                                                    console.log('📋 当前可用的工具调用ID:', message.metadata?.toolCalls?.map(tc => tc.id));
                                                                }
                                                            }
                                                        }
                                                    });
                                                } else if (parsed.type === 'complete') {
                                    // 处理完成事件，获取后端已保存的消息
                                    console.log('✅ 收到完成事件，获取已保存的消息:', parsed.data);
                                    const savedMessage = parsed.data?.message;
                                    
                                    if (savedMessage) {
                                        console.log('🔍 检查后端保存的消息metadata:', savedMessage.metadata);
                                        console.log('🔍 检查后端保存的消息toolCalls:', savedMessage.metadata?.toolCalls);
                                        
                                        // 用后端保存的消息替换临时消息
                                        set((state) => {
                                            const messageIndex = state.messages.findIndex(m => m.id === tempAssistantMessage.id);
                                            if (messageIndex !== -1) {
                                                const currentMessage = state.messages[messageIndex];
                                                console.log('🔍 当前临时消息的toolCalls:', currentMessage.metadata?.toolCalls);
                                                console.log('🔍 当前临时消息的contentSegments:', currentMessage.metadata?.contentSegments);
                                                
                                                // 合并metadata，保留临时消息中的重要数据
                                                const finalMetadata = savedMessage.metadata || {};
                                                
                                                // 如果后端消息没有工具调用数据，但临时消息有，则保留临时消息的工具调用数据
                                                if (!finalMetadata.toolCalls && currentMessage.metadata?.toolCalls) {
                                                    console.log('⚠️ 后端消息缺少工具调用数据，保留临时消息的工具调用数据');
                                                    finalMetadata.toolCalls = currentMessage.metadata.toolCalls;
                                                }
                                                
                                                // 如果后端消息没有contentSegments数据，但临时消息有，则保留临时消息的contentSegments数据
                                                if (!finalMetadata.contentSegments && currentMessage.metadata?.contentSegments) {
                                                    console.log('⚠️ 后端消息缺少contentSegments数据，保留临时消息的contentSegments数据');
                                                    finalMetadata.contentSegments = currentMessage.metadata.contentSegments;
                                                }
                                                
                                                state.messages[messageIndex] = {
                                                    id: savedMessage.id,
                                                    sessionId: savedMessage.session_id || savedMessage.sessionId,
                                                    role: savedMessage.role,
                                                    content: savedMessage.content,
                                                    status: savedMessage.status,
                                                    createdAt: savedMessage.created_at || savedMessage.createdAt,
                                                    metadata: finalMetadata
                                                };
                                                
                                                console.log('✅ 消息替换完成，最终metadata:', finalMetadata);
                                            }
                                        });
                                    }
                                                    break;
                                                } else if (parsed.type === 'error') {
                                                    throw new Error(parsed.message || parsed.data?.message || 'Stream error');
                                                } else if (parsed.type === 'cancelled') {
                                                    console.log('⚠️ 流式会话已被取消');
                                                    break;
                                                } else if (parsed.type === 'done') {
                                                    console.log('✅ 收到完成信号');
                                                    break;
                                                }
                                            } catch (parseError) {
                                                console.warn('解析流式数据失败:', parseError, 'data:', data);
                                            }
                                        }
                                    }
                                }
                            } finally {
                                reader.releaseLock();
                                
                                // 更新状态，结束流式传输
                                set((state) => {
                                    state.isLoading = false;
                                    state.isStreaming = false;
                                    state.streamingMessageId = null;
                                });
                            }

                            console.log('✅ 消息发送完成');

                        } catch (error) {
                            console.error('❌ 发送消息失败:', error);
                            
                            // 移除临时消息并显示错误
                            set((state) => {
                                const tempMessageIndex = state.messages.findIndex(m => m.id?.startsWith('temp_'));
                                if (tempMessageIndex !== -1) {
                                    state.messages.splice(tempMessageIndex, 1);
                                }
                                state.isLoading = false;
                                state.isStreaming = false;
                                state.streamingMessageId = null;
                                state.error = error instanceof Error ? error.message : 'Failed to send message';
                            });
                            
                            throw error;
                        }
                    },

                    updateMessage: async (messageId: string, updates: Partial<Message>) => {
                        try {
                            const updatedMessage = await databaseService.updateMessage(messageId, updates);
                            
                            set((state) => {
                                const index = state.messages.findIndex(m => m.id === messageId);
                                if (index !== -1 && updatedMessage) {
                                    state.messages[index] = updatedMessage;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to update message:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to update message';
                            });
                        }
                    },

                    deleteMessage: async (messageId: string) => {
                        try {
                            await databaseService.deleteMessage(messageId);
                            
                            set((state) => {
                                state.messages = state.messages.filter(m => m.id !== messageId);
                            });
                        } catch (error) {
                            console.error('Failed to delete message:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to delete message';
                            });
                        }
                    },

                    // 流式消息处理
                    startStreaming: (messageId: string) => {
                        set((state) => {
                            state.isStreaming = true;
                            state.streamingMessageId = messageId;
                        });
                    },

                    updateStreamingMessage: (content: string) => {
                        set((state) => {
                            if (state.streamingMessageId) {
                                const messageIndex = state.messages.findIndex(m => m.id === state.streamingMessageId);
                                if (messageIndex !== -1) {
                                    state.messages[messageIndex].content = content;
                                }
                            }
                        });
                    },

                    stopStreaming: () => {
                        set((state) => {
                            state.isStreaming = false;
                            state.streamingMessageId = null;
                        });
                    },

                    abortCurrentConversation: async () => {
                        const { currentSessionId } = get();
                        
                        if (currentSessionId) {
                            try {
                                // 调用后端停止聊天API
                                await client.stopChat(currentSessionId);
                                console.log('✅ 成功停止当前对话');
                            } catch (error) {
                                console.error('❌ 停止对话失败:', error);
                            }
                        }

                        set((state) => {
                            state.isStreaming = false;
                            state.streamingMessageId = null;
                            state.isLoading = false;
                        });
                    },

                    // UI操作
                    toggleSidebar: () => {
                        set((state) => {
                            state.sidebarOpen = !state.sidebarOpen;
                        });
                    },

                    setTheme: (theme: Theme) => {
                        set((state) => {
                            state.theme = theme;
                        });
                    },

                    // 配置操作
                    updateChatConfig: async (config: Partial<ChatConfig>) => {
                        set((state) => {
                            state.chatConfig = { ...state.chatConfig, ...config };
                        });
                    },

                    loadMcpConfigs: async () => {
                        try {
                            const userId = getUserIdParam();
                            const configs = await client.getMcpConfigs(userId);
                            set((state) => {
                                state.mcpConfigs = configs as McpConfig[];
                            });
                        } catch (error) {
                            console.error('Failed to load MCP configs:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to load MCP configs';
                            });
                        }
                    },

                    updateMcpConfig: async (config: McpConfig) => {
                        try {
                            const userId = getUserIdParam();
                            console.log('🔍 updateMcpConfig 调用:', { 
                                userId, 
                                customUserId, 
                                configId: config.id,
                                configName: config.name 
                            });
                            
                            if (config.id) {
                                const updateData = {
                                    id: config.id,
                                    name: config.name,
                                    command: config.command,
                                    enabled: config.enabled,
                                    userId,
                                };
                                console.log('🔍 updateMcpConfig 更新数据:', updateData);
                                await client.updateMcpConfig(config.id, updateData);
                            } else {
                                const createData = {
                                    id: crypto.randomUUID(),
                                    name: config.name,
                                    command: config.command,
                                    type: 'stdio' as const, // 添加必需的type字段，默认为stdio
                                    enabled: config.enabled,
                                    user_id: userId,
                                };
                                console.log('🔍 updateMcpConfig 创建数据:', createData);
                                await client.createMcpConfig(createData);
                            }
                            
                            // 重新加载配置
                            await get().loadMcpConfigs();
                        } catch (error) {
                            console.error('Failed to update MCP config:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to update MCP config';
                            });
                        }
                    },

                    deleteMcpConfig: async (id: string) => {
                        try {
                            await client.deleteMcpConfig(id);
                            set((state) => {
                                state.mcpConfigs = state.mcpConfigs.filter(config => config.id !== id);
                            });
                        } catch (error) {
                            console.error('Failed to delete MCP config:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to delete MCP config';
                            });
                        }
                    },

                    loadAiModelConfigs: async () => {
                        try {
                            const userId = getUserIdParam();
                            const apiConfigs = await client.getAiModelConfigs(userId) as any[];
                            
                            // 转换后端数据格式为前端格式
                            const configs = apiConfigs.map((config: any) => ({
                                id: config.id,
                                name: config.name,
                                base_url: config.base_url,
                                api_key: config.api_key,
                                model_name: config.model,
                                enabled: config.enabled,
                                createdAt: new Date(config.created_at),
                                updatedAt: new Date(config.created_at) // 使用created_at作为默认值
                            }));
                            
                            set((state) => {
                                state.aiModelConfigs = configs;
                            });
                        } catch (error) {
                            console.error('Failed to load AI model configs:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to load AI model configs';
                            });
                        }
                    },

                    updateAiModelConfig: async (config: AiModelConfig) => {
                        try {
                            const userId = getUserIdParam();
                            const existingConfig = get().aiModelConfigs.find(c => c.id === config.id);
                            const method = existingConfig ? 'update' : 'create';
                            
                            // 统一使用下划线格式的字段名称
                            const apiData = {
                                id: config.id || crypto.randomUUID(),
                                name: config.name,
                                provider: 'openai', // 默认provider
                                model: config.model_name,
                                api_key: config.api_key,
                                base_url: config.base_url,
                                enabled: config.enabled,
                                user_id: userId
                            };
                            
                            if (method === 'update') {
                                await client.updateAiModelConfig(config.id!, apiData);
                            } else {
                                await client.createAiModelConfig(apiData);
                            }
                            
                            // 重新加载配置
                            await get().loadAiModelConfigs();
                        } catch (error) {
                            console.error('Failed to update AI model config:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to update AI model config';
                            });
                        }
                    },

                    deleteAiModelConfig: async (id: string) => {
                        try {
                            await client.deleteAiModelConfig(id);
                            set((state) => {
                                state.aiModelConfigs = state.aiModelConfigs.filter(c => c.id !== id);
                            });
                        } catch (error) {
                            console.error('Failed to delete AI model config:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to delete AI model config';
                            });
                        }
                    },

                    setSelectedModel: (modelId: string | null) => {
                        set((state) => {
                            state.selectedModelId = modelId;
                        });
                    },

                    loadSystemContexts: async () => {
                        try {
                            const contexts = await client.getSystemContexts(getUserIdParam());
                            set((state) => {
                                state.systemContexts = contexts;
                            });
                        } catch (error) {
                            console.error('Failed to load system contexts:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to load system contexts';
                            });
                        }
                    },

                    createSystemContext: async (name: string, content: string) => {
                        try {
                            const context = await client.createSystemContext({
                                name,
                                content,
                                user_id: getUserIdParam(),
                            });
                            set((state) => {
                                state.systemContexts.push(context);
                            });
                        } catch (error) {
                            console.error('Failed to create system context:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to create system context';
                            });
                        }
                    },

                    updateSystemContext: async (id: string, name: string, content: string) => {
                        try {
                            const updatedContext = await client.updateSystemContext(id, { name, content });
                            set((state) => {
                                const index = state.systemContexts.findIndex(c => c.id === id);
                                if (index !== -1) {
                                    state.systemContexts[index] = updatedContext;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to update system context:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to update system context';
                            });
                        }
                    },

                    deleteSystemContext: async (id: string) => {
                        try {
                            await client.deleteSystemContext(id);
                            set((state) => {
                                state.systemContexts = state.systemContexts.filter(c => c.id !== id);
                                if (state.activeSystemContext?.id === id) {
                                    state.activeSystemContext = null;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to delete system context:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to delete system context';
                            });
                        }
                    },

                    activateSystemContext: async (id: string) => {
                        try {
                            const context = get().systemContexts.find(c => c.id === id);
                            set((state) => {
                                state.activeSystemContext = context || null;
                            });
                        } catch (error) {
                            console.error('Failed to activate system context:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to activate system context';
                            });
                        }
                    },

                    // 错误处理
                    setError: (error: string | null) => {
                        set((state) => {
                            state.error = error;
                        });
                    },

                    clearError: () => {
                        set((state) => {
                            state.error = null;
                        });
                    },
                }),
                {
                    name: 'chat-store-with-backend',
                    partialize: (state) => ({
                        theme: state.theme,
                        sidebarOpen: state.sidebarOpen,
                        chatConfig: state.chatConfig,
                        selectedModelId: state.selectedModelId,
                    }),
                }
            )
        )
    ));
}