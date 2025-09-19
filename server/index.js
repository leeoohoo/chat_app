import express from 'express';
import cors from 'cors';
import path from 'path';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { handleChatProxy, handleHealthCheck } from './proxy.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// 中间件
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../dist')));

// 数据库初始化
let db;

async function initDatabase() {
  try {
    db = await open({
      filename: path.join(__dirname, '../data/chat.db'),
      driver: sqlite3.Database
    });
    
    // 创建表
    await db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        user_id TEXT,
        project_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        summary TEXT, -- AI generated content summary
        tool_calls TEXT, -- JSON array of tool calls
        tool_call_id TEXT, -- For tool responses
        reasoning TEXT, -- AI reasoning process
        metadata TEXT, -- Additional metadata
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
      );
      
      CREATE TABLE IF NOT EXISTS mcp_configs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        command TEXT NOT NULL,
        args TEXT,
        env TEXT,
        user_id TEXT,
        enabled BOOLEAN DEFAULT true,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS ai_model_configs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        api_key TEXT,
        base_url TEXT,
        user_id TEXT,
        enabled BOOLEAN DEFAULT true,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS session_mcp_servers (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        mcp_config_id TEXT NOT NULL,
        enabled BOOLEAN DEFAULT true,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
        FOREIGN KEY (mcp_config_id) REFERENCES mcp_configs (id) ON DELETE CASCADE,
        UNIQUE(session_id, mcp_config_id)
      );
      
      CREATE TABLE IF NOT EXISTS system_contexts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        content TEXT,
        user_id TEXT,
        is_active BOOLEAN DEFAULT false,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
    
    // 检查并添加新字段（如果不存在）
    try {
      // 为sessions表添加user_id字段
      const sessionsTableInfo = await db.all("PRAGMA table_info(sessions)");
      const hasUserId = sessionsTableInfo.some(column => column.name === 'user_id');
      const hasProjectId = sessionsTableInfo.some(column => column.name === 'project_id');
      
      if (!hasUserId) {
        await db.exec("ALTER TABLE sessions ADD COLUMN user_id TEXT");
        console.log('已为sessions表添加user_id字段');
      }
      
      if (!hasProjectId) {
        await db.exec("ALTER TABLE sessions ADD COLUMN project_id TEXT");
        console.log('已为sessions表添加project_id字段');
      }
      
      // 为mcp_configs表添加user_id字段
      const mcpTableInfo = await db.all("PRAGMA table_info(mcp_configs)");
      const mcpHasUserId = mcpTableInfo.some(column => column.name === 'user_id');
      
      if (!mcpHasUserId) {
        await db.exec("ALTER TABLE mcp_configs ADD COLUMN user_id TEXT");
        console.log('已为mcp_configs表添加user_id字段');
      }
      
      // 为ai_model_configs表添加user_id字段
      const aiModelTableInfo = await db.all("PRAGMA table_info(ai_model_configs)");
      const aiModelHasUserId = aiModelTableInfo.some(column => column.name === 'user_id');
      
      if (!aiModelHasUserId) {
        await db.exec("ALTER TABLE ai_model_configs ADD COLUMN user_id TEXT");
        console.log('已为ai_model_configs表添加user_id字段');
      }
    } catch (error) {
      // 如果字段已存在，忽略错误
      console.log('字段迁移处理:', error.message);
    }
    
    console.log('数据库初始化成功');
  } catch (error) {
    console.error('数据库初始化失败:', error);
  }
}

// API 路由

// 获取所有会话
app.get('/api/sessions', async (req, res) => {
  try {
    const { userId, projectId } = req.query;
    console.log('🔍 GET /api/sessions 请求参数:', { userId, projectId });
    
    let query = 'SELECT * FROM sessions';
    let params = [];
    let conditions = [];
    
    if (userId) {
      conditions.push('user_id = ?');
      params.push(userId);
    }
    
    if (projectId) {
      conditions.push('project_id = ?');
      params.push(projectId);
    }
    
    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }
    
    query += ' ORDER BY updated_at DESC';
    
    console.log('🔍 执行SQL查询:', query, '参数:', params);
    const sessions = await db.all(query, params);
    console.log('🔍 查询结果:', sessions.length, '条会话');
    
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    const formattedSessions = sessions.map(session => ({
      ...session,
      userId: session.user_id,
      projectId: session.project_id,
      createdAt: session.created_at,
      updatedAt: session.updated_at
    }));
    res.json(formattedSessions);
  } catch (error) {
    console.error('❌ GET /api/sessions 错误:', error);
    res.status(500).json({ error: error.message });
  }
});

// 创建新会话
app.post('/api/sessions', async (req, res) => {
  try {
    const { id, title, userId, projectId } = req.body;
    console.log('🔍 POST /api/sessions 请求数据:', { id, title, userId, projectId });
    
    const result = await db.run(
      'INSERT INTO sessions (id, user_id, project_id, title) VALUES (?, ?, ?, ?)',
      [id, userId, projectId, title]
    );
    console.log('🔍 插入结果:', result);
    
    const session = await db.get('SELECT * FROM sessions WHERE id = ?', [id]);
    console.log('🔍 创建的会话:', session);
    res.json(session);
  } catch (error) {
    console.error('❌ POST /api/sessions 错误:', error);
    res.status(500).json({ error: error.message });
  }
});

// 获取会话详情
app.get('/api/sessions/:id', async (req, res) => {
  try {
    const session = await db.get('SELECT * FROM sessions WHERE id = ?', [req.params.id]);
    if (!session) {
      return res.status(404).json({ error: '会话不存在' });
    }
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    const formattedSession = {
      ...session,
      userId: session.user_id,
      createdAt: session.created_at,
      updatedAt: session.updated_at
    };
    res.json(formattedSession);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除会话
app.delete('/api/sessions/:id', async (req, res) => {
  try {
    await db.run('DELETE FROM sessions WHERE id = ?', [req.params.id]);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 获取会话消息
app.get('/api/sessions/:id/messages', async (req, res) => {
  try {
    console.log(`获取会话 ${req.params.id} 的消息`);
    
    // 首先检查会话是否存在
    const session = await db.get('SELECT id FROM sessions WHERE id = ?', [req.params.id]);
    if (!session) {
      console.log(`会话 ${req.params.id} 不存在`);
      return res.status(404).json({ error: '会话不存在' });
    }
    
    const messages = await db.all(
      'SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC',
      [req.params.id]
    );
    
    console.log(`找到 ${messages.length} 条消息`);
    
    // 解析JSON字段
    const formattedMessages = messages.map(message => ({
      ...message,
      toolCalls: message.tool_calls ? JSON.parse(message.tool_calls) : null,
      toolCallId: message.tool_call_id,
      metadata: message.metadata ? JSON.parse(message.metadata) : null,
      // 保持向后兼容
      tool_calls: undefined,
      tool_call_id: undefined
    }));
    res.json(formattedMessages);
  } catch (error) {
    console.error(`获取消息时出错:`, error);
    res.status(500).json({ error: error.message });
  }
});

// 创建消息
app.post('/api/messages', async (req, res) => {
  try {
    const { id, sessionId, role, content, summary, toolCalls, toolCallId, reasoning, metadata, createdAt } = req.body;
    
    // 为可选字段提供默认值
    const toolCallsJson = toolCalls ? JSON.stringify(toolCalls) : null;
    const metadataJson = metadata ? JSON.stringify(metadata) : null;
    const messageCreatedAt = createdAt || new Date().toISOString();
    
    await db.run(
      'INSERT INTO messages (id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [id, sessionId, role, content, summary || null, toolCallsJson, toolCallId || null, reasoning || null, metadataJson, messageCreatedAt]
    );
    
    // 更新会话的 updated_at
    await db.run(
      'UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [sessionId]
    );
    
    const message = await db.get('SELECT * FROM messages WHERE id = ?', [id]);
    res.json(message);
  } catch (error) {
    console.error('创建消息失败:', error);
    res.status(500).json({ error: error.message });
  }
});

// 获取 MCP 配置
app.get('/api/mcp-configs', async (req, res) => {
  try {
    const { userId } = req.query;
    let query = 'SELECT * FROM mcp_configs';
    let params = [];
    
    if (userId) {
      query += ' WHERE user_id = ?';
      params.push(userId);
    }
    
    query += ' ORDER BY created_at DESC';
    const configs = await db.all(query, params);
    res.json(configs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建 MCP 配置
app.post('/api/mcp-configs', async (req, res) => {
  try {
    const { id, name, command, args, env, userId, enabled } = req.body;
    // 如果没有提供 id 或 id 为 null，则生成一个新的 id
    const configId = id || Date.now().toString();
    await db.run(
      'INSERT INTO mcp_configs (id, name, command, args, env, user_id, enabled) VALUES (?, ?, ?, ?, ?, ?, ?)',
      [configId, name, command, JSON.stringify(args || []), JSON.stringify(env || {}), userId, enabled]
    );
    const config = await db.get('SELECT * FROM mcp_configs WHERE id = ?', [configId]);
    res.json(config);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 更新 MCP 配置
app.put('/api/mcp-configs/:id', async (req, res) => {
  try {
    const { name, command, args, env, userId, enabled } = req.body;
    await db.run(
      'UPDATE mcp_configs SET name = ?, command = ?, args = ?, env = ?, user_id = ?, enabled = ? WHERE id = ?',
      [name, command, JSON.stringify(args), JSON.stringify(env), userId, enabled, req.params.id]
    );
    const config = await db.get('SELECT * FROM mcp_configs WHERE id = ?', [req.params.id]);
    res.json(config);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除 MCP 配置
app.delete('/api/mcp-configs/:id', async (req, res) => {
  try {
    await db.run('DELETE FROM mcp_configs WHERE id = ?', [req.params.id]);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// AI模型配置相关API

// 获取所有AI模型配置
app.get('/api/ai-model-configs', async (req, res) => {
  try {
    const { userId } = req.query;
    let query = 'SELECT * FROM ai_model_configs';
    let params = [];
    
    if (userId) {
      query += ' WHERE user_id = ?';
      params.push(userId);
    }
    
    query += ' ORDER BY created_at DESC';
    
    const configs = await db.all(query, params);
    res.json(configs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建AI模型配置
app.post('/api/ai-model-configs', async (req, res) => {
  try {
    const { id, name, provider, model, apiKey, baseUrl, userId, enabled = true } = req.body;
    await db.run(
      'INSERT INTO ai_model_configs (id, name, provider, model, api_key, base_url, user_id, enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      [id, name, provider, model, apiKey, baseUrl, userId, enabled]
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 更新AI模型配置
app.put('/api/ai-model-configs/:id', async (req, res) => {
  try {
    const { name, provider, model, apiKey, baseUrl, userId, enabled } = req.body;
    await db.run(
      'UPDATE ai_model_configs SET name = ?, provider = ?, model = ?, api_key = ?, base_url = ?, user_id = ?, enabled = ? WHERE id = ?',
      [name, provider, model, apiKey, baseUrl, userId, enabled, req.params.id]
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除AI模型配置
app.delete('/api/ai-model-configs/:id', async (req, res) => {
  try {
    await db.run('DELETE FROM ai_model_configs WHERE id = ?', [req.params.id]);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 获取会话的MCP服务器配置
app.get('/api/sessions/:sessionId/mcp-servers', async (req, res) => {
  try {
    const { sessionId } = req.params;
    const mcpServers = await db.all(`
      SELECT sms.*, mc.name, mc.command, mc.args, mc.env
      FROM session_mcp_servers sms
      JOIN mcp_configs mc ON sms.mcp_config_id = mc.id
      WHERE sms.session_id = ? AND sms.enabled = true
      ORDER BY sms.created_at ASC
    `, [sessionId]);
    res.json(mcpServers);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 为会话添加MCP服务器
app.post('/api/sessions/:sessionId/mcp-servers', async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { mcpConfigId } = req.body;
    const id = Date.now().toString();
    
    await db.run(
      'INSERT INTO session_mcp_servers (id, session_id, mcp_config_id) VALUES (?, ?, ?)',
      [id, sessionId, mcpConfigId]
    );
    
    const sessionMcpServer = await db.get(
      'SELECT * FROM session_mcp_servers WHERE id = ?',
      [id]
    );
    res.json(sessionMcpServer);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除会话的MCP服务器配置
app.delete('/api/sessions/:sessionId/mcp-servers/:mcpConfigId', async (req, res) => {
  try {
    const { sessionId, mcpConfigId } = req.params;
    await db.run(
      'DELETE FROM session_mcp_servers WHERE session_id = ? AND mcp_config_id = ?',
      [sessionId, mcpConfigId]
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 获取系统上下文列表
app.get('/api/system-contexts', async (req, res) => {
  try {
    const { userId } = req.query;
    const contexts = await db.all(
      'SELECT * FROM system_contexts WHERE user_id = ? ORDER BY created_at DESC',
      [userId]
    );
    res.json(contexts);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 获取当前激活的系统上下文
app.get('/api/system-context/active', async (req, res) => {
  try {
    const { userId } = req.query;
    const result = await db.get(
      'SELECT * FROM system_contexts WHERE user_id = ? AND is_active = true',
      [userId]
    );
    res.json({ content: result?.content || '', context: result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建系统上下文
app.post('/api/system-contexts', async (req, res) => {
  try {
    const { name, content, userId } = req.body;
    const id = Date.now().toString();
    
    await db.run(
      'INSERT INTO system_contexts (id, name, content, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, datetime("now"), datetime("now"))',
      [id, name, content, userId]
    );
    
    const newContext = await db.get('SELECT * FROM system_contexts WHERE id = ?', [id]);
    res.json(newContext);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 更新系统上下文
app.put('/api/system-contexts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { name, content } = req.body;
    
    await db.run(
      'UPDATE system_contexts SET name = ?, content = ?, updated_at = datetime("now") WHERE id = ?',
      [name, content, id]
    );
    
    const updatedContext = await db.get('SELECT * FROM system_contexts WHERE id = ?', [id]);
    res.json(updatedContext);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除系统上下文
app.delete('/api/system-contexts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    await db.run('DELETE FROM system_contexts WHERE id = ?', [id]);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 激活系统上下文
app.post('/api/system-contexts/:id/activate', async (req, res) => {
  try {
    const { id } = req.params;
    const { userId } = req.body;
    
    // 先将该用户的所有上下文设为非激活状态
    await db.run(
      'UPDATE system_contexts SET is_active = false WHERE user_id = ?',
      [userId]
    );
    
    // 激活指定的上下文
    await db.run(
      'UPDATE system_contexts SET is_active = true WHERE id = ? AND user_id = ?',
      [id, userId]
    );
    
    const activeContext = await db.get('SELECT * FROM system_contexts WHERE id = ?', [id]);
    res.json(activeContext);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// AI 代理路由
// 通用 AI API 代理 - 支持所有 HTTP 方法的透明转发
app.all('/api/chat/completions', handleChatProxy);

// AI 代理健康检查
app.get('/api/proxy/health', handleHealthCheck);

// 服务前端静态文件 - 处理所有非API路由
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api')) {
    res.sendFile(path.join(__dirname, '../dist/index.html'));
  } else {
    res.status(404).json({ error: 'API endpoint not found' });
  }
});

// 启动服务器
async function startServer() {
  await initDatabase();
  app.listen(PORT, () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
  });
}

startServer().catch(console.error);

export default app;