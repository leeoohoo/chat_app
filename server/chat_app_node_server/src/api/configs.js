/**
 * 配置管理 API
 * 复刻自 Python: app/api/configs.py
 * 包含：MCP配置、AI模型配置、系统上下文
 */

import express from 'express';
import { getDatabaseSync } from '../models/database-factory.js';
import { logger } from '../utils/logger.js';
import { v4 as uuidv4 } from 'uuid';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const router = express.Router();

// ==================== MCP 配置 ====================

/**
 * GET /mcp-configs - 获取MCP配置列表
 */
router.get('/mcp-configs', async (req, res) => {
  try {
    const { user_id } = req.query;
    const db = getDatabaseSync();

    let query = 'SELECT * FROM mcp_configs';
    const params = [];

    if (user_id) {
      query += ' WHERE user_id = ?';
      params.push(user_id);
    }

    query += ' ORDER BY created_at DESC';

    const configs = db.fetchallSync(query, params);
    const out = [];
    for (const cfg of configs) {
      let appIds = [];
      try {
        const rows = db.fetchallSync(
          'SELECT application_id FROM mcp_config_applications WHERE mcp_config_id = ?',
          [cfg.id]
        );
        appIds = rows.map(r => r.application_id);
      } catch (e) {
        appIds = [];
      }
      out.push({ ...cfg, app_ids: appIds });
    }
    logger.info(`获取到 ${out.length} 个MCP配置`);
    res.json(out);
  } catch (error) {
    logger.error('获取MCP配置失败:', error);
    res.status(500).json({ error: '获取MCP配置失败' });
  }
});

/**
 * POST /mcp-configs - 创建MCP配置
 */
router.post('/mcp-configs', async (req, res) => {
  try {
    const { name, command, type, args, env, cwd, user_id, enabled, app_ids } = req.body;
    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    const argsStr = args ? JSON.stringify(args) : null;
    const envStr = env ? JSON.stringify(env) : null;

    db.executeSync(
      `INSERT INTO mcp_configs (id, name, command, type, args, env, cwd, user_id, enabled, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, name, command, type || 'stdio', argsStr, envStr, cwd || null, user_id || null, enabled !== false ? 1 : 0, now, now]
    );

    if (Array.isArray(app_ids)) {
      for (const appId of app_ids) {
        try {
          db.executeSync(
            'INSERT INTO mcp_config_applications (id, mcp_config_id, application_id, created_at) VALUES (?, ?, ?, ?)',
            [uuidv4(), id, appId, now]
          );
        } catch (e) {}
      }
    }

    const newConfig = db.fetchoneSync('SELECT * FROM mcp_configs WHERE id = ?', [id]);
    let appIds = [];
    try {
      const rows = db.fetchallSync(
        'SELECT application_id FROM mcp_config_applications WHERE mcp_config_id = ?',
        [id]
      );
      appIds = rows.map(r => r.application_id);
    } catch (e) {
      appIds = [];
    }
    logger.info(`创建MCP配置成功: ${id}`);
    res.status(201).json({ ...newConfig, app_ids: appIds });
  } catch (error) {
    logger.error('创建MCP配置失败:', error);
    res.status(500).json({ error: '创建MCP配置失败' });
  }
});

/**
 * PUT /mcp-configs/:config_id - 更新MCP配置
 */
router.put('/mcp-configs/:config_id', async (req, res) => {
  try {
    const { config_id } = req.params;
    const { name, command, type, args, env, cwd, enabled, app_ids } = req.body;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM mcp_configs WHERE id = ?', [config_id]);
    if (!existing) {
      return res.status(404).json({ error: 'MCP配置不存在' });
    }

    const updates = [];
    const params = [];

    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (command !== undefined) {
      updates.push('command = ?');
      params.push(command);
    }
    if (type !== undefined) {
      updates.push('type = ?');
      params.push(type);
    }
    if (args !== undefined) {
      updates.push('args = ?');
      params.push(JSON.stringify(args));
    }
    if (env !== undefined) {
      updates.push('env = ?');
      params.push(JSON.stringify(env));
    }
    if (cwd !== undefined) {
      updates.push('cwd = ?');
      params.push(cwd);
    }
    if (enabled !== undefined) {
      updates.push('enabled = ?');
      params.push(enabled ? 1 : 0);
    }

    if (updates.length > 0) {
      updates.push('updated_at = ?');
      params.push(new Date().toISOString());
      params.push(config_id);

      db.executeSync(
        `UPDATE mcp_configs SET ${updates.join(', ')} WHERE id = ?`,
        params
      );
    }

    if (app_ids !== undefined) {
      try {
        db.executeSync('DELETE FROM mcp_config_applications WHERE mcp_config_id = ?', [config_id]);
        const now = new Date().toISOString();
        if (Array.isArray(app_ids)) {
          for (const appId of app_ids) {
            try {
              db.executeSync(
                'INSERT INTO mcp_config_applications (id, mcp_config_id, application_id, created_at) VALUES (?, ?, ?, ?)',
                [uuidv4(), config_id, appId, now]
              );
            } catch (e) {}
          }
        }
      } catch (e) {}
    }

    const updated = db.fetchoneSync('SELECT * FROM mcp_configs WHERE id = ?', [config_id]);
    let appIds = [];
    try {
      const rows = db.fetchallSync(
        'SELECT application_id FROM mcp_config_applications WHERE mcp_config_id = ?',
        [config_id]
      );
      appIds = rows.map(r => r.application_id);
    } catch (e) {
      appIds = [];
    }
    logger.info(`成功更新MCP配置: ${config_id}`);
    res.json({ ...updated, app_ids: appIds });
  } catch (error) {
    logger.error('更新MCP配置失败:', error);
    res.status(500).json({ error: '更新MCP配置失败' });
  }
});

/**
 * DELETE /mcp-configs/:config_id - 删除MCP配置
 */
router.delete('/mcp-configs/:config_id', async (req, res) => {
  try {
    const { config_id } = req.params;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM mcp_configs WHERE id = ?', [config_id]);
    if (!existing) {
      return res.status(404).json({ error: 'MCP配置不存在' });
    }

    db.executeSync('DELETE FROM mcp_configs WHERE id = ?', [config_id]);
    logger.info(`成功删除MCP配置: ${config_id}`);
    res.json({ message: 'MCP配置删除成功', id: config_id });
  } catch (error) {
    logger.error('删除MCP配置失败:', error);
    res.status(500).json({ error: '删除MCP配置失败' });
  }
});

/**
 * GET /mcp-configs/:config_id/resource/config - 读取MCP配置资源
 */
router.get('/mcp-configs/:config_id/resource/config', async (req, res) => {
  try {
    const { config_id } = req.params;
    const db = getDatabaseSync();

    const cfg = db.fetchoneSync('SELECT * FROM mcp_configs WHERE id = ?', [config_id]);
    if (!cfg) {
      return res.status(404).json({ error: 'MCP配置不存在' });
    }

    if (cfg.type !== 'stdio') {
      return res.status(400).json({ error: '仅支持stdio类型的MCP配置读取资源' });
    }

    const command = cfg.command;
    if (!command) {
      return res.status(400).json({ error: 'MCP配置缺少可执行命令' });
    }

    // 解析 args 和 env
    let args = [];
    let env = {};

    if (cfg.args) {
      try {
        args = typeof cfg.args === 'string' ? JSON.parse(cfg.args) : cfg.args;
      } catch (e) {
        args = [];
      }
    }

    if (cfg.env) {
      try {
        env = typeof cfg.env === 'string' ? JSON.parse(cfg.env) : cfg.env;
      } catch (e) {
        env = {};
      }
    }

    const cwd = cfg.cwd || process.cwd();
    const alias = cfg.name;

    // 使用 MCP SDK 读取资源
    const transport = new StdioClientTransport({
      command,
      args,
      env: { ...process.env, ...env },
      cwd
    });

    const { Client } = await import('@modelcontextprotocol/sdk/client/index.js');
    const client = new Client({ name: 'resource-reader', version: '1.0.0' }, {});

    await client.connect(transport);
    const result = await client.readResource({ uri: 'config://server' });
    await client.close();

    // 提取文本内容
    let text = '';
    if (result.contents && result.contents.length > 0) {
      const content = result.contents[0];
      text = content.text || JSON.stringify(content);
    }

    // 尝试解析 JSON
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = { raw: text };
    }

    res.json({ success: true, config: data, alias });
  } catch (error) {
    logger.error('读取MCP配置资源失败:', error);
    res.status(500).json({ error: `读取MCP配置资源失败: ${error.message}` });
  }
});

/**
 * POST /mcp-configs/resource/config - 通过命令读取MCP配置资源
 */
router.post('/mcp-configs/resource/config', async (req, res) => {
  try {
    const { type, command, args, env, cwd, alias } = req.body;

    if (type !== 'stdio') {
      return res.status(400).json({ error: '仅支持stdio类型的MCP配置读取资源' });
    }

    if (!command) {
      return res.status(400).json({ error: '缺少可执行命令' });
    }

    // 解析参数
    let parsedArgs = [];
    if (typeof args === 'string') {
      try {
        parsedArgs = JSON.parse(args);
      } catch (e) {
        parsedArgs = [];
      }
    } else if (Array.isArray(args)) {
      parsedArgs = args;
    }

    let parsedEnv = {};
    if (typeof env === 'string') {
      try {
        parsedEnv = JSON.parse(env);
      } catch (e) {
        parsedEnv = {};
      }
    } else if (env && typeof env === 'object') {
      parsedEnv = env;
    }

    const workDir = cwd || process.cwd();
    const serverAlias = alias || 'mcp_server';

    // 使用 MCP SDK 读取资源
    const transport = new StdioClientTransport({
      command,
      args: parsedArgs,
      env: { ...process.env, ...parsedEnv },
      cwd: workDir
    });

    const { Client } = await import('@modelcontextprotocol/sdk/client/index.js');
    const client = new Client({ name: 'resource-reader', version: '1.0.0' }, {});

    await client.connect(transport);
    const result = await client.readResource({ uri: 'config://server' });
    await client.close();

    // 提取文本内容
    let text = '';
    if (result.contents && result.contents.length > 0) {
      const content = result.contents[0];
      text = content.text || JSON.stringify(content);
    }

    // 尝试解析 JSON
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = { raw: text };
    }

    res.json({ success: true, config: data, alias: serverAlias });
  } catch (error) {
    logger.error('读取MCP配置资源(按命令)失败:', error);
    res.status(500).json({ error: `读取MCP配置资源失败: ${error.message}` });
  }
});

// ==================== MCP 配置档案 ====================

/**
 * GET /mcp-configs/:config_id/profiles - 获取配置档案列表
 */
router.get('/mcp-configs/:config_id/profiles', async (req, res) => {
  try {
    const { config_id } = req.params;
    const db = getDatabaseSync();

    const profiles = db.fetchallSync(
      'SELECT * FROM mcp_config_profiles WHERE mcp_config_id = ? ORDER BY created_at DESC',
      [config_id]
    );

    res.json({ items: profiles });
  } catch (error) {
    logger.error('列出配置档案失败:', error);
    res.status(500).json({ error: '列出配置档案失败' });
  }
});

/**
 * POST /mcp-configs/:config_id/profiles - 创建配置档案
 */
router.post('/mcp-configs/:config_id/profiles', async (req, res) => {
  try {
    const { config_id } = req.params;
    const { name, args, env, cwd, enabled } = req.body;
    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    const argsStr = args ? JSON.stringify(args) : null;
    const envStr = env ? JSON.stringify(env) : null;

    db.executeSync(
      `INSERT INTO mcp_config_profiles (id, mcp_config_id, name, args, env, cwd, enabled, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, config_id, name || 'default', argsStr, envStr, cwd || null, enabled ? 1 : 0, now, now]
    );

    const newProfile = db.fetchoneSync('SELECT * FROM mcp_config_profiles WHERE id = ?', [id]);
    res.status(201).json(newProfile);
  } catch (error) {
    logger.error('创建配置档案失败:', error);
    res.status(500).json({ error: '创建配置档案失败' });
  }
});

/**
 * PUT /mcp-configs/:config_id/profiles/:profile_id - 更新配置档案
 */
router.put('/mcp-configs/:config_id/profiles/:profile_id', async (req, res) => {
  try {
    const { profile_id } = req.params;
    const { name, args, env, cwd, enabled } = req.body;
    const db = getDatabaseSync();

    const updates = [];
    const params = [];

    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (args !== undefined) {
      updates.push('args = ?');
      params.push(JSON.stringify(args));
    }
    if (env !== undefined) {
      updates.push('env = ?');
      params.push(JSON.stringify(env));
    }
    if (cwd !== undefined) {
      updates.push('cwd = ?');
      params.push(cwd);
    }
    if (enabled !== undefined) {
      updates.push('enabled = ?');
      params.push(enabled ? 1 : 0);
    }

    if (updates.length > 0) {
      updates.push('updated_at = ?');
      params.push(new Date().toISOString());
      params.push(profile_id);

      db.executeSync(
        `UPDATE mcp_config_profiles SET ${updates.join(', ')} WHERE id = ?`,
        params
      );
    }

    const updated = db.fetchoneSync('SELECT * FROM mcp_config_profiles WHERE id = ?', [profile_id]);
    res.json(updated);
  } catch (error) {
    logger.error('更新配置档案失败:', error);
    res.status(500).json({ error: '更新配置档案失败' });
  }
});

/**
 * DELETE /mcp-configs/:config_id/profiles/:profile_id - 删除配置档案
 */
router.delete('/mcp-configs/:config_id/profiles/:profile_id', async (req, res) => {
  try {
    const { config_id, profile_id } = req.params;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM mcp_config_profiles WHERE id = ?', [profile_id]);
    if (!existing) {
      return res.status(404).json({ error: '配置档案不存在' });
    }

    if (existing.mcp_config_id !== config_id) {
      return res.status(400).json({ error: '配置ID不匹配' });
    }

    db.executeSync('DELETE FROM mcp_config_profiles WHERE id = ?', [profile_id]);
    logger.info(`成功删除配置档案: ${profile_id}`);
    res.json({ message: '配置档案删除成功', id: profile_id });
  } catch (error) {
    logger.error('删除配置档案失败:', error);
    res.status(500).json({ error: '删除配置档案失败' });
  }
});

/**
 * POST /mcp-configs/:config_id/profiles/:profile_id/activate - 激活配置档案
 */
router.post('/mcp-configs/:config_id/profiles/:profile_id/activate', async (req, res) => {
  try {
    const { config_id, profile_id } = req.params;
    const db = getDatabaseSync();

    // 先禁用该配置的所有档案
    db.executeSync(
      'UPDATE mcp_config_profiles SET enabled = 0 WHERE mcp_config_id = ?',
      [config_id]
    );

    // 激活指定档案
    db.executeSync(
      'UPDATE mcp_config_profiles SET enabled = 1, updated_at = ? WHERE id = ?',
      [new Date().toISOString(), profile_id]
    );

    const activated = db.fetchoneSync('SELECT * FROM mcp_config_profiles WHERE id = ?', [profile_id]);
    res.json(activated);
  } catch (error) {
    logger.error('激活配置档案失败:', error);
    res.status(500).json({ error: '激活配置档案失败' });
  }
});

// ==================== AI 模型配置 ====================

/**
 * GET /ai-model-configs - 获取AI模型配置列表
 */
router.get('/ai-model-configs', async (req, res) => {
  try {
    const { user_id } = req.query;
    const db = getDatabaseSync();

    let query = 'SELECT * FROM ai_model_configs';
    const params = [];

    if (user_id) {
      query += ' WHERE user_id = ?';
      params.push(user_id);
    }

    query += ' ORDER BY created_at DESC';

    const configs = db.fetchallSync(query, params);
    logger.info(`获取到 ${configs.length} 个AI模型配置`);
    res.json(configs);
  } catch (error) {
    logger.error('获取AI模型配置失败:', error);
    res.status(500).json({ error: '获取AI模型配置失败' });
  }
});

/**
 * POST /ai-model-configs - 创建AI模型配置
 */
router.post('/ai-model-configs', async (req, res) => {
  try {
    const { name, provider, model, api_key, base_url, user_id, enabled } = req.body;
    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    db.executeSync(
      `INSERT INTO ai_model_configs (id, name, provider, model, api_key, base_url, user_id, enabled, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, name, provider || 'openai', model, api_key || null, base_url || null, user_id || null, enabled !== false ? 1 : 0, now, now]
    );

    const newConfig = db.fetchoneSync('SELECT * FROM ai_model_configs WHERE id = ?', [id]);
    logger.info(`创建AI模型配置成功: ${id}`);
    res.status(201).json(newConfig);
  } catch (error) {
    logger.error('创建AI模型配置失败:', error);
    res.status(500).json({ error: '创建AI模型配置失败' });
  }
});

/**
 * PUT /ai-model-configs/:config_id - 更新AI模型配置
 */
router.put('/ai-model-configs/:config_id', async (req, res) => {
  try {
    const { config_id } = req.params;
    const { name, provider, model, api_key, base_url, enabled } = req.body;
    const db = getDatabaseSync();

    const updates = [];
    const params = [];

    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (provider !== undefined) {
      updates.push('provider = ?');
      params.push(provider);
    }
    if (model !== undefined) {
      updates.push('model = ?');
      params.push(model);
    }
    if (api_key !== undefined) {
      updates.push('api_key = ?');
      params.push(api_key);
    }
    if (base_url !== undefined) {
      updates.push('base_url = ?');
      params.push(base_url);
    }
    if (enabled !== undefined) {
      updates.push('enabled = ?');
      params.push(enabled ? 1 : 0);
    }

    if (updates.length > 0) {
      updates.push('updated_at = ?');
      params.push(new Date().toISOString());
      params.push(config_id);

      db.executeSync(
        `UPDATE ai_model_configs SET ${updates.join(', ')} WHERE id = ?`,
        params
      );
    }

    const updated = db.fetchoneSync('SELECT * FROM ai_model_configs WHERE id = ?', [config_id]);
    if (!updated) {
      return res.status(404).json({ error: 'AI模型配置不存在' });
    }

    logger.info(`AI模型配置更新成功: ${config_id}`);
    res.json(updated);
  } catch (error) {
    logger.error('更新AI模型配置失败:', error);
    res.status(500).json({ error: '更新AI模型配置失败' });
  }
});

/**
 * DELETE /ai-model-configs/:config_id - 删除AI模型配置
 */
router.delete('/ai-model-configs/:config_id', async (req, res) => {
  try {
    const { config_id } = req.params;
    const db = getDatabaseSync();

    const existing = db.fetchoneSync('SELECT * FROM ai_model_configs WHERE id = ?', [config_id]);
    if (!existing) {
      return res.status(404).json({ error: 'AI模型配置不存在' });
    }

    db.executeSync('DELETE FROM ai_model_configs WHERE id = ?', [config_id]);
    logger.info(`AI模型配置删除成功: ${config_id}`);
    res.json({ message: 'AI模型配置删除成功' });
  } catch (error) {
    logger.error('删除AI模型配置失败:', error);
    res.status(500).json({ error: '删除AI模型配置失败' });
  }
});

// ==================== 系统上下文 ====================

/**
 * GET /system-contexts - 获取系统上下文列表
 */
router.get('/system-contexts', async (req, res) => {
  try {
    const { user_id } = req.query;

    if (!user_id) {
      return res.status(400).json({ error: 'user_id 为必填参数' });
    }

    const db = getDatabaseSync();
    const contexts = db.fetchallSync(
      'SELECT * FROM system_contexts WHERE user_id = ? ORDER BY created_at DESC',
      [user_id]
    );

    const out = [];
    for (const ctx of contexts) {
      let appIds = [];
      try {
        const rows = db.fetchallSync(
          'SELECT application_id FROM system_context_applications WHERE system_context_id = ?',
          [ctx.id]
        );
        appIds = rows.map(r => r.application_id);
      } catch (e) {
        appIds = [];
      }
      out.push({ ...ctx, app_ids: appIds });
    }

    logger.info(`获取到 ${out.length} 个系统上下文`);
    res.json(out);
  } catch (error) {
    logger.error('获取系统上下文失败:', error);
    res.status(500).json({ error: '获取系统上下文失败' });
  }
});

/**
 * GET /system-context/active - 获取活跃系统上下文
 */
router.get('/system-context/active', async (req, res) => {
  try {
    const { user_id } = req.query;

    if (!user_id) {
      return res.status(400).json({ error: 'user_id 为必填参数' });
    }

    const db = getDatabaseSync();
    const context = db.fetchoneSync(
      'SELECT * FROM system_contexts WHERE user_id = ? AND is_active = 1',
      [user_id]
    );

    let appIds = [];
    if (context) {
      try {
        const rows = db.fetchallSync(
          'SELECT application_id FROM system_context_applications WHERE system_context_id = ?',
          [context.id]
        );
        appIds = rows.map(r => r.application_id);
      } catch (e) {
        appIds = [];
      }
    }

    res.json({
      content: context ? context.content : '',
      context: context ? { ...context, app_ids: appIds } : null
    });
  } catch (error) {
    logger.error('获取活跃系统上下文失败:', error);
    res.status(500).json({ error: '获取活跃系统上下文失败' });
  }
});

/**
 * POST /system-contexts - 创建系统上下文
 */
router.post('/system-contexts', async (req, res) => {
  try {
    const { name, content, user_id, is_active, app_ids } = req.body;
    const db = getDatabaseSync();
    const id = uuidv4();
    const now = new Date().toISOString();

    db.executeSync(
      `INSERT INTO system_contexts (id, name, content, user_id, is_active, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [id, name, content, user_id, is_active ? 1 : 0, now, now]
    );

    if (Array.isArray(app_ids)) {
      for (const appId of app_ids) {
        try {
          db.executeSync(
            'INSERT INTO system_context_applications (id, system_context_id, application_id, created_at) VALUES (?, ?, ?, ?)',
            [uuidv4(), id, appId, now]
          );
        } catch (e) {}
      }
    }

    const newContext = db.fetchoneSync('SELECT * FROM system_contexts WHERE id = ?', [id]);
    let appIds = [];
    try {
      const rows = db.fetchallSync(
        'SELECT application_id FROM system_context_applications WHERE system_context_id = ?',
        [id]
      );
      appIds = rows.map(r => r.application_id);
    } catch (e) {
      appIds = [];
    }
    logger.info(`创建系统上下文成功: ${id}`);
    res.status(201).json({ ...newContext, app_ids: appIds });
  } catch (error) {
    logger.error('创建系统上下文失败:', error);
    res.status(500).json({ error: '创建系统上下文失败' });
  }
});

/**
 * PUT /system-contexts/:context_id - 更新系统上下文
 */
router.put('/system-contexts/:context_id', async (req, res) => {
  try {
    const { context_id } = req.params;
    const { name, content, is_active, app_ids } = req.body;
    const db = getDatabaseSync();

    const updates = [];
    const params = [];

    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (content !== undefined) {
      updates.push('content = ?');
      params.push(content);
    }
    if (is_active !== undefined) {
      updates.push('is_active = ?');
      params.push(is_active ? 1 : 0);
    }

    if (updates.length > 0) {
      updates.push('updated_at = ?');
      params.push(new Date().toISOString());
      params.push(context_id);

      db.executeSync(
        `UPDATE system_contexts SET ${updates.join(', ')} WHERE id = ?`,
        params
      );
    }

    if (app_ids !== undefined) {
      try {
        db.executeSync('DELETE FROM system_context_applications WHERE system_context_id = ?', [context_id]);
        const now = new Date().toISOString();
        if (Array.isArray(app_ids)) {
          for (const appId of app_ids) {
            try {
              db.executeSync(
                'INSERT INTO system_context_applications (id, system_context_id, application_id, created_at) VALUES (?, ?, ?, ?)',
                [uuidv4(), context_id, appId, now]
              );
            } catch (e) {}
          }
        }
      } catch (e) {}
    }

    const updated = db.fetchoneSync('SELECT * FROM system_contexts WHERE id = ?', [context_id]);
    let appIds = [];
    try {
      const rows = db.fetchallSync(
        'SELECT application_id FROM system_context_applications WHERE system_context_id = ?',
        [context_id]
      );
      appIds = rows.map(r => r.application_id);
    } catch (e) {
      appIds = [];
    }
    logger.info(`更新系统上下文成功: ${context_id}`);
    res.json({ ...updated, app_ids: appIds });
  } catch (error) {
    logger.error('更新系统上下文失败:', error);
    res.status(500).json({ error: '更新系统上下文失败' });
  }
});

/**
 * DELETE /system-contexts/:context_id - 删除系统上下文
 */
router.delete('/system-contexts/:context_id', async (req, res) => {
  try {
    const { context_id } = req.params;
    const db = getDatabaseSync();

    db.executeSync('DELETE FROM system_contexts WHERE id = ?', [context_id]);
    logger.info(`删除系统上下文: ${context_id}`);
    res.json({ message: '系统上下文删除成功' });
  } catch (error) {
    logger.error('删除系统上下文失败:', error);
    res.status(500).json({ error: '删除系统上下文失败' });
  }
});

/**
 * POST /system-contexts/:context_id/activate - 激活系统上下文
 */
router.post('/system-contexts/:context_id/activate', async (req, res) => {
  try {
    const { context_id } = req.params;
    const { user_id } = req.body;
    const db = getDatabaseSync();

    // 先禁用该用户的所有系统上下文
    db.executeSync(
      'UPDATE system_contexts SET is_active = 0 WHERE user_id = ?',
      [user_id]
    );

    // 激活指定上下文
    db.executeSync(
      'UPDATE system_contexts SET is_active = 1, updated_at = ? WHERE id = ?',
      [new Date().toISOString(), context_id]
    );

    const activated = db.fetchoneSync('SELECT * FROM system_contexts WHERE id = ?', [context_id]);
    logger.info(`激活系统上下文成功: ${context_id}`);
    res.json(activated);
  } catch (error) {
    logger.error('激活系统上下文失败:', error);
    res.status(500).json({ error: '激活系统上下文失败' });
  }
});

export default router;
