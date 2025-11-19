/**
 * Chat API v2 (Agent 版本)
 * 复刻自 Python: app/api/chat_api_agent_v2.py
 * 使用 Agent 封装实现 /v2/chat/stream 流式接口
 */

import express from 'express';
import { buildSseStream } from '../services/v2/agent.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

/**
 * POST /v2/chat/stream - 基于 Agent 的流式聊天接口
 */
router.post('/chat/stream', async (req, res) => {
  try {
    const { session_id, content, ai_model_config, user_id } = req.body;

    if (!session_id || !content) {
      return res.status(400).json({
        error: 'session_id 和 content 不能为空'
      });
    }

    // 设置 SSE 响应头
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    try {
      const modelConfig = ai_model_config || {};
      const stream = buildSseStream(session_id, content, modelConfig, user_id);

      // 迭代异步生成器并写入响应
      for await (const chunk of stream) {
        res.write(chunk);
      }

      // 发送结束标记
      res.write('data: [DONE]\n\n');

    } catch (error) {
      logger.error('chat_stream_v2_agent error:', error);
      const errorEvent = {
        type: 'error',
        data: { error: error.message },
        timestamp: new Date().toISOString()
      };
      res.write(`data: ${JSON.stringify(errorEvent)}\n\n`);
    } finally {
      res.end();
    }

  } catch (error) {
    logger.error('v2 流式聊天失败:', error);
    if (!res.headersSent) {
      res.status(500).json({ error: error.message });
    } else {
      res.end();
    }
  }
});

export default router;
