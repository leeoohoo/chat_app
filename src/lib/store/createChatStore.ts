import {create} from 'zustand';
import {subscribeWithSelector} from 'zustand/middleware';
import {immer} from 'zustand/middleware/immer';
import {persist} from 'zustand/middleware';
import type {Message, Session, ChatConfig, Theme, McpConfig, AiModelConfig, SystemContext} from '../../types';
import {DatabaseService} from '../database';
import {apiClient} from '../api/client';
// import {messageManager} from '../services/messageManager';
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
}

/**
 * 创建聊天store的工厂函数
 * @param customApiClient 自定义的API客户端实例，如果不提供则使用默认的apiClient
 * @param config 自定义配置，包含userId和projectId
 * @returns 聊天store hook
 */
export function createChatStore(customApiClient?: ApiClient, config?: ChatStoreConfig) {
    const client = customApiClient || apiClient;
    const customUserId = config?.userId;
    const customProjectId = config?.projectId;
    
    // 使用传入的参数或默认值
    const userId = customUserId || 'default-user';
    const projectId = customProjectId || 'default-project';
    
    // 获取userId的统一函数
    const getUserIdParam = () => userId;
    
    // 获取会话相关参数的统一函数
    const getSessionParams = () => {
        return { userId, projectId };
    };
    
    // 创建DatabaseService实例
    const databaseService = new DatabaseService(userId, projectId);
    
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
                                userId,
                                projectId
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
                        const { currentSession } = get();
                        if (!currentSession) {
                            throw new Error('No active session');
                        }

                        try {
                            set((state) => {
                                state.isLoading = true;
                                state.error = null;
                            });

                            // 创建用户消息
                            const userMessage = await databaseService.createMessage({
                                sessionId: currentSession.id,
                                role: 'user',
                                content,
                                status: 'completed',
                                createdAt: new Date(),
                                metadata: {
                                    attachments,
                                },
                            });

                            // 添加用户消息到状态
                            set((state) => {
                                state.messages.push(userMessage);
                            });

                            // 创建助手消息占位符
                            const assistantMessage = await databaseService.createMessage({
                                sessionId: currentSession.id,
                                role: 'assistant',
                                content: '',
                                status: 'streaming',
                                createdAt: new Date(),
                            });

                            // 添加助手消息到状态
                            set((state) => {
                                state.messages.push(assistantMessage);
                                state.streamingMessageId = assistantMessage.id;
                                state.isStreaming = true;
                            });

                            // 这里应该调用AI服务来处理消息
                            // 由于messageManager没有sendMessage方法，我们暂时跳过AI调用
                            // 实际使用时需要集成AI服务
                            
                            set((state) => {
                                state.isStreaming = false;
                                state.streamingMessageId = null;
                                state.isLoading = false;
                            });
                        } catch (error) {
                            console.error('Failed to send message:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to send message';
                                state.isLoading = false;
                                state.isStreaming = false;
                                state.streamingMessageId = null;
                            });
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
                                const messageIndex = state.messages.findIndex(
                                    m => m.id === state.streamingMessageId
                                );
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
                        try {
                            set((state) => {
                                state.chatConfig = { ...state.chatConfig, ...config };
                            });
                        } catch (error) {
                            console.error('Failed to update chat config:', error);
                            set((state) => {
                                state.error = error instanceof Error ? error.message : 'Failed to update chat config';
                            });
                        }
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
                                    command: config.serverUrl, // 使用serverUrl作为command
                                    enabled: config.enabled,
                                    userId,
                                };
                                console.log('🔍 updateMcpConfig 更新数据:', updateData);
                                await client.updateMcpConfig(config.id, updateData);
                            } else {
                                const createData = {
                                    id: crypto.randomUUID(),
                                    name: config.name,
                                    command: config.serverUrl,
                                    enabled: config.enabled,
                                    userId,
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
                            
                            // 转换字段名以匹配后端API
                            const apiData = {
                                id: config.id || crypto.randomUUID(),
                                name: config.name,
                                provider: 'openai', // 默认provider
                                model: config.model_name,
                                apiKey: config.api_key,
                                baseUrl: config.base_url,
                                enabled: config.enabled,
                                userId
                            };
                            
                            if (method === 'update') {
                                await client.updateAiModelConfig(apiData.id, apiData);
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
                                state.aiModelConfigs = state.aiModelConfigs.filter(config => config.id !== id);
                                // 如果删除的是当前选中的模型，清除选择
                                if (state.selectedModelId === id) {
                                    state.selectedModelId = null;
                                }
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
                            const activeContext = await client.getActiveSystemContext(getUserIdParam());
                            set((state) => {
                                state.systemContexts = contexts;
                                // 处理activeContext的返回格式
                                if (activeContext && activeContext.content) {
                                    // 从contexts中找到对应的完整上下文对象
                                    const fullActiveContext = contexts.find(ctx => ctx.content === activeContext.content);
                                    state.activeSystemContext = fullActiveContext || null;
                                } else {
                                    state.activeSystemContext = null;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to load system contexts:', error);
                            set((state) => {
                                state.systemContexts = [];
                                state.activeSystemContext = null;
                            });
                        }
                    },

                    createSystemContext: async (name: string, content: string) => {
                        try {
                            const newContext = await client.createSystemContext({
                                name,
                                content,
                                userId: getUserIdParam()
                            });
                            set((state) => {
                                state.systemContexts.push(newContext);
                            });
                        } catch (error) {
                            console.error('Failed to create system context:', error);
                            throw error;
                        }
                    },

                    updateSystemContext: async (id: string, name: string, content: string) => {
                        try {
                            const updatedContext = await client.updateSystemContext(id, { name, content });
                            set((state) => {
                                const index = state.systemContexts.findIndex(ctx => ctx.id === id);
                                if (index !== -1) {
                                    state.systemContexts[index] = updatedContext;
                                }
                                if (state.activeSystemContext?.id === id) {
                                    state.activeSystemContext = updatedContext;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to update system context:', error);
                            throw error;
                        }
                    },

                    deleteSystemContext: async (id: string) => {
                        try {
                            await client.deleteSystemContext(id);
                            set((state) => {
                                state.systemContexts = state.systemContexts.filter(ctx => ctx.id !== id);
                                if (state.activeSystemContext?.id === id) {
                                    state.activeSystemContext = null;
                                }
                            });
                        } catch (error) {
                            console.error('Failed to delete system context:', error);
                            throw error;
                        }
                    },

                    activateSystemContext: async (id: string) => {
                        try {
                            await client.activateSystemContext(id, getUserIdParam());
                            set((state) => {
                                const context = state.systemContexts.find(ctx => ctx.id === id);
                                if (context) {
                                    // 更新所有上下文的激活状态
                                    state.systemContexts.forEach(ctx => {
                                        ctx.isActive = ctx.id === id;
                                    });
                                    state.activeSystemContext = { ...context, isActive: true };
                                }
                            });
                        } catch (error) {
                            console.error('Failed to activate system context:', error);
                            throw error;
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
                    name: 'chat-store',
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