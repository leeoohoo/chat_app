/**
 * AI 客户端 - 协调 AI 请求和工具调用的递归处理
 * 复刻自 Python: app/services/v2/ai_client.py
 */

import { logger } from '../../utils/logger.js';

export class AiClient {
  constructor(aiRequestHandler, mcpToolExecute, toolResultProcessor, messageManager) {
    this.aiRequestHandler = aiRequestHandler;
    this.mcpToolExecute = mcpToolExecute;
    this.toolResultProcessor = toolResultProcessor;
    this.messageManager = messageManager;

    // 配置参数
    this.maxIterations = 25;           // 防止无限循环
    this.summaryThreshold = 15;        // 自动摘要触发阈值
    this.summaryKeepLastN = 2;         // 摘要后保留最近 N 条
    this.historyLimit = 2;             // 默认加载最近 N 条历史

    // 系统提示
    this.systemPrompt = null;
  }

  /**
   * 处理 AI 请求（包含工具调用的递归）
   */
  async processRequest(messages, sessionId, options = {}) {
    const {
      model = 'gpt-4',
      temperature = 0.7,
      maxTokens = null,
      onChunk = null,
      onThinkingChunk = null,
      systemPrompt = null,
      historyLimit = null,
      onToolsStart = null,
      onToolsStream = null,
      onToolsEnd = null
    } = options;

    try {
      // 1. 加载历史消息
      const limit = historyLimit !== null ? historyLimit : this.historyLimit;
      let historyMessages = [];
      if (limit > 0) {
        const dbMessages = await this.messageManager.getSessionMessages(sessionId, limit);
        historyMessages = this._convertToOpenAIMessages(dbMessages);
      }

      // 2. 合并系统提示和消息
      const allMessages = [];

      // 添加系统提示
      const finalSystemPrompt = systemPrompt || this.systemPrompt;
      if (finalSystemPrompt) {
        allMessages.push({
          role: 'system',
          content: finalSystemPrompt
        });
      }

      // 添加历史消息
      allMessages.push(...historyMessages);

      // 添加当前消息
      allMessages.push(...messages);

      // 3. 获取可用工具
      const tools = this.mcpToolExecute.getAvailableTools();

      // 4. 调用递归处理
      return await this._processWithTools(
        allMessages,
        tools,
        sessionId,
        model,
        temperature,
        maxTokens,
        onChunk,
        onThinkingChunk,
        systemPrompt || this.systemPrompt,
        onToolsStart,
        onToolsStream,
        onToolsEnd,
        0  // iteration = 0
      );
    } catch (error) {
      logger.error('处理 AI 请求失败:', error);
      throw error;
    }
  }

  /**
   * 递归处理工具调用
   */
  async _processWithTools(
    apiMessages,
    tools,
    sessionId,
    model,
    temperature,
    maxTokens,
    onChunk,
    onThinkingChunk,
    systemPrompt,
    onToolsStart,
    onToolsStream,
    onToolsEnd,
    iteration
  ) {
    // 检查迭代次数
    if (iteration >= this.maxIterations) {
      logger.warn(`达到最大迭代次数 (${this.maxIterations})，停止工具调用`);
      return {
        success: false,
        error: '达到最大迭代次数',
        iteration
      };
    }

    logger.info(`AI 请求迭代 ${iteration}，消息数量: ${apiMessages.length}`);

    // 调用 AI
    const aiResponse = await this.aiRequestHandler.handleRequest(apiMessages, {
      tools,
      model,
      temperature,
      maxTokens,
      onChunk,
      onThinkingChunk,
      session_id: sessionId
    });

    const { content, reasoning, tool_calls, finish_reason } = aiResponse;

    // 如果没有工具调用，返回结果
    if (!tool_calls || tool_calls.length === 0) {
      logger.info('AI 响应完成，无工具调用');
      return {
        success: true,
        content,
        reasoning,
        tool_calls: null,
        finish_reason,
        iteration
      };
    }

    // 有工具调用
    logger.info(`AI 请求了 ${tool_calls.length} 个工具调用`);

    // 触发工具开始回调
    if (onToolsStart) {
      onToolsStart(tool_calls);
    }

    // 构建助手消息（包含工具调用）
    const assistantMessage = {
      role: 'assistant',
      content: content || null
    };

    if (tool_calls) {
      assistantMessage.tool_calls = tool_calls;
    }

    // 执行工具调用
    const toolResults = await this.mcpToolExecute.executeToolsStream(
      tool_calls,
      (result) => {
        if (onToolsStream) {
          onToolsStream(result);
        }
      }
    );

    // 触发工具完成回调
    if (onToolsEnd) {
      onToolsEnd(toolResults);
    }

    // 保存工具结果到数据库
    for (const toolResult of toolResults) {
      this.messageManager.saveToolMessage(
        sessionId,
        toolResult.content,
        toolResult.tool_call_id,
        {
          metadata: {
            toolName: toolResult.name,
            success: toolResult.success,
            isError: toolResult.is_error
          }
        }
      );
    }

    // 构建工具消息
    const toolMessages = toolResults.map(result => ({
      role: 'tool',
      tool_call_id: result.tool_call_id,
      content: result.content
    }));

    // 递归调用：添加助手消息和工具结果
    const newMessages = [
      ...apiMessages,
      assistantMessage,
      ...toolMessages
    ];

    return await this._processWithTools(
      newMessages,
      tools,
      sessionId,
      model,
      temperature,
      maxTokens,
      null,  // 后续迭代不再流式输出 chunk
      null,  // 后续迭代不再流式输出 thinking
      systemPrompt,
      onToolsStart,
      onToolsStream,
      onToolsEnd,
      iteration + 1
    );
  }

  /**
   * 处理简单请求（不使用工具）
   */
  async processSimpleRequest(messages, sessionId, options = {}) {
    const {
      model = 'gpt-4',
      temperature = 0.7,
      maxTokens = null,
      onThinkingChunk = null
    } = options;

    try {
      const aiResponse = await this.aiRequestHandler.handleRequest(messages, {
        tools: null,  // 不使用工具
        model,
        temperature,
        maxTokens,
        onChunk: null,
        onThinkingChunk
      });

      return {
        success: true,
        content: aiResponse.content,
        reasoning: aiResponse.reasoning,
        finish_reason: aiResponse.finish_reason
      };
    } catch (error) {
      logger.error('处理简单请求失败:', error);
      throw error;
    }
  }

  /**
   * 设置系统提示
   */
  setSystemPrompt(prompt) {
    this.systemPrompt = prompt;
  }

  /**
   * 转换数据库消息为 OpenAI 格式
   */
  _convertToOpenAIMessages(dbMessages) {
    return dbMessages.map(msg => {
      if (msg.role === 'tool') {
        return {
          role: 'tool',
          tool_call_id: msg.tool_call_id,
          content: msg.content
        };
      }

      const message = {
        role: msg.role,
        content: msg.content
      };

      if (msg.toolCalls && msg.toolCalls.length > 0) {
        message.tool_calls = msg.toolCalls;
      }

      return message;
    });
  }
}
