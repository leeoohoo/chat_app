import express from 'express';
import cors from 'cors';
import path from 'path';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
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
      
      CREATE TABLE IF NOT EXISTS system_context (
        id INTEGER PRIMARY KEY,
        content TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
    
    console.log('数据库初始化成功');
  } catch (error) {
    console.error('数据库初始化失败:', error);
  }
}

// API 路由

// 获取所有会话
app.get('/api/sessions', async (req, res) => {
  try {
    const sessions = await db.all('SELECT * FROM sessions ORDER BY updated_at DESC');
    // 转换字段名：数据库使用下划线命名，前端使用驼峰命名
    const formattedSessions = sessions.map(session => ({
      ...session,
      createdAt: session.created_at,
      updatedAt: session.updated_at
    }));
    res.json(formattedSessions);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建新会话
app.post('/api/sessions', async (req, res) => {
  try {
    const { id, title } = req.body;
    const result = await db.run(
      'INSERT INTO sessions (id, title) VALUES (?, ?)',
      [id, title]
    );
    const session = await db.get('SELECT * FROM sessions WHERE id = ?', [id]);
    res.json(session);
  } catch (error) {
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
    const { id, sessionId, role, content, toolCalls, toolCallId, reasoning, metadata, createdAt } = req.body;
    
    // 为可选字段提供默认值
    const toolCallsJson = toolCalls ? JSON.stringify(toolCalls) : null;
    const metadataJson = metadata ? JSON.stringify(metadata) : null;
    const messageCreatedAt = createdAt || new Date().toISOString();
    
    await db.run(
      'INSERT INTO messages (id, session_id, role, content, tool_calls, tool_call_id, reasoning, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [id, sessionId, role, content, toolCallsJson, toolCallId || null, reasoning || null, metadataJson, messageCreatedAt]
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
    const configs = await db.all('SELECT * FROM mcp_configs ORDER BY created_at DESC');
    res.json(configs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建 MCP 配置
app.post('/api/mcp-configs', async (req, res) => {
  try {
    const { id, name, command, args, env, enabled } = req.body;
    await db.run(
      'INSERT INTO mcp_configs (id, name, command, args, env, enabled) VALUES (?, ?, ?, ?, ?, ?)',
      [id, name, command, JSON.stringify(args), JSON.stringify(env), enabled]
    );
    const config = await db.get('SELECT * FROM mcp_configs WHERE id = ?', [id]);
    res.json(config);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 更新 MCP 配置
app.put('/api/mcp-configs/:id', async (req, res) => {
  try {
    const { name, command, args, env, enabled } = req.body;
    await db.run(
      'UPDATE mcp_configs SET name = ?, command = ?, args = ?, env = ?, enabled = ? WHERE id = ?',
      [name, command, JSON.stringify(args), JSON.stringify(env), enabled, req.params.id]
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
    const configs = await db.all('SELECT * FROM ai_model_configs ORDER BY created_at DESC');
    res.json(configs);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建AI模型配置
app.post('/api/ai-model-configs', async (req, res) => {
  try {
    const { id, name, provider, model, apiKey, baseUrl, enabled = true } = req.body;
    await db.run(
      'INSERT INTO ai_model_configs (id, name, provider, model, api_key, base_url, enabled) VALUES (?, ?, ?, ?, ?, ?, ?)',
      [id, name, provider, model, apiKey, baseUrl, enabled]
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 更新AI模型配置
app.put('/api/ai-model-configs/:id', async (req, res) => {
  try {
    const { name, provider, model, apiKey, baseUrl, enabled } = req.body;
    await db.run(
      'UPDATE ai_model_configs SET name = ?, provider = ?, model = ?, api_key = ?, base_url = ?, enabled = ? WHERE id = ?',
      [name, provider, model, apiKey, baseUrl, enabled, req.params.id]
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

// 获取系统上下文
app.get('/api/system-context', async (req, res) => {
  try {
    const result = await db.get(
      'SELECT content FROM system_context WHERE id = 1'
    );
    res.json({ content: result?.content || '' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 更新系统上下文
app.post('/api/system-context', async (req, res) => {
  try {
    const { content } = req.body;
    await db.run(
      'INSERT OR REPLACE INTO system_context (id, content, updated_at) VALUES (1, ?, datetime("now"))',
      [content]
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

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