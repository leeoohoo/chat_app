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
 * 创建聊天store的工厂函数
 * @param customApiClient 自定义的API客户端实例，如果不提供则使用默认的apiClient
 * @param config 自定义配置，包含userId和projectId
 * @returns 聊天store hook
 */
export function createChatStore(customApiClient?: ApiClient, config?: ChatStoreConfig) {
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
    
    // 创建DatabaseService实例（传入ApiClient，避免默认 '/api' 导致Electron环境相对路径问题）
    const databaseService = new DatabaseService(userId, projectId, customApiClient || apiClient);
    
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
                        const { currentSessionId, selectedModelId, aiModelConfigs, chatConfig, isLoading, isStreaming } = get();

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
                            // 创建用户消息并保存到数据库
                            const userMessageTime = new Date();
                            const userMessage = await messageManager.saveUserMessage({
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
                            });

                            set((state) => {
                                state.messages.push(userMessage);
                                state.isLoading = true;
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
                                state.isStreaming = true;
                                state.streamingMessageId = tempAssistantMessage.id;
                            });

                            // 构建模型配置
                            const modelConfig = selectedModel ? {
                                model_name: selectedModel.model_name,
                                temperature: chatConfig.temperature,
                                max_tokens: 16000,
                                api_key: selectedModel.api_key,
                                base_url: selectedModel.base_url
                            } : undefined;

                            // 设置回调函数处理AI响应
                            await chatService.sendMessage(currentSessionId, content, attachments, {
                                onChunk: (data: any) => {
                                    // 更新流式消息内容
                                    set((state) => {
                                        const message = state.messages.find(m => m.id === tempAssistantMessage.id);
                                        if (message && message.metadata) {
                                            // 确保data.content是字符串，如果是对象则提取content字段
                                            const content = typeof data.content === 'string' ? data.content :
                                                (typeof data === 'string' ? data :
                                                    (data.content || ''));
                                            
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
                                },
                                onToolCall: (toolCalls: any) => {
                                    // 处理工具调用
                                    console.log('Tool calls:', toolCalls);
                                    set((state) => {
                                        const message = state.messages.find(m => m.id === tempAssistantMessage.id);
                                        if (message && message.metadata) {
                                            // 将工具调用添加到消息的metadata中
                                            if (!message.metadata.toolCalls) {
                                                message.metadata.toolCalls = [];
                                            }
                                            
                                            const segments = message.metadata.contentSegments || [];
                                            
                                            // 添加新的工具调用
                                            if (Array.isArray(toolCalls)) {
                                                toolCalls.forEach((tc: any) => {
                                                    const toolCall = {
                                                        id: tc.id,
                                                        messageId: message.id,
                                                        name: tc.function?.name || tc.name,
                                                        arguments: tc.function?.arguments || tc.arguments,
                                                        result: '',
                                                        createdAt: new Date()
                                                    };
                                                    message.metadata!.toolCalls!.push(toolCall);
                                                    
                                                    // 添加工具调用分段
                                                    segments.push({
                                                        content: '',
                                                        type: 'tool_call' as const,
                                                        toolCallId: toolCall.id
                                                    });
                                                });
                                            } else {
                                                const toolCall = {
                                                    id: toolCalls.id,
                                                    messageId: message.id,
                                                    name: toolCalls.function?.name || toolCalls.name,
                                                    arguments: toolCalls.function?.arguments || toolCalls.arguments,
                                                    result: '',
                                                    createdAt: new Date()
                                                };
                                                message.metadata!.toolCalls!.push(toolCall);
                                                
                                                // 添加工具调用分段
                                                segments.push({ 
                                                    content: '',
                                                    type: 'tool_call' as const,
                                                    toolCallId: toolCalls.id
                                                });
                                            }
                                            
                                            // 为工具调用后的内容创建新的文本分段
                                            segments.push({ content: '', type: 'text' as const });
                                            message.metadata!.currentSegmentIndex = segments.length - 1;
                                        }
                                    });
                                },
                                onToolResult: (results: any) => {
                                    // 处理工具结果
                                    console.log('Tool results:', results);
                                    set((state) => {
                                        const message = state.messages.find(m => m.id === tempAssistantMessage.id);
                                        if (message && message.metadata && message.metadata.toolCalls) {
                                            // 更新对应工具调用的结果
                                            if (Array.isArray(results)) {
                                                results.forEach((result: any) => {
                                                    const toolCall = message.metadata!.toolCalls!.find((tc: any) => tc.id === result.tool_call_id);
                                                    if (toolCall) {
                                                        toolCall.result = result.result;
                                                    }
                                                });
                                            } else if (results.tool_call_id) {
                                                const toolCall = message.metadata!.toolCalls!.find((tc: any) => tc.id === results.tool_call_id);
                                                if (toolCall) {
                                                    toolCall.result = results.result;
                                                }
                                            }
                                        }
                                    });
                                },
                                onToolStreamChunk: (data: any) => {
                                    // 更新工具调用的流式返回内容
                                    set((state) => {
                                        const message = state.messages.find(m => m.id === tempAssistantMessage.id);
                                        if (message && message.metadata && message.metadata.toolCalls) {
                                            const toolCall = message.metadata.toolCalls.find((tc: any) => tc.id === data.tool_call_id);
                                            if (toolCall) {
                                                toolCall.result = (toolCall.result || '') + data.chunk;
                                            }
                                        }
                                    });
                                },
                                onComplete: async () => {
                                    // 完成流式响应，将临时消息转换为真实消息并保存
                                    try {
                                        const tempMessage = get().messages.find(m => m.id === tempAssistantMessage.id);
                                        if (tempMessage) {
                                            // 准备保存数据，包含工具调用信息
                                            const messageData: any = {
                                                sessionId: currentSessionId,
                                                role: 'assistant',
                                                content: tempMessage.content,
                                                status: 'completed',
                                                createdAt: tempMessage.createdAt,
                                                metadata: tempMessage.metadata
                                            };
                                            
                                            // 如果有工具调用，添加toolCalls字段
                                            if (tempMessage.metadata?.toolCalls && tempMessage.metadata.toolCalls.length > 0) {
                                                messageData.toolCalls = tempMessage.metadata.toolCalls.map((tc: any) => ({
                                                    id: tc.id,
                                                    function: {
                                                        name: tc.name,
                                                        arguments: typeof tc.arguments === 'string' ? tc.arguments : JSON.stringify(tc.arguments)
                                                    }
                                                }));
                                            }
                                            
                                            // 保存助手消息到数据库
                                            const savedMessage = await messageManager.saveAssistantMessage(messageData);
                                            
                                            // 确保保存的消息包含完整的contentSegments数据
                                            if (tempMessage.metadata?.contentSegments && 
                                                (!savedMessage.metadata?.contentSegments || 
                                                 savedMessage.metadata.contentSegments.length === 0)) {
                                                console.warn('ContentSegments lost during save, preserving from temp message');
                                                if (!savedMessage.metadata) {
                                                    savedMessage.metadata = {};
                                                }
                                                savedMessage.metadata.contentSegments = tempMessage.metadata.contentSegments;
                                            }
                                            
                                            // 更新状态，用真实消息替换临时消息
                                            set((state) => {
                                                const tempIndex = state.messages.findIndex(m => m.id === tempAssistantMessage.id);
                                                if (tempIndex !== -1) {
                                                    state.messages[tempIndex] = savedMessage;
                                                }
                                                state.isLoading = false;
                                                state.isStreaming = false;
                                                state.streamingMessageId = null;
                                            });
                                            
                                            // 重新选择当前会话以确保工具调用正确显示
                                            if (currentSessionId) {
                                                await get().selectSession(currentSessionId);
                                            }
                                        }
                                    } catch (error) {
                                        console.error('Failed to save assistant message:', error);
                                        // 如果保存失败，仍然更新状态
                                        set((state) => {
                                            state.isLoading = false;
                                            state.isStreaming = false;
                                            state.streamingMessageId = null;
                                        });
                                    }
                                },
                                onError: (error: any) => {
                                    // 检查是否是用户主动中断的错误
                                    const isUserAborted = error.message === 'Stream aborted by user' || 
                                                         error.message === 'Request was aborted' ||
                                                         error.message === 'Stream request was aborted' ||
                                                         error.message?.includes('aborted by user') ||
                                                         error.message?.includes('was aborted') ||
                                                         error.name === 'AbortError';
                                    
                                    if (isUserAborted) {
                                        // 用户主动中断，不显示错误信息，只更新状态
                                        console.log('Stream aborted by user - not showing error message');
                                        set((state) => {
                                            state.isLoading = false;
                                            state.isStreaming = false;
                                            state.streamingMessageId = null;
                                            // 不设置 error，避免显示红色警告
                                        });
                                    } else {
                                        // 真正的错误，显示错误信息
                                        console.error('AI request error:', error);
                                        set((state) => {
                                            state.error = error.message || 'AI response failed';
                                            state.isLoading = false;
                                            state.isStreaming = false;
                                            state.streamingMessageId = null;
                                        });
                                    }
                                }
                            }, modelConfig);
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

                    abortCurrentConversation: () => {
                        console.log('abortCurrentConversation 被调用');
                        try {
                            // 调用ChatService的停止方法
                            chatService.abortCurrentConversation();
                            console.log('ChatService.abortCurrentConversation 调用成功');
                        } catch (error) {
                            console.error('调用 ChatService.abortCurrentConversation 时出错:', error);
                        }
                        // 更新状态
                        set((state) => {
                            state.isStreaming = false;
                            state.streamingMessageId = null;
                            state.isLoading = false;
                        });
                        console.log('状态已更新: isStreaming=false, isLoading=false');
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
                                    command: config.command,
                                    type: config.type, // 确保更新时传递协议类型
                                    args: config.args ?? undefined,
                                    env: config.env ?? undefined,
                                    cwd: (config as any).cwd ?? undefined,
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
                                    type: (config.type ?? 'stdio') as 'http' | 'stdio', // 使用表单选择的类型
                                    args: config.args ?? undefined,
                                    env: config.env ?? undefined,
                                    cwd: (config as any).cwd ?? undefined,
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
                            
                            // 转换字段名以匹配后端API
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
                            const activeContextResponse = await client.getActiveSystemContext(getUserIdParam());
                            set((state) => {
                                // 先将所有上下文的isActive设为false
                                const updatedContexts = contexts.map(ctx => ({
                                    ...ctx,
                                    isActive: false
                                }));
                                
                                // 处理激活的上下文
                                if (activeContextResponse && activeContextResponse.context) {
                                    const activeContext = activeContextResponse.context;
                                    // 找到对应的上下文并设置为激活状态
                                    const activeIndex = updatedContexts.findIndex(ctx => ctx.id === activeContext.id);
                                    if (activeIndex !== -1) {
                                        updatedContexts[activeIndex].isActive = true;
                                        state.activeSystemContext = { ...updatedContexts[activeIndex] };
                                    } else {
                                        state.activeSystemContext = null;
                                    }
                                } else {
                                    state.activeSystemContext = null;
                                }
                                
                                state.systemContexts = updatedContexts;
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
                                user_id: getUserIdParam()
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