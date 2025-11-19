/**
 * AI 请求处理器 - 处理与 OpenAI API 的交互
 * 复刻自 Python: app/services/v2/ai_request_handler.py
 */

import OpenAI from 'openai';
import { logger } from '../../utils/logger.js';

export class AiRequestHandler {
  constructor(openaiClient, messageManager) {
    this.openaiClient = openaiClient;
    this.messageManager = messageManager;
  }

  /**
   * 处理 AI 请求（支持流式和非流式）
   */
  async handleRequest(messages, options = {}) {
    const {
      tools = null,
      model = 'gpt-4',
      temperature = 0.7,
      maxTokens = null,
      onChunk = null,
      onThinkingChunk = null,
      stream = Boolean(onChunk || onThinkingChunk),
      session_id = null
    } = options;

    // 准备请求参数
    const requestParams = {
      model,
      messages,
      temperature
    };

    if (maxTokens) {
      requestParams.max_tokens = maxTokens;
    }

    if (tools && tools.length > 0) {
      requestParams.tools = tools;
      requestParams.tool_choice = 'auto';
    }

    if (stream) {
      requestParams.stream = true;
      requestParams.stream_options = { include_usage: true };
      return await this._handleStreamRequest(requestParams, session_id, onChunk, onThinkingChunk);
    } else {
      return await this._handleNormalRequest(requestParams, session_id);
    }
  }

  /**
   * 处理非流式请求
   */
  async _handleNormalRequest(requestParams, sessionId = null) {
    try {
      const response = await this.openaiClient.chat.completions.create(requestParams);

      const choice = response.choices[0];
      const message = choice.message;

      // 提取推理内容（不同模型字段可能不同）
      let reasoningText = null;
      try {
        if (message.reasoning_content) {
          reasoningText = message.reasoning_content;
        } else if (message.reasoning) {
          reasoningText = message.reasoning;
        }
      } catch (e) {
        reasoningText = null;
      }

      // 提取响应内容
      const result = {
        content: message.content || '',
        reasoning: reasoningText,
        tool_calls: message.tool_calls || null,
        finish_reason: choice.finish_reason,
        usage: response.usage
      };

      // 保存助手消息到数据库
      if (sessionId && this.messageManager) {
        const metadata = {};
        if (message.tool_calls) {
          metadata.toolCalls = message.tool_calls;
        }

        try {
          this.messageManager.saveAssistantMessage(
            sessionId,
            message.content || '',
            {
              reasoning: reasoningText || null,
              metadata: Object.keys(metadata).length > 0 ? metadata : null,
              toolCalls: message.tool_calls || null
            }
          );
        } catch (error) {
          logger.warn(`保存助手消息失败: ${error.message}`);
        }
      }

      return result;
    } catch (error) {
      logger.error('AI 请求失败:', error);
      throw error;
    }
  }

  /**
   * 处理流式请求
   */
  async _handleStreamRequest(requestParams, sessionId = null, onChunk, onThinkingChunk) {
    try {
      const stream = await this.openaiClient.chat.completions.create(requestParams);

      let fullContent = '';
      let reasoning = null;
      let toolCalls = [];
      let finishReason = null;
      let usage = null;

      // 用于累积工具调用
      const toolCallsMap = new Map();

      for await (const chunk of stream) {
        const delta = chunk.choices[0]?.delta;

        if (!delta) {
          // 处理 usage chunk
          if (chunk.usage) {
            usage = chunk.usage;
          }
          continue;
        }

        // 处理内容流
        if (delta.content) {
          fullContent += delta.content;
          if (onChunk) {
            onChunk(delta.content);
          }
        }

        // 处理推理内容（推理模型如 o1 会返回 reasoning_content）
        if (delta.reasoning_content) {
          if (!reasoning) reasoning = '';
          reasoning += delta.reasoning_content;
          if (onThinkingChunk) {
            onThinkingChunk(delta.reasoning_content);
          }
        } else if (delta.reasoning) {
          // 兼容可能的其他命名
          if (!reasoning) reasoning = '';
          reasoning += delta.reasoning;
          if (onThinkingChunk) {
            onThinkingChunk(delta.reasoning);
          }
        }

        // 处理工具调用
        if (delta.tool_calls) {
          for (const toolCallDelta of delta.tool_calls) {
            const index = toolCallDelta.index;

            if (!toolCallsMap.has(index)) {
              toolCallsMap.set(index, {
                id: toolCallDelta.id || '',
                type: 'function',
                function: {
                  name: '',
                  arguments: ''
                }
              });
            }

            const toolCall = toolCallsMap.get(index);

            if (toolCallDelta.id) {
              toolCall.id = toolCallDelta.id;
            }

            if (toolCallDelta.function) {
              if (toolCallDelta.function.name) {
                toolCall.function.name += toolCallDelta.function.name;
              }
              if (toolCallDelta.function.arguments) {
                toolCall.function.arguments += toolCallDelta.function.arguments;
              }
            }
          }
        }

        // 处理完成原因
        if (chunk.choices[0]?.finish_reason) {
          finishReason = chunk.choices[0].finish_reason;
        }
      }

      // 转换工具调用为数组
      if (toolCallsMap.size > 0) {
        toolCalls = Array.from(toolCallsMap.values());
      }

      // 保存助手消息到数据库
      if (sessionId && this.messageManager) {
        const metadata = {};
        if (toolCalls.length > 0) {
          metadata.toolCalls = toolCalls;
        }

        try {
          this.messageManager.saveAssistantMessage(
            sessionId,
            fullContent,
            {
              reasoning: reasoning || null,
              metadata: Object.keys(metadata).length > 0 ? metadata : null,
              toolCalls: toolCalls.length > 0 ? toolCalls : null
            }
          );
        } catch (error) {
          logger.warn(`保存助手消息失败: ${error.message}`);
        }
      }

      return {
        content: fullContent,
        reasoning,
        tool_calls: toolCalls.length > 0 ? toolCalls : null,
        finish_reason: finishReason,
        usage
      };
    } catch (error) {
      logger.error('AI 流式请求失败:', error);
      throw error;
    }
  }

  /**
   * 处理简单请求（不使用工具）
   */
  async handleSimpleRequest(messages, options = {}) {
    return await this.handleRequest(messages, {
      ...options,
      tools: null
    });
  }
}
