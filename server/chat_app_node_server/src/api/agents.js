/**
 * 智能体管理 API
 * 复刻自 Python: app/api/agents.py
 */

import express from 'express';
import { getDatabaseSync } from '../models/database-factory.js';
import { buildSseStreamFromAgentId } from '../services/v2/agent.js';
import { logger } from '../utils/logger.js';
import { v4 as uuidv4 } from 'uuid';

const router = express.Router();

/**
 * GET /agents - 获取智能体列表
 */
router.get('/', async (req, res) => {
  try {
    const { user_id } = req.query;
    const db = getDatabaseSync();

    let query = 'SELECT * FROM agents';
    const params = [];

    if (user_id) {
      query += ' WHERE user_id = ?';
      params.push(user_id);
    }

    query += ' ORDER BY created_at DESC';

    const agents = db.fetchallSync(query, params);
    const out = [];
    for (const a of agents) {
      let mcpIds = [];
      let callableIds = [];
      try {
        if (a.mcp_config_ids) {
          const parsed = typeof a.mcp_config_ids === 'string' ? JSON.parse(a.mcp_config_ids) : a.mcp_config_ids;
          if (Array.isArray(parsed)) mcpIds = parsed;
        }
      } catch (e) {}
      try {
        if (a.callable_agent_ids) {
          const parsed = typeof a.callable_agent_ids === 'string' ? JSON.parse(a.callable_agent_ids) : a.callable_agent_ids;
          if (Array.isArray(parsed)) callableIds = parsed;
        }
      } catch (e) {}
      let appIds = [];
      try {
        const rows = db.fetchallSync(
          'SELECT application_id FROM agent_applications WHERE agent_id = ?',
          [a.id]
        );
        appIds = rows.map(r => r.application_id);
      } catch (e) {
        appIds = [];
      }
      out.push({ ...a, app_ids: appIds, mcp_config_ids: mcpIds, callable_agent_ids: callableIds });
    }
    logger.info(`获取到 ${out.length} 个智能体`);
    res.json(out);
  } catch (error) {
    logger.error('获取智能体列表失败:', error);
    res.status(500).json({ error: '获取智能体列表失败' });
  }
});

/**
 * POST /agents - 创建智能体
 */
router.post('/', async (req, res) => {
  try {
    const { name, ai_model_config_id, system_context_id, description, user_id, enabled, app_ids, mcp_config_ids, callable_agent_ids } = req.body;

    if (!name || !ai_model_config_id) {
      return res.status(400).json({ error: 'name 和 ai_model_config_id 为必填项' });
    }

    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    const mcpIdsStr = Array.isArray(mcp_config_ids) ? JSON.stringify(mcp_config_ids) : (mcp_config_ids || null);
    const callableIdsStr = Array.isArray(callable_agent_ids) ? JSON.stringify(callable_agent_ids) : (callable_agent_ids || null);

    db.executeSync(
      `INSERT INTO agents (id, name, ai_model_config_id, system_context_id, description, user_id, mcp_config_ids, callable_agent_ids, enabled, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, name, ai_model_config_id, system_context_id || null, description || null, user_id || null, mcpIdsStr, callableIdsStr, enabled !== false ? 1 : 0, now, now]
    );

    if (Array.isArray(app_ids)) {
      for (const appId of app_ids) {
        try {
          db.executeSync(
            'INSERT INTO agent_applications (id, agent_id, application_id, created_at) VALUES (?, ?, ?, ?)',
            [uuidv4(), id, appId, now]
          );
        } catch (e) {}
      }
    }

    const newAgent = db.fetchoneSync('SELECT * FROM agents WHERE id = ?', [id]);
    let parsedMcp = [];
    let parsedCallable = [];
    try {
      if (newAgent.mcp_config_ids) {
        const p = typeof newAgent.mcp_config_ids === 'string' ? JSON.parse(newAgent.mcp_config_ids) : newAgent.mcp_config_ids;
        if (Array.isArray(p)) parsedMcp = p;
      }
    } catch (e) {}
    try {
      if (newAgent.callable_agent_ids) {
        const p = typeof newAgent.callable_agent_ids === 'string' ? JSON.parse(newAgent.callable_agent_ids) : newAgent.callable_agent_ids;
        if (Array.isArray(p)) parsedCallable = p;
      }
    } catch (e) {}
    let appIds = [];
    try {
      const rows = db.fetchallSync(
        'SELECT application_id FROM agent_applications WHERE agent_id = ?',
        [id]
      );
      appIds = rows.map(r => r.application_id);
    } catch (e) {
      appIds = [];
    }
    logger.info(`创建智能体成功: ${id}`);
    res.status(201).json({ ...newAgent, app_ids: appIds, mcp_config_ids: parsedMcp, callable_agent_ids: parsedCallable });
  } catch (error) {
    logger.error('创建智能体失败:', error);
    res.status(500).json({ error: '创建智能体失败' });
  }
});

/**
 * GET /agents/:agent_id - 获取特定智能体
 */
router.get('/:agent_id', async (req, res) => {
  try {
    const { agent_id } = req.params;
    const db = getDatabaseSync();

  const agent = db.fetchoneSync('SELECT * FROM agents WHERE id = ?', [agent_id]);

  if (!agent) {
    return res.status(404).json({ error: 'Agent 不存在' });
  }

  let mcpIds = [];
  let callableIds = [];
  try {
    if (agent.mcp_config_ids) {
      const parsed = typeof agent.mcp_config_ids === 'string' ? JSON.parse(agent.mcp_config_ids) : agent.mcp_config_ids;
      if (Array.isArray(parsed)) mcpIds = parsed;
    }
  } catch (e) {}
  try {
    if (agent.callable_agent_ids) {
      const parsed = typeof agent.callable_agent_ids === 'string' ? JSON.parse(agent.callable_agent_ids) : agent.callable_agent_ids;
      if (Array.isArray(parsed)) callableIds = parsed;
    }
  } catch (e) {}

  let appIds = [];
  try {
    const rows = db.fetchallSync(
      'SELECT application_id FROM agent_applications WHERE agent_id = ?',
      [agent_id]
    );
    appIds = rows.map(r => r.application_id);
  } catch (e) {
    appIds = [];
  }

  res.json({ ...agent, app_ids: appIds, mcp_config_ids: mcpIds, callable_agent_ids: callableIds });
  } catch (error) {
    logger.error('获取智能体失败:', error);
    res.status(500).json({ error: '获取智能体失败' });
  }
});

/**
 * PUT /agents/:agent_id - 更新智能体
 */
router.put('/:agent_id', async (req, res) => {
  try {
    const { agent_id } = req.params;
    const { name, ai_model_config_id, system_context_id, description, enabled, app_ids, mcp_config_ids, callable_agent_ids } = req.body;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM agents WHERE id = ?', [agent_id]);
    if (!existing) {
      return res.status(404).json({ error: 'Agent 不存在' });
    }

    const updates = [];
    const params = [];

    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (ai_model_config_id !== undefined) {
      updates.push('ai_model_config_id = ?');
      params.push(ai_model_config_id);
    }
    if (system_context_id !== undefined) {
      updates.push('system_context_id = ?');
      params.push(system_context_id);
    }
    if (description !== undefined) {
      updates.push('description = ?');
      params.push(description);
    }
    if (enabled !== undefined) {
      updates.push('enabled = ?');
      params.push(enabled ? 1 : 0);
    }
    if (mcp_config_ids !== undefined) {
      updates.push('mcp_config_ids = ?');
      params.push(Array.isArray(mcp_config_ids) ? JSON.stringify(mcp_config_ids) : mcp_config_ids);
    }
    if (callable_agent_ids !== undefined) {
      updates.push('callable_agent_ids = ?');
      params.push(Array.isArray(callable_agent_ids) ? JSON.stringify(callable_agent_ids) : callable_agent_ids);
    }

    if (updates.length > 0) {
      updates.push('updated_at = ?');
      params.push(new Date().toISOString());
      params.push(agent_id);

      db.executeSync(
        `UPDATE agents SET ${updates.join(', ')} WHERE id = ?`,
        params
      );
    }

    if (app_ids !== undefined) {
      try {
        db.executeSync('DELETE FROM agent_applications WHERE agent_id = ?', [agent_id]);
        const now = new Date().toISOString();
        if (Array.isArray(app_ids)) {
          for (const appId of app_ids) {
            try {
              db.executeSync(
                'INSERT INTO agent_applications (id, agent_id, application_id, created_at) VALUES (?, ?, ?, ?)',
                [uuidv4(), agent_id, appId, now]
              );
            } catch (e) {}
          }
        }
      } catch (e) {}
    }

    const updated = db.fetchoneSync('SELECT * FROM agents WHERE id = ?', [agent_id]);
    let parsedMcp = [];
    let parsedCallable = [];
    try {
      if (updated.mcp_config_ids) {
        const p = typeof updated.mcp_config_ids === 'string' ? JSON.parse(updated.mcp_config_ids) : updated.mcp_config_ids;
        if (Array.isArray(p)) parsedMcp = p;
      }
    } catch (e) {}
    try {
      if (updated.callable_agent_ids) {
        const p = typeof updated.callable_agent_ids === 'string' ? JSON.parse(updated.callable_agent_ids) : updated.callable_agent_ids;
        if (Array.isArray(p)) parsedCallable = p;
      }
    } catch (e) {}
    let appIds = [];
    try {
      const rows = db.fetchallSync(
        'SELECT application_id FROM agent_applications WHERE agent_id = ?',
        [agent_id]
      );
      appIds = rows.map(r => r.application_id);
    } catch (e) {
      appIds = [];
    }
    logger.info(`更新智能体成功: ${agent_id}`);
    res.json({ ...updated, app_ids: appIds, mcp_config_ids: parsedMcp, callable_agent_ids: parsedCallable });
  } catch (error) {
    logger.error('更新智能体失败:', error);
    res.status(500).json({ error: '更新智能体失败' });
  }
});

/**
 * DELETE /agents/:agent_id - 删除智能体
 */
router.delete('/:agent_id', async (req, res) => {
  try {
    const { agent_id } = req.params;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM agents WHERE id = ?', [agent_id]);
    if (!existing) {
      return res.status(404).json({ error: 'Agent 不存在' });
    }

    db.executeSync('DELETE FROM agents WHERE id = ?', [agent_id]);
    logger.info(`删除智能体成功: ${agent_id}`);
    res.json({ ok: true });
  } catch (error) {
    logger.error('删除智能体失败:', error);
    res.status(500).json({ error: '删除智能体失败' });
  }
});

/**
 * POST /agents/chat/stream - 基于智能体ID的流式聊天
 */
router.post('/chat/stream', async (req, res) => {
  try {
    const { session_id, content, agent_id, user_id } = req.body;

    if (!session_id || !content || !agent_id) {
      return res.status(400).json({ error: 'session_id, content 和 agent_id 为必填项' });
    }

    // 设置 SSE 响应头
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    try {
      const stream = buildSseStreamFromAgentId(session_id, content, agent_id, user_id);

      for await (const chunk of stream) {
        res.write(chunk);
      }

      res.write('data: [DONE]\n\n');
    } catch (error) {
      logger.error('智能体聊天处理失败:', error);
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
    logger.error('智能体流式聊天失败:', error);
    if (!res.headersSent) {
      res.status(500).json({ error: error.message });
    } else {
      res.end();
    }
  }
});

export default router;
