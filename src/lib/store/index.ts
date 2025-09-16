import {create} from 'zustand';
import {subscribeWithSelector} from 'zustand/middleware';
import {immer} from 'zustand/middleware/immer';
import {persist} from 'zustand/middleware';
import type {Message, Session, ChatConfig, Theme, McpConfig, AiModelConfig, ContentSegment} from '../../types';
import {databaseService} from '../database';
import {apiClient} from '../api/client';
import {messageManager} from '../services/messageManager';
// import { generateId } from '../utils';

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

    // 配置
    chatConfig: ChatConfig;
    mcpConfigs: McpConfig[];
    aiModelConfigs: AiModelConfig[];
    selectedModelId: string | null;
    systemContext: string | null;

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
    loadSystemContext: () => Promise<void>;
    updateSystemContext: (content: string) => Promise<void>;

    // 错误处理
    setError: (error: string | null) => void;
    clearError: () => void;
}

// 创建聊天store
export const useChatStore = create<ChatState & ChatActions>()
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
                systemContext: null,
                selectedModelId: null,
                error: null,

                // 会话操作
                loadSessions: async () => {
                    try {
                        set((state) => {
                            state.isLoading = true;
                            state.error = null;
                        });

                        const sessions = await databaseService.getAllSessions();

                        set((state) => {
                            state.sessions = sessions;
                            state.isLoading = false;
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to load sessions';
                            state.isLoading = false;
                        });
                    }
                },

                createSession: async (title = 'New Chat') => {
                    try {
                        const session = await databaseService.createSession({
                            title,
                            createdAt: new Date(),
                            updatedAt: new Date(),
                            messageCount: 0,
                            tokenUsage: 0,
                            pinned: false,
                            archived: false,
                        });

                        set((state) => {
                            state.sessions.unshift(session);
                            state.currentSessionId = session.id;
                            state.currentSession = session;
                            state.messages = [];
                        });

                        return session.id;
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to create session';
                        });
                        throw error;
                    }
                },

                selectSession: async (sessionId: string) => {
                    try {
                        console.log('🔍 selectSession 被调用，sessionId:', sessionId);
                        set((state) => {
                            state.isLoading = true;
                            state.error = null;
                        });
                        console.log('✅ isLoading 已设置为 true');

                        const {conversationsApi} = await import('../api');
                        const sessionResponse = await conversationsApi.getDetails(sessionId);
                        const messagesResponse = await conversationsApi.getMessages(sessionId);
                        console.log('✅ API 调用完成，获取到会话和消息数据');
                        console.log('📊 原始消息数据结构:', messagesResponse);
                        const messages = messagesResponse.data?.messages || [];
                        console.log('📊 解析后的消息数组:', messages.length, '条消息');
                        messages.forEach((msg: any, index: number) => {
                            console.log(`📝 消息 ${index + 1}:`, {
                                id: msg.id,
                                role: msg.role,
                                content: msg.content ? msg.content.substring(0, 100) + '...' : '(空内容)',
                                metadata: msg.metadata,
                                hasToolCalls: !!(msg.metadata && msg.metadata.toolCalls),
                                toolCallsCount: msg.metadata?.toolCalls ? msg.metadata.toolCalls.length : 0,
                                toolCallsPreview: msg.metadata?.toolCalls ? msg.metadata.toolCalls.map((tc: any) => tc.name || tc.type) : []
                            });
                        });

                        set((state) => {
                            state.currentSessionId = sessionId;
                            const conversation = sessionResponse.data.conversation;
                            state.currentSession = {
                                id: conversation.id,
                                title: conversation.title,
                                createdAt: new Date(conversation.created_at),
                                updatedAt: new Date(conversation.updated_at),
                                messageCount: (conversation as any).messageCount || 0,
                                tokenUsage: (conversation as any).tokenUsage || 0,
                                tags: (conversation as any).tags || null,
                                pinned: (conversation as any).pinned || false,
                                archived: (conversation as any).archived || false,
                                metadata: (conversation as any).metadata || null
                            };
                            // 转换消息格式并确保正确排序
                            const messages = messagesResponse.data.messages.map((msg: any, index: number) => {
                                const processed = {
                                    ...msg,
                                    createdAt: new Date(msg.created_at || msg.createdAt),
                                    updatedAt: msg.updated_at ? new Date(msg.updated_at) : undefined,
                                    status: msg.status || 'completed'
                                };
                                console.log(`🔄 处理消息 ${index + 1} (${msg.id}):`, {
                                    原始content: msg.content,
                                    原始metadata: msg.metadata,
                                    处理后content: processed.content,
                                    处理后metadata: processed.metadata
                                });
                                return processed;
                            });

                            // 按创建时间排序，确保最早的消息在前面，最新的在后面
                            state.messages = messages.sort((a: any, b: any) => {
                                const timeA = a.createdAt.getTime();
                                const timeB = b.createdAt.getTime();
                                return timeA - timeB;
                            });
                            console.log('✅ 最终存储的messages数量:', messages.length);
                            state.isLoading = false;
                        });
                        console.log('✅ selectSession 完成，currentSessionId 已设置为:', sessionId);
                    } catch (error) {
                        console.error('❌ selectSession 失败:', error);
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to load session';
                            state.isLoading = false;
                        });
                    }
                },

                updateSession: async (sessionId: string, updates: Partial<Session>) => {
                    try {
                        await databaseService.updateSession(sessionId, updates);

                        set((state) => {
                            const sessionIndex = state.sessions.findIndex(s => s.id === sessionId);
                            if (sessionIndex !== -1) {
                                state.sessions[sessionIndex] = {...state.sessions[sessionIndex], ...updates};
                            }

                            if (state.currentSessionId === sessionId && state.currentSession) {
                                state.currentSession = {...state.currentSession, ...updates};
                            }
                        });
                    } catch (error) {
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
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to delete session';
                        });
                    }
                },

                // 消息操作
                loadMessages: async (sessionId: string) => {
                    try {
                        const {conversationsApi} = await import('../api');
                        const messagesResponse = await conversationsApi.getMessages(sessionId);

                        console.log('=== loadMessages Debug ===');
                        console.log('Session ID:', sessionId);
                        console.log('Raw messages from API:', messagesResponse.data.messages.length);
                        
                        messagesResponse.data.messages.forEach((msg: any, index: number) => {
                            console.log(`Message ${index + 1}:`, {
                                id: msg.id,
                                role: msg.role,
                                content: msg.content ? msg.content.substring(0, 100) + '...' : '[EMPTY]',
                                hasToolCalls: !!(msg.toolCalls || msg.metadata?.toolCalls),
                                tool_calls: msg.tool_calls ? 'YES' : 'NO'
                            });
                        });

                        set((state) => {
                            // 转换消息格式并确保正确排序
                            const messages = messagesResponse.data.messages.map((msg: any) => {
                                // 构建metadata对象，确保工具调用正确映射
                                const metadata = {
                                    ...msg.metadata,
                                    // 将服务器返回的toolCalls字段映射到metadata.toolCalls
                                    toolCalls: msg.toolCalls || msg.metadata?.toolCalls || [],
                                };

                                return {
                                    ...msg,
                                    createdAt: new Date(msg.created_at || msg.createdAt),
                                    status: msg.status || 'completed',
                                    metadata
                                };
                            });

                            // 按创建时间排序，确保最早的消息在前面，最新的在后面
                            state.messages = messages.sort((a: any, b: any) => {
                                const timeA = a.createdAt.getTime();
                                const timeB = b.createdAt.getTime();
                                return timeA - timeB;
                            });
                            
                            console.log('Final processed messages:', state.messages.length);
                            state.messages.forEach((msg: any, index: number) => {
                                console.log(`Processed ${index + 1}:`, {
                                    id: msg.id,
                                    role: msg.role,
                                    content: msg.content ? msg.content.substring(0, 50) + '...' : '[EMPTY]',
                                    hasMetadataToolCalls: !!(msg.metadata?.toolCalls?.length),
                                    toolCallsCount: msg.metadata?.toolCalls?.length || 0
                                });
                            });
                        });
                    } catch (error) {
                        console.error('loadMessages error:', error);
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to load messages';
                        });
                    }
                },

                sendMessage: async (content: string, attachments = []) => {
                    const {currentSessionId, selectedModelId, aiModelConfigs} = get();

                    if (!currentSessionId) {
                        throw new Error('No active session');
                    }

                    if (!selectedModelId) {
                        throw new Error('请先选择一个AI模型');
                    }

                    const selectedModel = aiModelConfigs.find(model => model.id === selectedModelId);
                    if (!selectedModel || !selectedModel.enabled) {
                        throw new Error('选择的模型不可用');
                    }

                    try {
                        // 创建用户消息
                        const userMessageTime = new Date();
                        const userMessage = await messageManager.saveUserMessage({
                            sessionId: currentSessionId,
                            role: 'user',
                            content,
                            status: 'completed',
                            createdAt: userMessageTime,
                            metadata: {
                                ...(attachments.length > 0 ? {attachments} : {}),
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

                        // 使用ChatService发送消息
                        const {chatService} = await import('../services');

                        // 构建模型配置
                        const {chatConfig} = get();
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
                                                 const toolCall = message.metadata!.toolCalls!.find((tc: any) => tc.id === result.toolCallId);
                                                 if (toolCall) {
                                                     toolCall.result = result.result;
                                                 }
                                             });
                                         } else if (results.toolCallId) {
                                             const toolCall = message.metadata!.toolCalls!.find((tc: any) => tc.id === results.toolCallId);
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
                                         const toolCall = message.metadata.toolCalls.find((tc: any) => tc.id === data.toolCallId);
                                         if (toolCall) {
                                             toolCall.result = (toolCall.result || '') + data.chunk;
                                         }
                                     }
                                 });
                            },
                            onComplete: async (data: any) => {
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
                                        
                                        // 工具调用结果的保存由toolResultProcessor统一处理，避免重复保存
                                        // 这里只保存assistant消息，tool消息由ToolResultProcessor处理
                                        
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
                                // 处理错误
                                set((state) => {
                                    state.error = error.message || 'AI response failed';
                                    state.isLoading = false;
                                    state.isStreaming = false;
                                    state.streamingMessageId = null;
                                });
                            }
                        }, modelConfig);

                    } catch (error) {
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
                        // 过滤掉数据库不支持的字段，特别是'tool'角色
                        const dbUpdates = {
                            ...updates,
                            // 如果role是'tool'，则不更新role字段
                            ...(updates.role === 'tool' ? { role: undefined } : {})
                        };
                        
                        // 移除undefined的role字段
                        if (dbUpdates.role === undefined) {
                            delete (dbUpdates as any).role;
                        }
                        
                        await databaseService.updateMessage(messageId, dbUpdates as any);

                        set((state) => {
                            const messageIndex = state.messages.findIndex(m => m.id === messageId);
                            if (messageIndex !== -1) {
                                state.messages[messageIndex] = {...state.messages[messageIndex], ...updates};
                            }
                        });
                    } catch (error) {
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
                    const {streamingMessageId} = get();
                    if (!streamingMessageId) return;

                    set((state) => {
                        const messageIndex = state.messages.findIndex(m => m.id === streamingMessageId);
                        if (messageIndex !== -1) {
                            state.messages[messageIndex].content = content;
                        }
                    });
                },

                stopStreaming: () => {
                    const {streamingMessageId} = get();

                    set((state) => {
                        state.isStreaming = false;
                        state.isLoading = false;
                        state.streamingMessageId = null;
                    });

                    // 保存最终消息到数据库
                    if (streamingMessageId) {
                        const message = get().messages.find(m => m.id === streamingMessageId);
                        if (message) {
                            databaseService.updateMessage(streamingMessageId, {
                                content: message.content,
                                updatedAt: new Date(),
                            });
                        }
                    }
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
                        const newConfig = {...get().chatConfig, ...config};

                        set((state) => {
                            state.chatConfig = newConfig;
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to update config';
                        });
                    }
                },

                loadMcpConfigs: async () => {
                    try {
                        const configs = await apiClient.getMcpConfigs() as any[];
                        set((state) => {
                            state.mcpConfigs = configs.map((config: any) => ({
                                id: config.id,
                                name: config.name,
                                serverUrl: config.command, // 后端使用command字段存储serverUrl
                                enabled: config.enabled,
                                createdAt: new Date(config.created_at),
                                updatedAt: new Date(config.updated_at)
                            }));
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to load MCP configs';
                        });
                    }
                },

                updateMcpConfig: async (config: McpConfig) => {
                    try {
                        const configIndex = get().mcpConfigs.findIndex(c => c.id === config.id);

                        if (configIndex !== -1) {
                            // 更新现有配置
                            await apiClient.updateMcpConfig(config.id, {
                                name: config.name,
                                command: config.serverUrl, // 后端使用command字段存储serverUrl
                                enabled: config.enabled,
                                args: [],
                                env: {}
                            });
                        } else {
                            // 创建新配置
                            await apiClient.createMcpConfig({
                                id: config.id,
                                name: config.name,
                                command: config.serverUrl, // 后端使用command字段存储serverUrl
                                enabled: config.enabled,
                                args: [],
                                env: {}
                            });
                        }

                        // 更新本地状态
                        set((state) => {
                            const configIndex = state.mcpConfigs.findIndex(c => c.id === config.id);
                            if (configIndex !== -1) {
                                state.mcpConfigs[configIndex] = config;
                            } else {
                                state.mcpConfigs.push(config);
                            }
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to update MCP config';
                        });
                    }
                },

                deleteMcpConfig: async (id: string) => {
                    try {
                        await apiClient.deleteMcpConfig(id);
                        set((state) => {
                            state.mcpConfigs = state.mcpConfigs.filter(config => config.id !== id);
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to delete MCP config';
                        });
                    }
                },

                // AI模型配置操作
                loadAiModelConfigs: async () => {
                    try {
                        const response = await fetch('/api/ai-model-configs');
                        if (!response.ok) {
                            throw new Error('Failed to load AI model configs');
                        }
                        const apiConfigs = await response.json();

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
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to load AI model configs';
                        });
                    }
                },

                updateAiModelConfig: async (config: AiModelConfig) => {
                    try {
                        const existingConfig = get().aiModelConfigs.find(c => c.id === config.id);
                        const method = existingConfig ? 'PUT' : 'POST';
                        const url = existingConfig ? `/api/ai-model-configs/${config.id}` : '/api/ai-model-configs';

                        // 转换字段名以匹配后端API
                        const apiData = {
                            id: config.id,
                            name: config.name,
                            provider: 'openai', // 默认provider
                            model: config.model_name,
                            apiKey: config.api_key,
                            baseUrl: config.base_url,
                            enabled: config.enabled
                        };

                        const response = await fetch(url, {
                            method,
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(apiData),
                        });

                        if (!response.ok) {
                            const errorText = await response.text();
                            throw new Error(`Failed to save AI model config: ${errorText}`);
                        }

                        // 更新本地状态
                        set((state) => {
                            const configIndex = state.aiModelConfigs.findIndex(c => c.id === config.id);
                            if (configIndex !== -1) {
                                state.aiModelConfigs[configIndex] = config;
                            } else {
                                state.aiModelConfigs.push(config);
                            }
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to update AI model config';
                        });
                    }
                },

                deleteAiModelConfig: async (id: string) => {
                    try {
                        const response = await fetch(`/api/ai-model-configs/${id}`, {
                            method: 'DELETE',
                        });

                        if (!response.ok) {
                            throw new Error('Failed to delete AI model config');
                        }

                        // 更新本地状态
                        set((state) => {
                            state.aiModelConfigs = state.aiModelConfigs.filter(config => config.id !== id);
                            // 如果删除的是当前选中的模型，清除选择
                            if (state.selectedModelId === id) {
                                state.selectedModelId = null;
                            }
                        });
                    } catch (error) {
                        set((state) => {
                            state.error = error instanceof Error ? error.message : 'Failed to delete AI model config';
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

                setSelectedModel: (modelId: string | null) => {
                    set((state) => {
                        state.selectedModelId = modelId;
                    });
                },

                // 系统上下文操作
                loadSystemContext: async () => {
                    try {
                        console.log('Store: Loading system context from API');
                        const response = await apiClient.getSystemContext();
                        console.log('Store: API response:', response);
                        set((state) => {
                            state.systemContext = response.content || null;
                        });
                        console.log('Store: System context set to:', response.content || null);
                    } catch (error) {
                        console.error('Store: Failed to load system context:', error);
                        set((state) => {
                            state.systemContext = null;
                        });
                    }
                },

                updateSystemContext: async (content: string) => {
                    try {
                        await apiClient.updateSystemContext(content);
                        set((state) => {
                            state.systemContext = content;
                        });
                    } catch (error) {
                        console.error('Failed to update system context:', error);
                        throw error;
                    }
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

// 选择器hooks
export const useCurrentSession = () => useChatStore((state) => state.currentSession);
export const useMessages = () => useChatStore((state) => state.messages);
export const useSessions = () => useChatStore((state) => state.sessions);
export const useIsLoading = () => useChatStore((state) => state.isLoading);
export const useIsStreaming = () => useChatStore((state) => state.isStreaming);
export const useTheme = () => useChatStore((state) => state.theme);
export const useSidebarOpen = () => useChatStore((state) => state.sidebarOpen);
export const useError = () => useChatStore((state) => state.error);
export const useAiModelConfigs = () => useChatStore((state) => state.aiModelConfigs);
export const useSelectedModelId = () => useChatStore((state) => state.selectedModelId);