/**
 * Sessions API 路由 - 会话管理
 * 复刻自 Python: app/api/sessions.py
 */

import express from 'express';
import { SessionService } from '../models/session.js';
import { logger } from '../utils/logger.js';

const router = express.Router();

/**
 * GET /api/sessions - 获取会话列表
 * 支持按 user_id 和 project_id 过滤
 */
router.get('/', async (req, res) => {
  try {
    const { user_id, project_id } = req.query;

    let sessions;
    if (user_id || project_id) {
      sessions = await SessionService.getByUserProject(user_id, project_id);
    } else {
      sessions = await SessionService.getAll();
    }

    res.json(sessions);
  } catch (error) {
    logger.error('获取会话列表失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/sessions - 创建新会话
 */
router.post('/', async (req, res) => {
  try {
    const { title, description, metadata, user_id, project_id } = req.body;

    if (!title) {
      return res.status(400).json({ error: '会话标题不能为空' });
    }

    const sessionId = await SessionService.create({
      title,
      description,
      metadata,
      user_id,
      project_id
    });

    const session = await SessionService.getById(sessionId);

    res.status(201).json(session);
  } catch (error) {
    logger.error('创建会话失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/sessions/:id - 获取特定会话
 */
router.get('/:id', async (req, res) => {
  try {
    const session = await SessionService.getById(req.params.id);

    if (!session) {
      return res.status(404).json({ error: '会话不存在' });
    }

    res.json(session);
  } catch (error) {
    logger.error('获取会话失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PUT /api/sessions/:id - 更新会话
 */
router.put('/:id', async (req, res) => {
  try {
    const { title, description, metadata } = req.body;

    await SessionService.update(req.params.id, {
      title,
      description,
      metadata
    });

    const session = await SessionService.getById(req.params.id);

    res.json(session);
  } catch (error) {
    logger.error('更新会话失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * DELETE /api/sessions/:id - 删除会话
 */
router.delete('/:id', async (req, res) => {
  try {
    await SessionService.delete(req.params.id);

    res.json({ success: true, message: '会话已删除' });
  } catch (error) {
    logger.error('删除会话失败:', error);
    res.status(500).json({ error: error.message });
  }
});

// ==================== MCP 服务器关联 ====================

import { getDatabaseSync } from '../models/database-factory.js';
import { v4 as uuidv4 } from 'uuid';

/**
 * GET /api/sessions/:session_id/mcp-servers - 获取会话的MCP服务器配置
 */
router.get('/:session_id/mcp-servers', async (req, res) => {
  try {
    const { session_id } = req.params;
    const db = getDatabaseSync();

    const servers = db.fetchallSync(
      'SELECT * FROM session_mcp_servers WHERE session_id = ?',
      [session_id]
    );

    logger.info(`获取会话 ${session_id} 的 ${servers.length} 个MCP服务器`);
    res.json(servers);
  } catch (error) {
    logger.error('获取会话MCP服务器失败:', error);
    res.status(500).json({ error: '获取会话MCP服务器失败' });
  }
});

/**
 * POST /api/sessions/:session_id/mcp-servers - 添加会话MCP服务器关联
 */
router.post('/:session_id/mcp-servers', async (req, res) => {
  try {
    const { session_id } = req.params;
    const { mcp_server_name, mcp_config_id } = req.body;
    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    db.executeSync(
      `INSERT INTO session_mcp_servers (id, session_id, mcp_server_name, mcp_config_id, created_at)
       VALUES (?, ?, ?, ?, ?)`,
      [id, session_id, mcp_server_name, mcp_config_id || null, now]
    );

    logger.info(`为会话 ${session_id} 添加MCP服务器成功: ${id}`);
    res.status(201).json({ id, session_id, mcp_server_name });
  } catch (error) {
    logger.error('添加会话MCP服务器失败:', error);
    res.status(500).json({ error: '添加会话MCP服务器失败' });
  }
});

/**
 * DELETE /api/sessions/:session_id/mcp-servers/:mcp_config_id - 删除会话MCP服务器关联
 */
router.delete('/:session_id/mcp-servers/:mcp_config_id', async (req, res) => {
  try {
    const { session_id, mcp_config_id } = req.params;
    const db = getDatabaseSync();

    db.executeSync(
      'DELETE FROM session_mcp_servers WHERE session_id = ? AND (id = ? OR mcp_config_id = ?)',
      [session_id, mcp_config_id, mcp_config_id]
    );

    logger.info(`删除会话 ${session_id} 的MCP服务器关联成功`);
    res.json({ success: true });
  } catch (error) {
    logger.error('删除会话MCP服务器关联失败:', error);
    res.status(500).json({ error: '删除会话MCP服务器关联失败' });
  }
});

// ==================== 会话消息（Python 路径格式） ====================

import { MessageService } from '../models/message.js';

/**
 * GET /api/sessions/:session_id/messages - 获取会话的消息列表
 */
router.get('/:session_id/messages', async (req, res) => {
  try {
    const { session_id } = req.params;
    let { limit, offset } = req.query;

    // 兼容前端可能传入的 limit=0（表示不限制）
    if (limit !== undefined && parseInt(limit, 10) === 0) {
      limit = null;
    } else if (limit) {
      limit = parseInt(limit, 10);
    }

    // 解析偏移量（用于分页“加载更多”）
    if (offset !== undefined) {
      offset = parseInt(offset, 10);
      if (Number.isNaN(offset) || offset < 0) offset = 0;
    }

    let messages;
    if (limit) {
      // 当提供 limit 时，按“最近”分页返回
      if (offset) {
        messages = await MessageService.getRecentPageBySession(session_id, limit, offset);
      } else {
        messages = await MessageService.getRecentBySession(session_id, limit);
      }
    } else {
      // 未提供 limit，保持历史行为：返回全部，按时间升序
      messages = await MessageService.getBySession(session_id, null);
    }

    logger.info(`获取会话 ${session_id} 的 ${messages.length} 条消息 (limit=${limit || 'all'}, offset=${offset || 0})`);
    res.json(messages);
  } catch (error) {
    logger.error('获取会话消息失败:', error);
    res.status(500).json({ error: '获取会话消息失败' });
  }
});

/**
 * POST /api/sessions/:session_id/messages - 创建新消息
 */
router.post('/:session_id/messages', async (req, res) => {
  try {
    const { session_id } = req.params;
    const { role, content, tool_calls, tool_call_id, reasoning, metadata } = req.body;

    const message = await MessageService.create({
      sessionId: session_id,
      role,
      content,
      toolCalls: tool_calls,
      tool_call_id,
      reasoning,
      metadata
    });

    logger.info(`创建消息成功: ${message.id}`);
    res.status(201).json(message);
  } catch (error) {
    logger.error('创建消息失败:', error);
    res.status(500).json({ error: '创建消息失败' });
  }
});

export default router;
