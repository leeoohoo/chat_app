/**
 * AI 服务主类 - 协调所有组件
 * 复刻自 Python: app/services/v2/ai_server.py
 */

import OpenAI from 'openai';
import { MessageManager } from './message-manager.js';
import { AiRequestHandler } from './ai-request-handler.js';
import { AiClient } from './ai-client.js';
import { McpToolExecute } from './mcp-tool-execute.js';
import { ToolResultProcessor } from './tool-result-processor.js';
import { logger } from '../../utils/logger.js';

export class AiServer {
  constructor(options = {}) {
    const {
      openaiApiKey,
      mcpToolExecute = null,
      defaultModel = 'gpt-4',
      defaultTemperature = 0.7,
      baseUrl = null
    } = options;

    // 初始化 OpenAI 客户端
    this.openaiClient = new OpenAI({
      apiKey: openaiApiKey,
      baseURL: baseUrl
    });

    // 初始化组件
    this.messageManager = new MessageManager();
    this.aiRequestHandler = new AiRequestHandler(this.openaiClient, this.messageManager);
    this.mcpToolExecute = mcpToolExecute || new McpToolExecute();
    this.toolResultProcessor = new ToolResultProcessor(this.messageManager, this.aiRequestHandler);
    this.aiClient = new AiClient(
      this.aiRequestHandler,
      this.mcpToolExecute,
      this.toolResultProcessor,
      this.messageManager
    );

    // 默认配置
    this.defaultModel = defaultModel;
    this.defaultTemperature = defaultTemperature;
  }

  /**
   * 聊天处理（支持工具调用）
   */
  async chat(sessionId, userMessage, options = {}) {
    const {
      model = this.defaultModel,
      temperature = this.defaultTemperature,
      maxTokens = null,
      useTools = true,
      onChunk = null,
      onThinkingChunk = null,
      onToolsStart = null,
      onToolsStream = null,
      onToolsEnd = null
    } = options;

    try {
      // 1. 保存用户消息
      const saveResult = this.messageManager.saveUserMessage(sessionId, userMessage);
      if (!saveResult.success) {
        throw new Error(saveResult.error);
      }

      // 2. 准备消息
      const messages = [
        {
          role: 'user',
          content: userMessage
        }
      ];

      // 3. 处理 AI 请求
      const result = await this.aiClient.processRequest(messages, sessionId, {
        model,
        temperature,
        maxTokens,
        onChunk,
        onThinkingChunk,
        onToolsStart,
        onToolsStream,
        onToolsEnd
      });

      // 4. 保存助手消息
      if (result.success) {
        this.messageManager.saveAssistantMessage(
          sessionId,
          result.content || '',
          {
            reasoning: result.reasoning,
            toolCalls: result.tool_calls
          }
        );
      }

      return result;
    } catch (error) {
      logger.error('聊天处理失败:', error);
      throw error;
    }
  }

  /**
   * 流式聊天处理
   */
  async streamChat(sessionId, userMessage, options = {}) {
    return await this.chat(sessionId, userMessage, options);
  }

  /**
   * 获取可用工具列表
   */
  getAvailableTools() {
    return this.mcpToolExecute.getAvailableTools();
  }

  /**
   * 设置系统提示
   */
  setSystemPrompt(prompt) {
    this.aiClient.setSystemPrompt(prompt);
  }

  /**
   * 获取消息管理器
   */
  getMessageManager() {
    return this.messageManager;
  }
}
