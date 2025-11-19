/**
 * Messages API 路由 - 消息管理
 * 复刻自 Python: app/api/messages.py
 */

import express from 'express';
import { MessageService } from '../models/message.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

/**
 * GET /api/messages - 获取消息列表
 * 支持按 session_id 过滤
 */
router.get('/', async (req, res) => {
  try {
    const { session_id, limit, offset } = req.query;

    if (!session_id) {
      return res.status(400).json({ error: '必须提供 session_id' });
    }

    const messages = await MessageService.getBySession(
      session_id,
      limit ? parseInt(limit, 10) : null,
      offset ? parseInt(offset, 10) : 0
    );

    res.json(messages);
  } catch (error) {
    logger.error('获取消息列表失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/messages - 创建新消息
 */
router.post('/', async (req, res) => {
  try {
    const { sessionId, role, content, toolCalls, tool_call_id, reasoning, metadata } = req.body;

    if (!sessionId || !role || !content) {
      return res.status(400).json({ error: 'sessionId, role 和 content 不能为空' });
    }

    const message = await MessageService.create({
      sessionId,
      role,
      content,
      toolCalls,
      tool_call_id,
      reasoning,
      metadata
    });

    res.status(201).json(message);
  } catch (error) {
    logger.error('创建消息失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/messages/:id - 获取特定消息
 */
router.get('/:id', async (req, res) => {
  try {
    const message = await MessageService.getById(req.params.id);

    if (!message) {
      return res.status(404).json({ error: '消息不存在' });
    }

    res.json(message);
  } catch (error) {
    logger.error('获取消息失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * DELETE /api/messages/:id - 删除消息
 */
router.delete('/:id', async (req, res) => {
  try {
    await MessageService.delete(req.params.id);

    res.json({ success: true, message: '消息已删除' });
  } catch (error) {
    logger.error('删除消息失败:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
