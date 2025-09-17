// 共享数据库服务层 - 可以在前端和后端共同使用
import sqlite3 from 'sqlite3';
import { open, Database } from 'sqlite';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// 类型定义
export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: string;
  content: string;
  summary?: string;
  tool_calls?: string;
  tool_call_id?: string;
  reasoning?: string;
  metadata?: string;
  created_at: string;
}

export interface McpConfig {
  id: string;
  name: string;
  command: string;
  args?: string;
  env?: string;
  enabled: boolean;
  created_at: string;
}

export interface AiModelConfig {
  id: string;
  name: string;
  provider: string;
  model: string;
  api_key?: string;
  base_url?: string;
  enabled: boolean;
  created_at: string;
}

// 共享数据库服务类
export class SharedDatabaseService {
  private db: Database | null = null;
  private dbPath: string;

  constructor(dbPath?: string) {
    // 如果在浏览器环境中，使用默认路径
    if (typeof window !== 'undefined') {
      this.dbPath = dbPath || 'chat.db';
    } else {
      // Node.js 环境
      const __filename = fileURLToPath(import.meta.url);
      const __dirname = dirname(__filename);
      this.dbPath = dbPath || path.join(__dirname, '../../../data/chat.db');
    }
  }

  // 初始化数据库
  async init(): Promise<void> {
    try {
      this.db = await open({
        filename: this.dbPath,
        driver: sqlite3.Database
      });
      
      await this.createTables();
      console.log('数据库初始化成功');
    } catch (error) {
      console.error('数据库初始化失败:', error);
      throw error;
    }
  }

  // 创建表结构
  private async createTables(): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    
    await this.db.exec(`
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
        summary TEXT,
        tool_calls TEXT,
        tool_call_id TEXT,
        reasoning TEXT,
        metadata TEXT,
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
  }

  // 会话相关方法
  async getAllSessions(): Promise<Session[]> {
    if (!this.db) throw new Error('数据库未初始化');
    return await this.db.all('SELECT * FROM sessions ORDER BY updated_at DESC');
  }

  async createSession(id: string, title: string): Promise<Session> {
    if (!this.db) throw new Error('数据库未初始化');
    await this.db.run(
      'INSERT INTO sessions (id, title) VALUES (?, ?)',
      [id, title]
    );
    const session = await this.db.get('SELECT * FROM sessions WHERE id = ?', [id]);
    return session as Session;
  }

  async getSession(id: string): Promise<Session | null> {
    if (!this.db) throw new Error('数据库未初始化');
    const session = await this.db.get('SELECT * FROM sessions WHERE id = ?', [id]);
    return session as Session || null;
  }

  async deleteSession(id: string): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    await this.db.run('DELETE FROM sessions WHERE id = ?', [id]);
  }

  // 消息相关方法
  async getSessionMessages(sessionId: string): Promise<Message[]> {
    if (!this.db) throw new Error('数据库未初始化');
    return await this.db.all(
      'SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC',
      [sessionId]
    );
  }

  async createMessage(messageData: Omit<Message, 'created_at'>): Promise<Message> {
    if (!this.db) throw new Error('数据库未初始化');
    
    const { id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata } = messageData;
    
    await this.db.run(
      'INSERT INTO messages (id, session_id, role, content, summary, tool_calls, tool_call_id, reasoning, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [id, session_id, role, content, summary || null, tool_calls || null, tool_call_id || null, reasoning || null, metadata || null]
    );
    
    // 更新会话的 updated_at
    await this.db.run(
      'UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
      [session_id]
    );
    
    const message = await this.db.get('SELECT * FROM messages WHERE id = ?', [id]);
    return message as Message;
  }

  // MCP配置相关方法
  async getMcpConfigs(): Promise<McpConfig[]> {
    if (!this.db) throw new Error('数据库未初始化');
    return await this.db.all('SELECT * FROM mcp_configs ORDER BY created_at DESC');
  }

  async createMcpConfig(config: Omit<McpConfig, 'created_at'>): Promise<McpConfig> {
    if (!this.db) throw new Error('数据库未初始化');
    
    const { id, name, command, args, env, enabled } = config;
    await this.db.run(
      'INSERT INTO mcp_configs (id, name, command, args, env, enabled) VALUES (?, ?, ?, ?, ?, ?)',
      [id, name, command, args || null, env || null, enabled]
    );
    
    const result = await this.db.get('SELECT * FROM mcp_configs WHERE id = ?', [id]);
    return result as McpConfig;
  }

  async updateMcpConfig(id: string, updates: Partial<McpConfig>): Promise<McpConfig> {
    if (!this.db) throw new Error('数据库未初始化');
    
    const { name, command, args, env, enabled } = updates;
    await this.db.run(
      'UPDATE mcp_configs SET name = ?, command = ?, args = ?, env = ?, enabled = ? WHERE id = ?',
      [name, command, args, env, enabled, id]
    );
    
    const result = await this.db.get('SELECT * FROM mcp_configs WHERE id = ?', [id]);
    return result as McpConfig;
  }

  async deleteMcpConfig(id: string): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    await this.db.run('DELETE FROM mcp_configs WHERE id = ?', [id]);
  }

  // AI模型配置相关方法
  async getAiModelConfigs(): Promise<AiModelConfig[]> {
    if (!this.db) throw new Error('数据库未初始化');
    return await this.db.all('SELECT * FROM ai_model_configs ORDER BY created_at DESC');
  }

  async createAiModelConfig(config: Omit<AiModelConfig, 'created_at'>): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    
    const { id, name, provider, model, api_key, base_url, enabled } = config;
    await this.db.run(
      'INSERT INTO ai_model_configs (id, name, provider, model, api_key, base_url, enabled) VALUES (?, ?, ?, ?, ?, ?, ?)',
      [id, name, provider, model, api_key || null, base_url || null, enabled]
    );
  }

  async updateAiModelConfig(id: string, updates: Partial<AiModelConfig>): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    
    const { name, provider, model, api_key, base_url, enabled } = updates;
    await this.db.run(
      'UPDATE ai_model_configs SET name = ?, provider = ?, model = ?, api_key = ?, base_url = ?, enabled = ? WHERE id = ?',
      [name, provider, model, api_key, base_url, enabled, id]
    );
  }

  async deleteAiModelConfig(id: string): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    await this.db.run('DELETE FROM ai_model_configs WHERE id = ?', [id]);
  }

  // 系统上下文相关方法
  async getSystemContext(): Promise<{ content: string }> {
    if (!this.db) throw new Error('数据库未初始化');
    
    const result = await this.db.get(
      'SELECT content FROM system_context WHERE id = 1'
    );
    return { content: result?.content || '' };
  }

  async updateSystemContext(content: string): Promise<void> {
    if (!this.db) throw new Error('数据库未初始化');
    
    await this.db.run(
      'INSERT OR REPLACE INTO system_context (id, content, updated_at) VALUES (1, ?, datetime("now"))',
      [content]
    );
  }

  // 关闭数据库连接
  async close(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
    }
  }
}

// 导出单例实例
export const sharedDatabaseService = new SharedDatabaseService();