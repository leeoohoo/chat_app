/**
 * Chat API v2 - 流式聊天核心功能
 * 复刻自 Python: app/api/chat_api_v2.py
 */

import express from 'express';
import { AiServer } from '../services/v2/ai-server.js';
import { McpToolExecute } from '../services/v2/mcp-tool-execute.js';
import { McpConfigService } from '../models/mcp-config.js';
import { buildSseStream, buildSseStreamFromAgentId } from '../services/v2/agent.js';
import { logger } from '../utils/logger.js';
import { config } from '../utils/config.js';
import { getDatabaseSync } from '../models/database-factory.js';

const router = express.Router();

/**
 * 加载 MCP 配置（同步）
 */
function loadMcpConfigsSync(userId = null) {
  try {
    const db = getDatabaseSync();

    let query = 'SELECT * FROM mcp_configs WHERE enabled = 1';
    const params = [];

    if (userId) {
      query += ' AND user_id = ?';
      params.push(userId);
    }

    const configs = db.fetchallSync(query, params);

    const httpServers = [];
    const stdioServers = [];

    for (const cfg of configs) {
      const serverName = `${cfg.name}_${cfg.id.substring(0, 8)}`;

      if (cfg.type === 'http') {
        httpServers.push({
          name: serverName,
          url: cfg.command  // HTTP 类型中 command 字段存储 URL
        });
      } else if (cfg.type === 'stdio') {
        // 解析 args
        let args = [];
        if (cfg.args) {
          if (typeof cfg.args === 'string') {
            try {
              const parsed = JSON.parse(cfg.args);
              if (Array.isArray(parsed)) {
                args = parsed.map(a => String(a).trim()).filter(a => a);
              }
            } catch (e) {
              // 如果不是 JSON，尝试按空格分割
              args = cfg.args.trim().split(/\s+/).filter(a => a);
            }
          } else if (Array.isArray(cfg.args)) {
            args = cfg.args.map(a => String(a).trim()).filter(a => a);
          }
        }

        // 解析 env
        let env = {};
        if (cfg.env) {
          if (typeof cfg.env === 'string') {
            try {
              const parsed = JSON.parse(cfg.env);
              if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                env = parsed;
              }
            } catch (e) {
              // 解析失败，使用空对象
              env = {};
            }
          } else if (cfg.env && typeof cfg.env === 'object' && !Array.isArray(cfg.env)) {
            env = cfg.env;
          }
        }

        let cwd = cfg.cwd;

        // 读取激活的配置档案并覆盖 args/env/cwd
        try {
          const activeProfile = db.fetchoneSync(
            'SELECT * FROM mcp_config_profiles WHERE mcp_config_id = ? AND enabled = 1',
            [cfg.id]
          );

          if (activeProfile) {
            // 解析档案的 args
            if (activeProfile.args) {
              let profArgs = [];
              if (typeof activeProfile.args === 'string') {
                try {
                  const parsed = JSON.parse(activeProfile.args);
                  if (Array.isArray(parsed)) {
                    profArgs = parsed.map(a => String(a).trim()).filter(a => a);
                  }
                } catch (e) {
                  profArgs = [];
                }
              } else if (Array.isArray(activeProfile.args)) {
                profArgs = activeProfile.args.map(a => String(a).trim()).filter(a => a);
              }
              if (profArgs.length > 0) {
                args = profArgs;
              }
            }

            // 解析档案的 env
            if (activeProfile.env) {
              let profEnv = {};
              if (typeof activeProfile.env === 'string') {
                try {
                  const parsed = JSON.parse(activeProfile.env);
                  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                    profEnv = parsed;
                  }
                } catch (e) {
                  profEnv = {};
                }
              } else if (activeProfile.env && typeof activeProfile.env === 'object') {
                profEnv = activeProfile.env;
              }
              if (Object.keys(profEnv).length > 0) {
                env = profEnv;
                logger.info(`[CHAT_V2] 从档案加载 env: ${JSON.stringify(env)}`);
              }
            }

            // 档案的 cwd
            if (activeProfile.cwd) {
              cwd = activeProfile.cwd;
            }

            logger.info(`应用配置档案: ${activeProfile.name} (id=${activeProfile.id}), env keys: ${Object.keys(env).join(', ')}`);
          }
        } catch (e) {
          logger.warn(`加载配置档案失败: ${e.message}`);
        }

        const server = {
          name: serverName,
          command: cfg.command
        };

        // 只有当有值时才添加（与 Python 版本一致）
        if (args.length > 0) {
          server.args = args;
        }
        if (cwd) {
          server.cwd = cwd;
        }
        if (env && Object.keys(env).length > 0) {
          server.env = env;
        }

        stdioServers.push(server);
      }
    }

    return { httpServers, stdioServers };
  } catch (error) {
    logger.error('加载 MCP 配置失败:', error);
    return { httpServers: [], stdioServers: [] };
  }
}

/**
 * POST /api/agent_v2/chat/stream - 流式聊天端点
 */
router.post('/agent_v2/chat/stream', async (req, res) => {
  try {
    const { session_id, content, ai_model_config, user_id } = req.body;

    if (!session_id || !content) {
      return res.status(400).json({
        error: 'session_id 和 content 不能为空'
      });
    }

    // 获取模型配置
    const modelConfig = ai_model_config || {};
    const model = modelConfig.model_name || 'gpt-4';
    const temperature = modelConfig.temperature || 0.7;
    const maxTokens = modelConfig.max_tokens || null;
    const useTools = modelConfig.use_tools !== false;
    const apiKey = modelConfig.api_key || config.OPENAI_API_KEY;
    const baseUrl = modelConfig.base_url || config.OPENAI_BASE_URL;

    // 加载 MCP 配置
    const { httpServers, stdioServers } = loadMcpConfigsSync(user_id);

    // 创建 MCP 工具执行器
    const mcpToolExecute = new McpToolExecute({
      mcp_servers: httpServers,
      stdio_mcp_servers: stdioServers
    });

    // 初始化工具
    if (useTools && (httpServers.length > 0 || stdioServers.length > 0)) {
      logger.info(`初始化 MCP 工具 (${httpServers.length} HTTP + ${stdioServers.length} STDIO)`);
      await mcpToolExecute.init();
      logger.info(`MCP 工具初始化完成，共 ${mcpToolExecute.getTools().length} 个工具`);
    }

    // 创建 AI 服务器
    const aiServer = new AiServer({
      openaiApiKey: apiKey,
      mcpToolExecute,
      defaultModel: model,
      defaultTemperature: temperature,
      baseUrl
    });

    // 设置 SSE 响应头
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    // 发送 SSE 事件
    const sendSSE = (data) => {
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    };

    // 发送开始事件
    sendSSE({
      type: 'start',
      session_id,
      timestamp: new Date().toISOString()
    });

    // 定义回调函数
    const onChunk = (chunk) => {
      sendSSE({
        type: 'chunk',
        content: chunk,
        timestamp: new Date().toISOString()
      });
    };

    const onThinkingChunk = (text) => {
      sendSSE({
        type: 'thinking',
        content: text,
        timestamp: new Date().toISOString()
      });
    };

    const onToolsStart = (toolCalls) => {
      sendSSE({
        type: 'tools_start',
        data: { tool_calls: toolCalls },
        timestamp: new Date().toISOString()
      });
    };

    const onToolsStream = (result) => {
      sendSSE({
        type: 'tools_stream',
        data: result,
        timestamp: new Date().toISOString()
      });
    };

    const onToolsEnd = (results) => {
      sendSSE({
        type: 'tools_end',
        data: { tool_results: results },
        timestamp: new Date().toISOString()
      });
    };

    try {
      // 执行聊天
      const result = await aiServer.chat(session_id, content, {
        model,
        temperature,
        maxTokens,
        useTools,
        onChunk,
        onThinkingChunk,
        onToolsStart,
        onToolsStream,
        onToolsEnd
      });

      // 发送完成事件
      sendSSE({
        type: 'complete',
        result,
        timestamp: new Date().toISOString()
      });

      // 发送结束标记
      sendSSE('[DONE]');

    } catch (error) {
      logger.error('聊天处理失败:', error);
      sendSSE({
        type: 'error',
        data: { error: error.message },
        timestamp: new Date().toISOString()
      });
    } finally {
      // 清理资源
      await mcpToolExecute.cleanup();
      res.end();
    }

  } catch (error) {
    logger.error('流式聊天失败:', error);
    if (!res.headersSent) {
      res.status(500).json({ error: error.message });
    } else {
      res.end();
    }
  }
});

/**
 * GET /api/agent_v2/tools - 获取可用工具列表
 */
router.get('/agent_v2/tools', async (req, res) => {
  try {
    const { user_id } = req.query;

    // 加载 MCP 配置
    const { httpServers, stdioServers } = loadMcpConfigsSync(user_id);

    // 创建 MCP 工具执行器
    const mcpToolExecute = new McpToolExecute({
      mcp_servers: httpServers,
      stdio_mcp_servers: stdioServers
    });

    // 初始化工具
    await mcpToolExecute.init();

    // 获取工具列表
    const tools = mcpToolExecute.getTools();

    res.json({
      tools,
      count: tools.length,
      servers: {
        http: httpServers.length,
        stdio: stdioServers.length
      }
    });

  } catch (error) {
    logger.error('获取工具列表失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/agent_v2/status - 获取服务器状态
 */
router.get('/agent_v2/status', (req, res) => {
  res.json({
    status: 'ok',
    version: '2.0.0',
    timestamp: new Date().toISOString(),
    openai: {
      configured: Boolean(config.OPENAI_API_KEY),
      base_url: config.OPENAI_BASE_URL
    }
  });
});

/**
 * POST /api/agent_v2/session/:session_id/reset - 重置会话
 */
router.post('/agent_v2/session/:session_id/reset', async (req, res) => {
  try {
    const { session_id } = req.params;
    const db = getDatabaseSync();

    // 删除会话的所有消息
    db.executeSync('DELETE FROM messages WHERE session_id = ?', [session_id]);

    logger.info(`会话重置完成: session_id=${session_id}`);
    res.json({
      success: true,
      message: '会话重置成功',
      session_id
    });
  } catch (error) {
    logger.error('会话重置失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/agent_v2/session/:session_id/config - 获取会话配置
 */
router.get('/agent_v2/session/:session_id/config', async (req, res) => {
  try {
    const { session_id } = req.params;

    // 返回默认配置
    const sessionConfig = {
      model: config.OPENAI_MODEL || 'gpt-4',
      temperature: 0.7,
      session_id
    };

    res.json({
      success: true,
      config: sessionConfig
    });
  } catch (error) {
    logger.error('获取会话配置失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/agent_v2/session/:session_id/config - 更新会话配置
 */
router.post('/agent_v2/session/:session_id/config', async (req, res) => {
  try {
    const { session_id } = req.params;
    const configData = req.body;

    // TODO: 实现会话配置存储
    // 目前只是返回成功，实际应该存储到数据库或内存中

    logger.info(`会话配置更新完成: session_id=${session_id}`);
    res.json({
      success: true,
      message: '会话配置更新成功'
    });
  } catch (error) {
    logger.error('会话配置更新失败:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/agent_v2/chat/stream/simple - 简化的流式聊天端点（使用 Agent 封装）
 */
router.post('/agent_v2/chat/stream/simple', async (req, res) => {
  try {
    const { session_id, content, ai_model_config, user_id, agent_id } = req.body;

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
      let stream;

      // 如果提供了 agent_id，使用 agent 配置
      if (agent_id) {
        stream = buildSseStreamFromAgentId(session_id, content, agent_id, user_id);
      } else {
        // 否则使用 model_config
        const modelConfig = ai_model_config || {};
        stream = buildSseStream(session_id, content, modelConfig, user_id);
      }

      // 迭代异步生成器并写入响应
      for await (const chunk of stream) {
        res.write(chunk);
      }

      // 发送结束标记
      res.write('data: [DONE]\n\n');

    } catch (error) {
      logger.error('简化聊天处理失败:', error);
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
    logger.error('简化流式聊天失败:', error);
    if (!res.headersSent) {
      res.status(500).json({ error: error.message });
    } else {
      res.end();
    }
  }
});

export default router;
