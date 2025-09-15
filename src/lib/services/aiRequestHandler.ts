
import OpenAI from 'openai';
import { conversationsApi } from '../api/index';
import type { Message, AiModelConfig } from '../../types';

type CallbackType = 'chunk' | 'error' | 'complete';

interface CallbackData {
    type?: string;
    content?: string;
    accumulated?: string;
}

class AiRequestHandler {
    private messages: Message[];
    private tools: any[];
    private conversationId: string;
    private callback: (type: CallbackType, data?: any) => void;
    private modelConfig: AiModelConfig;
    private stream: boolean;
    private useOpenAIPackage: boolean;
    private abortController: AbortController;
    private isAborted: boolean;

    constructor(messages: Message[], tools: any[], conversationId: string, callback: (type: CallbackType, data?: any) => void, modelConfig: AiModelConfig) {
        this.messages = messages;
        this.tools = tools;
        this.conversationId = conversationId;
        this.callback = callback;
        this.modelConfig = modelConfig;
        this.stream = true;
        // 添加一个标志来控制是否使用 OpenAI 包
        this.useOpenAIPackage = true; // 默认使用 OpenAI 包
        // 添加中止控制器
        this.abortController = new AbortController();
        this.isAborted = false;

    }

    /**
     * 发送聊天完成请求
     * @returns {Promise<Message[]>} 更新后的消息列表
     */
    async chatCompletion(): Promise<Message[]> {
        try {
            // 检查是否已被中止
            if (this.isAborted) {
                throw new Error('Request was aborted');
            }

            // 检查模型配置
            console.log('Using OpenAI package with base URL:', this.modelConfig.base_url);
            console.log('API Key:', this.modelConfig.api_key ? 'Present' : 'Missing');

            // 创建 OpenAI 客户端
            const openai = new OpenAI({
                apiKey: this.modelConfig.api_key,
                baseURL: this.modelConfig.base_url,
                dangerouslyAllowBrowser: true // 允许在浏览器中使用
            });

            // 构建请求参数
            const payload = this.buildPayLoad();

            // 使用 OpenAI 客户端发送流式请求
            const stream = await openai.chat.completions.create({
                ...payload,
                stream: true
            });

            // 处理流式响应
            await this.handleOpenAIStreamResponse(stream, this.callback);

            return this.messages;
        } catch (error: any) {
            console.error('Chat completion failed:', error);
            console.error('Error type:', error.constructor.name);
            console.error('Error message:', error.message);
            console.error('Error stack:', error.stack);

            // 检查是否是网络相关错误
            if (error.message.includes('CORS') || error.message.includes('fetch')) {
                console.error('This appears to be a CORS or network error. Check your base_url and API configuration.');
            }

            // 通过callback通知错误
            if (this.callback) {
                this.callback('error', error);
            }
            throw error;
        }
    }

    /**
     * 处理 OpenAI 包的流式响应
     * @param {AsyncIterable} stream - OpenAI 流式响应
     * @param {Function} callback - 回调函数
     */
    async handleOpenAIStreamResponse(stream: any, callback: (type: CallbackType, data?: any) => void): Promise<void> {
        // 初始化消息对象
        const message: any = {
            role: 'assistant',
            content: '',
            reasoning_content: '',
            tool_calls: [],
            model_info: {
                model: this.modelConfig.model_name,
                temperature: (this.modelConfig as any).temperature,
                max_tokens: (this.modelConfig as any).max_tokens
            },
            function_calls: [] // 兼容后端格式
        };

        try {
            console.log('Starting to process OpenAI stream...');
            let chunkCount = 0;
            let existingCall = null

            for await (const chunk of stream) {
                // 检查是否已被中止
                if (this.isAborted) {
                    console.log('Stream processing aborted');
                    break;
                }

                chunkCount++;
                if (chunk.choices && chunk.choices.length > 0) {
                    const choice = chunk.choices[0];
                    const delta = choice.delta;

                    if (delta) {
                        // 处理普通文本内容
                        if (delta.content) {
                            message.content += delta.content;
                            if (callback) {
                                callback('chunk', {
                                    type: 'text',
                                    content: delta.content,
                                });
                            }
                        }

                        // 处理推理内容（如果模型支持）
                        if (delta.reasoning_content) {
                            message.reasoning_content += delta.reasoning_content;
                            if (callback) {
                                callback('chunk', {
                                    type: 'reasoning_content',
                                    content: delta.reasoning_content,
                                    accumulated: message.reasoning_content
                                });
                            }
                        }

                        // 处理工具调用
                        if (delta.tool_calls) {
                            for (const toolCall of delta.tool_calls) {
                                // 检查 toolCall 是否有效，处理不同模型的兼容性
                                if (!toolCall) {
                                    console.warn('Invalid tool call:', toolCall);
                                    continue;
                                }

                                // 处理 index 为 null 或 undefined 的情况（如 Gemini）
                                let index = toolCall.index;
                                if (index === null || index === undefined || typeof index !== 'number') {
                                    // 如果没有有效的 index，使用当前数组长度作为 index
                                    index = message.tool_calls.length;
                                    console.log(`Tool call index was ${toolCall.index}, using ${index} instead`);
                                }

                                // 确保tool_calls数组有足够的元素
                                while (message.tool_calls.length <= index) {
                                    message.tool_calls.push({
                                        id: '',
                                        type: 'function',
                                        function: {
                                            name: '',
                                            arguments: ''
                                        }
                                    });
                                }

                                existingCall = message.tool_calls[index];

                                // 确保 existingCall.function 存在
                                if (!existingCall.function) {
                                    existingCall.function = {
                                        name: '',
                                        arguments: ''
                                    };
                                }

                                // 处理 ID，如果为空字符串则生成一个
                                if (toolCall.id && toolCall.id !== '') {
                                    existingCall.id = toolCall.id;
                                } else if (!existingCall.id || existingCall.id === '') {
                                    // 为 Gemini 等模型生成一个临时 ID
                                    existingCall.id = `call_${Date.now()}_${index}`;
                                }

                                if (toolCall.function) {
                                    if (toolCall.function.name) {
                                        existingCall.function.name = toolCall.function.name;
                                    }
                                    if (toolCall.function.arguments) {
                                    existingCall.function.arguments += toolCall.function.arguments;
                                }
                                }


                            }
                        }
                    }
                }
            }

            console.log(`OpenAI stream completed. Processed ${chunkCount} chunks.`);

            // 处理工具调用的function_calls格式（兼容后端）
            if (message.tool_calls.length > 0) {
                message.function_calls = message.tool_calls.map((toolCall: any) => ({
                    id: toolCall.id,
                    name: toolCall.function.name,
                    arguments: toolCall.function.arguments
                }));
            }

            // 最后把完整的消息添加到messages列表
            this.messages.push(message);

            // 保存助手消息到数据库
            try {
                console.log('Final message content before saving:', message.content);
                console.log('Final message content length:', message.content?.length || 0);

                // 检查是否有内容需要保存
                if (!message.content && (!message.tool_calls || message.tool_calls.length === 0)) {
                    console.warn('No content or tool calls to save, skipping message save');
                    return;
                }

                const messageData = {
                    role: 'assistant',
                    content: message.content || '',
                    reasoning_content: message.reasoning_content || ''
                };

                // 只有在有工具调用时才添加相关字段
                if (message.tool_calls && message.tool_calls.length > 0) {
                    (messageData as any).tool_calls = message.tool_calls;
                }
                if (message.function_calls && message.function_calls.length > 0) {
                    (messageData as any).function_calls = message.function_calls;
                }

                console.log('Saving assistant message:', messageData);
                await conversationsApi.addMessage(this.conversationId, messageData);
                console.log('Assistant message saved successfully');
            } catch (saveError: any) {
            console.error('Failed to save assistant message:', saveError);
                console.error('Save error details:', saveError.response?.data);
            }

            // AI响应处理完成，消息已保存

        } catch (error) {
            console.error('Stream processing error:', error);
            if (callback) {
                callback('error', error);
            }
            throw error;
        }
    }



    /**
     * 构建请求体
     * @returns {Object} 符合OpenAI格式的请求体
     */
    buildPayLoad() {
        // 转换消息格式为 OpenAI 标准格式
        const openaiMessages = this.convertToOpenAIFormat(this.messages);


        // 完全不传递temperature和top_p，让API使用默认值
        const requestData = {
            model: this.modelConfig.model_name || 'gpt-3.5-turbo',
            messages: openaiMessages,
            max_tokens: (this.modelConfig as any).max_tokens || 4000
        };

        // 如果有工具，添加工具配置
        if (this.tools && this.tools.length > 0) {
            (requestData as any).tools = this.tools;
        }

        return requestData;
    }

    /**
     * 清理HTML标签和多余的空白字符
     * @param {string} content - 原始内容
     * @returns {string} 清理后的纯文本内容
     */
    cleanHtmlContent(content: any): string {
        if (!content || typeof content !== 'string') {
            return '';
        }
        
        // 移除HTML标签，但保留换行符
        let cleanContent = content.replace(/<[^>]*>/g, '');
        
        // 解码HTML实体
        cleanContent = cleanContent
            .replace(/&amp;/g, '&')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&nbsp;/g, ' ');
        
        // 清理多余的空白字符，但保留有意义的换行
        cleanContent = cleanContent
            .replace(/[ \t]+/g, ' ')  // 多个空格和制表符替换为单个空格
            .replace(/\n[ \t]*/g, '\n')  // 移除换行后的空格和制表符
            .replace(/\n{3,}/g, '\n\n')  // 三个或更多连续换行替换为双换行
            .trim();  // 去除首尾空白
        
        return cleanContent;
    }

    /**
     * 将项目内部消息格式转换为 OpenAI 标准格式
     * @param {Array} messages - 项目内部消息格式
     * @returns {Array} OpenAI 标准格式的消息
     */
    convertToOpenAIFormat(messages: any[]): any[] {
        return messages.map(msg => {
            // 获取原始内容
            let content = msg.content || msg.message || '';
            
            // 如果是助手消息，清理HTML标签
            if (msg.role === 'assistant') {
                content = this.cleanHtmlContent(content);
            }
            
            // 基础消息格式
            const openaiMsg = {
                role: msg.role,
                content: content
            };

            // 如果是 assistant 消息且包含工具调用
            if (msg.role === 'assistant' && (msg.tool_calls || msg.function_calls)) {
                const toolCalls = msg.tool_calls || msg.function_calls || [];
                if (toolCalls.length > 0) {
                    console.log('Converting tool calls for assistant message:', toolCalls);
                    (openaiMsg as any).tool_calls = toolCalls.map((call: any) => {
                        // 获取函数名和参数，兼容不同格式
                        const functionName = call.function?.name || call.name;
                        const functionArgs = call.function?.arguments || call.arguments;

                        // 确保函数名存在
                        if (!functionName) {
                            console.warn('Tool call missing function name:', call);
                            return null; // 跳过无效的工具调用
                        }

                        // 确保参数格式正确
                        let argsString;
                        if (typeof functionArgs === 'string') {
                            argsString = functionArgs;
                        } else if (functionArgs && typeof functionArgs === 'object') {
                            argsString = JSON.stringify(functionArgs);
                        } else {
                            argsString = '{}'; // 默认空对象
                        }

                        // 验证 JSON 格式
                        try {
                            JSON.parse(argsString);
                        } catch (e: any) {
                            console.warn('Invalid JSON in tool call arguments, using empty object:', argsString, e);
                            argsString = '{}';
                        }

                        const result = {
                            id: call.id || `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                            type: call.type || 'function',
                            function: {
                                name: functionName,
                                arguments: argsString
                            }
                        };

                        console.log('Converted tool call:', result);
                        return result;
                    }).filter((call: any) => call !== null); // 过滤掉无效的工具调用
                }
            }

            // 如果是工具调用结果消息
            if (msg.role === 'tool') {
                (openaiMsg as any).tool_call_id = msg.tool_call_id;
            }

            return openaiMsg;
        }).filter((msg: any) => 
            // 过滤掉无效消息
            msg.role && (msg.content || (msg as any).tool_calls)
        );
    }

    /**
     * 中止当前请求
     */
    abort() {
        console.log('AiRequestHandler: Aborting request');
        this.isAborted = true;
        if (this.abortController) {
            this.abortController.abort();
        }
    }

    /**
     * 检查是否已被中止
     * @returns {boolean}
     */
    isRequestAborted() {
        return this.isAborted;
    }
}
export default AiRequestHandler;