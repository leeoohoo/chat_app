import AiRequestHandler from './aiRequestHandler';
import { conversationsApi } from '../api/index';
import type { Message, ToolCall, AiModelConfig } from '../../types';

interface McpToolExecute {
    executeStream(toolCall: ToolCall, onChunk: (chunk: string) => void, onComplete: () => void, onError: (error: Error) => void): Promise<void>;
    execute(toolCalls: ToolCall[]): Promise<any[]>;
    toolSupportsStreaming(toolName: string): boolean;
}

type CallbackType = 'chunk' | 'tool_call' | 'error' | 'complete' | 'tool_stream_chunk' | 'tool_result' | 'conversation_complete';

interface CallbackData {
    type?: string;
    content?: string;
    accumulated?: string;
    toolCallId?: string;
    chunk?: string;
}
class AiClient {
    private messages: Message[];
    private conversationId: string;
    private tools: any[];
    private modelConfig: AiModelConfig;
    private callBack: (type: CallbackType, data?: any) => void;
    private mcpToolExecute: McpToolExecute | null;
    private payLoad: any;
    private isAborted: boolean;
    private currentAiRequestHandler: AiRequestHandler | null;

    constructor(messages: Message[], conversationId: string, tools: any[], modelConfig: AiModelConfig, callBack: (type: CallbackType, data?: any) => void, mcpToolExecute: McpToolExecute | null) {
        this.messages = messages;
        this.conversationId = conversationId;
        this.tools = tools;
        this.modelConfig = modelConfig;
        this.callBack = callBack;
        this.mcpToolExecute = mcpToolExecute;
        this.payLoad = {}
        // 添加中止控制
        this.isAborted = false;
        this.currentAiRequestHandler = null;
    }



    async start() {
        await this.handleToolCallRecursively(25, 0)
    }

    async handleToolCallRecursively(maxRounds: number, currentRound: number): Promise<void> {
        //1. 判断是否已经到达最大轮次
        if(currentRound >= maxRounds) {
            this.callBack("error", "Maximum rounds reached");
            return;
        }

        // 检查是否已被中止
        if (this.isAborted) {
            console.log('AiClient: Request aborted');
            return;
        }

        //2. 判断最新的消息 的role 是否是assistant
        let message = this.messages[this.messages.length - 1]; // 修复: 使用数组索引获取最后一个消息

        if(message && message.role === "assistant") {
            //如果是助手的消息，要判断是否需要调用工具
            if((message as any).tool_calls && (message as any).tool_calls.length > 0) {
                // 检查是否已被中止
                if (this.isAborted) {
                    console.log('AiClient: Tool call execution aborted');
                    return;
                }

                this.callBack("tool_call", (message as any).tool_calls);

                // 处理工具调用 - 支持流式和普通调用
                let executeResult = [];
                
                for (const toolCall of (message as any).tool_calls) {
                    // 检查是否在工具执行过程中被中止
                    if (this.isAborted) {
                        console.log('AiClient: Aborted during tool execution');
                        return;
                    }
                    
                    const toolName = toolCall.function?.name || toolCall.name;
                    const supportsStreaming = this.mcpToolExecute!.toolSupportsStreaming(toolName);
                    
                    if (supportsStreaming) {
                        // 使用流式调用
                        console.log(`Using streaming execution for tool: ${toolName}`);
                        
                        const toolResult = {
                            tool_call_id: toolCall.id || `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                            role: 'tool',
                            name: toolName,
                            content: ''
                        };
                        
                        try {
                            await this.mcpToolExecute!.executeStream(
                                toolCall,
                                // onChunk: 接收流式数据
                                (chunk) => {
                                    if (this.isAborted) return;
                                    
                                    // 处理chunk数据，提取实际文本内容
                                    const processedChunk = this.processChunk(chunk);
                                    toolResult.content += processedChunk;
                                    
                                    // 通知界面更新工具执行进度，使用处理后的内容
                                    this.callBack("tool_stream_chunk", {
                                        toolCallId: toolCall.id,
                                        chunk: processedChunk,
                                    });
                                   
                                },
                                // onComplete: 流式调用完成
                                () => {
                                    if (this.isAborted) return;
                                    console.log(`Stream completed for tool: ${toolName}`);
                                },
                                // onError: 错误处理
                                (error) => {
                                    if (this.isAborted) return;
                                    console.error(`Stream error for tool ${toolName}:`, error);
                                    toolResult.content = JSON.stringify({
                                        error: error.message || 'Tool execution failed'
                                    });
                                }
                            );
                            
                            // 如果没有内容，设置默认结果
                            if (!toolResult.content) {
                                toolResult.content = JSON.stringify({ result: 'Tool execution completed' });
                            }
                            
                        } catch (error: any) {
                            console.error(`Failed to execute stream tool ${toolName}:`, error);
                            toolResult.content = JSON.stringify({
                                error: error.message || 'Tool execution failed'
                            });
                        }
                        
                        executeResult.push(toolResult);
                        
                    } else {
                        // 使用普通调用（单个工具）
                        console.log(`Using regular execution for tool: ${toolName}`);
                        const singleToolResult = await this.mcpToolExecute!.execute([toolCall]);
                        executeResult.push(...singleToolResult);
                    }
                }

                // 检查是否在工具执行过程中被中止
                if (this.isAborted) {
                    console.log('AiClient: Aborted after tool execution');
                    return;
                }

                // 保存工具调用结果
                for (const result of executeResult) {
                    // 处理工具调用结果的内容，提取实际文本而不是JSON格式
                    const processedResult = this.processToolResult(result);
                    await conversationsApi.addMessage(this.conversationId, processedResult);
                    this.messages.push(processedResult); // 修复: 使用 push 添加消息
                }

                // 通过callback通知展示层工具执行结果
                this.callBack("tool_result", executeResult);

                // 工具调用完成后，需要继续调用AI获取响应，而不是立即递归检查
                // 检查是否已被中止
                if (this.isAborted) {
                    console.log('AiClient: Aborted before chatCompletion after tool execution');
                    return;
                }
                
                await this.chatCompletion();
                
                // 检查是否在AI调用后被中止
                if (this.isAborted) {
                    console.log('AiClient: Aborted after chatCompletion after tool execution');
                    return;
                }
                
                await this.handleToolCallRecursively(maxRounds, currentRound + 1);
            } else {
                // 没有工具调用，对话完成
                this.callBack("conversation_complete", message);
                return;
            }
        } else {
            // 如果不是助手，那就是用户或者工具调用结果，这时候就继续调用ai
            // 检查是否已被中止
            if (this.isAborted) {
                console.log('AiClient: Aborted before chatCompletion');
                return;
            }
            
            await this.chatCompletion();
            
            // 检查是否在AI调用后被中止
            if (this.isAborted) {
                console.log('AiClient: Aborted after chatCompletion');
                return;
            }
            
            await this.handleToolCallRecursively(maxRounds, currentRound + 1);
        }
    }

    async chatCompletion(): Promise<void> {
        // 检查是否已被中止
        if (this.isAborted) {
            console.log('AiClient: chatCompletion aborted');
            return;
        }
        const aiRequestHandler = new AiRequestHandler(this.messages, this.tools, this.conversationId, this.callBack, this.modelConfig);
        this.currentAiRequestHandler = aiRequestHandler;

        try {
            this.messages = await aiRequestHandler.chatCompletion();
        } catch (error) {
            if (this.isAborted) {
                console.log('AiClient: chatCompletion was aborted');
                return;
            }
            throw error;
        } finally {
            this.currentAiRequestHandler = null;
        }
    }

    /**
     * 中止当前请求
     */
    abort() {
        console.log('AiClient: Aborting request');
        this.isAborted = true;
        if (this.currentAiRequestHandler) {
            this.currentAiRequestHandler.abort();
        }
    }

    /**
     * 检查是否已被中止
     * @returns {boolean}
     */
    isRequestAborted() {
        return this.isAborted;
    }

    /**
     * 处理单个chunk数据，提取实际文本内容
     * @param {string} chunk - 单个chunk数据
     * @returns {string} 处理后的文本内容
     */
    processChunk(chunk: any, has_data: boolean = false): string {
        if (!chunk || typeof chunk !== 'string') {
            return chunk || '';
        }

        try {
            // 去除可能的 'data: ' 前缀
            let cleanChunk = chunk;
            if (cleanChunk.startsWith('data: ')) {
                cleanChunk = cleanChunk.substring(6);
            }
            
            // 尝试解析JSON
            const parsedChunk = JSON.parse(cleanChunk);
            if (parsedChunk && typeof parsedChunk === 'object') {
                // 优先提取content字段
                if (parsedChunk.content) {
                    // 如果content是字符串且以'data: '开头，递归处理
                    if (typeof parsedChunk.content === 'string' && parsedChunk.content.startsWith('data: ')) {
                        return this.processChunk(parsedChunk.content,false);
                    } else {
                        return has_data? "\n" + parsedChunk.content + "": parsedChunk.content;
                    }
                } else if (parsedChunk.data) {
                    // 如果data是字符串且以'data: '开头，递归处理
                    if (typeof parsedChunk.data === 'string' && parsedChunk.data.startsWith('data: ')) {
                        return this.processChunk(parsedChunk.data,true);
                    } else {
                        return parsedChunk.data;
                    }
                } else if (parsedChunk.ai_stream_chunk) {
                    // 如果ai_stream_chunk是字符串且以'data: '开头，递归处理
                    if (typeof parsedChunk.ai_stream_chunk === 'string' && parsedChunk.ai_stream_chunk.startsWith('data: ')) {
                        return this.processChunk(parsedChunk.ai_stream_chunk,false);
                    } else {
                        return parsedChunk.ai_stream_chunk;
                    }
                }
            }
        } catch {
            // 如果不是JSON格式，直接返回原始内容
            return chunk;
        }
        
        return '';
    }

    /**
     * 处理工具调用结果，提取实际文本内容而不是JSON格式
     * @param {Object} result - 工具调用结果
     * @returns {Object} 处理后的结果
     */
    processToolResult(result: any): any {
        // 对于流式工具调用，内容已经在chunk级别处理过了，直接返回
        // 对于非流式工具调用，内容可能仍然是JSON格式，需要处理
        if (!result || !result.content) {
            return result;
        }

        let processedContent = result.content;
        
        // 检查是否是JSON格式的工具调用结果
        if (typeof processedContent === 'string' && processedContent.trim().startsWith('{')) {
            try {
                const parsed = JSON.parse(processedContent);
                // 如果是标准的工具调用结果格式，保持原样
                if (parsed.error || parsed.result !== undefined) {
                    return result;
                }
            } catch {
                // 不是有效JSON，保持原样
            }
        }

        return result;
    }
}
export default AiClient;