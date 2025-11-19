/**
 * 工具结果处理器 - 处理工具执行结果
 * 复刻自 Python: app/services/v2/tool_result_processor.py
 */

import { logger } from '../../utils/logger.js';

export class ToolResultProcessor {
  constructor(messageManager, aiRequestHandler) {
    this.messageManager = messageManager;
    this.aiRequestHandler = aiRequestHandler;
  }

  /**
   * 处理工具执行结果
   */
  async processToolResults(toolResults, sessionId, options = {}) {
    const { generateSummary = true } = options;

    try {
      // 1. 保存每个工具结果为消息
      for (const result of toolResults) {
        this.messageManager.saveToolMessage(
          sessionId,
          result.content,
          result.tool_call_id,
          {
            metadata: {
              toolName: result.name,
              success: result.success,
              isError: result.is_error
            }
          }
        );
      }

      // 2. 如果需要生成摘要（对于长内容）
      if (generateSummary) {
        for (const result of toolResults) {
          if (result.content && result.content.length > 5000) {
            // 内容过长，生成摘要
            logger.info(`工具结果过长 (${result.content.length} 字符)，生成摘要...`);
            // 这里可以调用 AI 生成摘要，暂时简化处理
          }
        }
      }

      return {
        success: true,
        processed_count: toolResults.length
      };
    } catch (error) {
      logger.error('处理工具结果失败:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
}
