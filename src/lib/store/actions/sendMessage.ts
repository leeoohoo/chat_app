import type { Message } from '../../../types';
import type ApiClient from '../../api/client';

// 工厂函数：创建 sendMessage 处理器，注入依赖以便于在 store 外部维护
export function createSendMessageHandler({
  set,
  get,
  client,
  getUserIdParam,
}: {
  set: (fn: (state: any) => void) => void;
  get: () => any;
  client: ApiClient;
  getUserIdParam: () => string;
}) {
  return async function sendMessage(content: string, attachments: any[] = []) {
    const {
      currentSessionId,
      selectedModelId,
      aiModelConfigs,
      chatConfig,
      isLoading,
      isStreaming,
      activeSystemContext,
      selectedAgentId,
      agents,
    } = get();

    if (!currentSessionId) {
      throw new Error('No active session');
    }

    // 检查是否已经在发送消息，防止重复发送
    if (isLoading || isStreaming) {
      console.log('Message sending already in progress, ignoring duplicate request');
      return;
    }

    // 需要选择模型或智能体之一
    let selectedModel: any = null;
    let selectedAgent: any = null;
    if (selectedAgentId) {
      selectedAgent = agents.find((a: any) => a.id === selectedAgentId);
      if (!selectedAgent || selectedAgent.enabled === false) {
        throw new Error('选择的智能体不可用');
      }
    } else if (selectedModelId) {
      selectedModel = aiModelConfigs.find((model: any) => model.id === selectedModelId);
      if (!selectedModel || !selectedModel.enabled) {
        throw new Error('选择的模型不可用');
      }
    } else {
      throw new Error('请先选择一个模型或智能体');
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
          model: selectedAgent ? `[Agent] ${selectedAgent.name}` : selectedModel.model_name,
          ...(selectedModel
            ? {
                modelConfig: {
                  id: selectedModel.id,
                  name: selectedModel.name,
                  base_url: selectedModel.base_url,
                  model_name: selectedModel.model_name,
                },
              }
            : {}),
        },
      };

      set((state: any) => {
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
          model: selectedAgent ? `[Agent] ${selectedAgent.name}` : selectedModel.model_name,
          ...(selectedModel
            ? {
                modelConfig: {
                  id: selectedModel.id,
                  name: selectedModel.name,
                  base_url: selectedModel.base_url,
                  model_name: selectedModel.model_name,
                },
              }
            : {}),
          toolCalls: [], // 初始化工具调用数组
          contentSegments: [{ content: '', type: 'text' as const }], // 初始化内容分段
          currentSegmentIndex: 0, // 当前正在写入的分段索引
        },
      };

      set((state: any) => {
        state.messages.push(tempAssistantMessage);
        state.streamingMessageId = tempAssistantMessage.id;
      });

      // 准备聊天请求数据（根据选择的目标：模型或智能体）
      const chatRequest = selectedAgent
        ? {
            session_id: currentSessionId,
            message: content,
            // 仅在选择智能体时携带智能体信息，不包含模型配置
            agent_id: selectedAgent.id,
            system_context: activeSystemContext?.content || chatConfig.systemPrompt || '',
            attachments: attachments || [],
          }
        : {
            session_id: currentSessionId,
            message: content,
            // 仅在选择模型时携带模型配置
            model_config: {
              model: selectedModel.model_name,
              base_url: selectedModel.base_url,
              api_key: selectedModel.api_key || '',
              temperature: chatConfig.temperature,
              max_tokens: chatConfig.maxTokens,
            },
            system_context: activeSystemContext?.content || chatConfig.systemPrompt || '',
            attachments: attachments || [],
          };

      console.log('🚀 开始调用后端流式聊天API:', chatRequest);

      // 使用后端API进行流式聊天（模型或智能体）
      const response = selectedAgent
        ? await client.streamAgentChat(
            currentSessionId,
            content,
            selectedAgent.id,
            getUserIdParam()
          )
        : await client.streamChat(currentSessionId, content, selectedModel, getUserIdParam());

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
                    set((state: any) => {
                      const message = state.messages.find((m: any) => m.id === tempAssistantMessage.id);
                      if (message && message.metadata) {
                        // 确保parsed.content是字符串
                        const contentStr =
                          typeof parsed.content === 'string'
                            ? parsed.content
                            : typeof parsed === 'string'
                            ? parsed
                            : parsed.content || '';

                        // 获取当前分段索引
                        const currentIndex = message.metadata.currentSegmentIndex || 0;
                        const segments = message.metadata.contentSegments || [];

                        // 确保当前分段存在且为文本类型
                        if (segments[currentIndex] && segments[currentIndex].type === 'text') {
                          segments[currentIndex].content += contentStr;
                        } else {
                          // 如果当前分段不存在或不是文本类型，创建新的文本分段
                          segments.push({ content: contentStr, type: 'text' as const });
                          message.metadata.currentSegmentIndex = segments.length - 1;
                        }

                        // 更新完整内容用于向后兼容
                        message.content = segments
                          .filter((s: any) => s.type === 'text')
                          .map((s: any) => s.content)
                          .join('');
                      }
                    });
                  }
                } else if (parsed.type === 'thinking') {
                  // 新增类型：模型的思考过程（与正文分离，可折叠显示，灰色字体）
                  if (parsed.content) {
                    set((state: any) => {
                      const message = state.messages.find((m: any) => m.id === tempAssistantMessage.id);
                      if (message && message.metadata) {
                        const contentStr =
                          typeof parsed.content === 'string'
                            ? parsed.content
                            : typeof parsed === 'string'
                            ? parsed
                            : parsed.content || '';

                        const segments = message.metadata.contentSegments || [];
                        const lastIdx = segments.length - 1;

                        if (lastIdx >= 0 && segments[lastIdx].type === 'thinking') {
                          // 继续在当前思考分段追加
                          (segments[lastIdx] as any).content += contentStr;
                          message.metadata.currentSegmentIndex = lastIdx;
                        } else {
                          // 创建新的思考分段
                          segments.push({ content: contentStr, type: 'thinking' as const });
                          message.metadata.currentSegmentIndex = segments.length - 1;
                        }

                        // 正文只汇总 text 分段，思考不并入 message.content
                        message.content = segments
                          .filter((s: any) => s.type === 'text')
                          .map((s: any) => s.content)
                          .join('');
                      }
                    });
                  }
                } else if (parsed.type === 'content') {
                  // 兼容旧格式: {type: 'content', content: '...'}
                  // 更新UI中的流式消息，使用分段管理
                  set((state: any) => {
                    const message = state.messages.find((m: any) => m.id === tempAssistantMessage.id);
                    if (message && message.metadata) {
                      // 确保parsed.content是字符串
                      const contentStr =
                        typeof parsed.content === 'string'
                          ? parsed.content
                          : typeof parsed === 'string'
                          ? parsed
                          : parsed.content || '';

                      // 获取当前分段索引
                      const currentIndex = message.metadata.currentSegmentIndex || 0;
                      const segments = message.metadata.contentSegments || [];

                      // 确保当前分段存在且为文本类型
                      if (segments[currentIndex] && segments[currentIndex].type === 'text') {
                        segments[currentIndex].content += contentStr;
                      } else {
                        // 如果当前分段不存在或不是文本类型，创建新的文本分段
                        segments.push({ content: contentStr, type: 'text' as const });
                        message.metadata.currentSegmentIndex = segments.length - 1;
                      }

                      // 更新完整内容用于向后兼容
                      message.content = segments
                        .filter((s: any) => s.type === 'text')
                        .map((s: any) => s.content)
                        .join('');
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
                      createdAt: tc.createdAt || tc.created_at || new Date(), // 添加前端需要的createdAt，支持多种时间格式
                    };

                    console.log('🔧 [DEBUG] 转换后的工具调用:', toolCall);
                    return toolCall;
                  };

                  // 修复：从 parsed.data.tool_calls 中提取工具调用数组
                  console.log('🔧 [DEBUG] tools_start 原始数据:', parsed.data);
                  const rawToolCalls = parsed.data.tool_calls || parsed.data;
                  const toolCallsArray = Array.isArray(rawToolCalls) ? rawToolCalls : [rawToolCalls];
                  console.log('🔧 [DEBUG] 提取的工具调用数组:', toolCallsArray);

                  set((state: any) => {
                    const messageIndex = state.messages.findIndex((m: any) => m.id === tempAssistantMessage.id);
                    console.log('🔧 查找消息索引:', messageIndex, '消息ID:', tempAssistantMessage.id);
                    if (messageIndex !== -1) {
                      const message = state.messages[messageIndex];
                      console.log('🔧 找到消息，当前metadata:', message.metadata);
                      if (!message.metadata) {
                        message.metadata = {} as any;
                      }
                      if (!message.metadata.toolCalls) {
                        message.metadata.toolCalls = [] as any[];
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
                          toolCallId: toolCall.id,
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

                  set((state: any) => {
                    const messageIndex = state.messages.findIndex((m: any) => m.id === tempAssistantMessage.id);
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

                          console.log('🔍 查找工具调用:', toolCallId, '在消息中:', message.metadata?.toolCalls?.map((tc: any) => tc.id));
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
                                is_error: result.is_error,
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
                                is_stream: result.is_stream,
                              });
                            }
                          } else {
                            console.log('❌ 未找到对应的工具调用:', toolCallId);
                            console.log('📋 当前可用的工具调用ID:', message.metadata?.toolCalls?.map((tc: any) => tc.id));
                          }
                        });

                        // 强制触发消息更新以确保自动滚动
                        // 通过更新消息的 updatedAt 时间戳来触发 React 重新渲染
                        (message as any).updatedAt = new Date();
                      }
                    }
                  });
                } else if (parsed.type === 'tools_stream') {
                  // 处理工具流式返回内容
                  console.log('🔧 收到工具流式数据:', parsed.data);
                  const data = parsed.data;

                  set((state: any) => {
                    const messageIndex = state.messages.findIndex((m: any) => m.id === tempAssistantMessage.id);
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
                              is_error: data.is_error,
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
                              is_stream: data.is_stream,
                            });
                          }

                          // 强制触发UI更新
                          (message as any).updatedAt = new Date();
                        }
                      }
                    }
                  });
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
        set((state: any) => {
          state.isLoading = false;
          state.isStreaming = false;
          state.streamingMessageId = null;
        });
      }

      console.log('✅ 消息发送完成');
    } catch (error) {
      console.error('❌ 发送消息失败:', error);

      // 移除临时消息并显示错误
      set((state: any) => {
        const tempMessageIndex = state.messages.findIndex((m: any) => m.id?.startsWith('temp_'));
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
  };
}