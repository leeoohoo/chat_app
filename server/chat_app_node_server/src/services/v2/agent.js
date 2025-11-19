/**
 * Agent 封装类 - 提供简单易用的 Agent 接口
 * 复刻自 Python: app/services/v2/agent.py
 *
 * 封装所有复杂的配置和调用逻辑，支持根据 user_id 自动加载 MCP 配置
 */

import OpenAI from 'openai';
import { MessageManager } from './message-manager.js';
import { AiRequestHandler } from './ai-request-handler.js';
import { ToolResultProcessor } from './tool-result-processor.js';
import { McpToolExecute } from './mcp-tool-execute.js';
import { AiClient } from './ai-client.js';
import { logger } from '../../utils/logger.js';
import { getDatabaseSync } from '../../models/database-factory.js';

/**
 * Agent 配置类
 */
export class AgentConfig {
  constructor(options = {}) {
    this.api_key = options.api_key;
    this.base_url = options.base_url || null;
    this.model_name = options.model_name || 'gpt-4';
    this.system_prompt = options.system_prompt || null;
    this.temperature = options.temperature !== undefined ? options.temperature : 0.7;
    this.max_tokens = options.max_tokens || null;
    this.mcp_servers = options.mcp_servers || [];
    this.stdio_mcp_servers = options.stdio_mcp_servers || [];
    this.user_id = options.user_id || null;
  }
}

/**
 * Agent 封装类
 * 提供简单的接口来执行带工具调用的对话
 */
export class Agent {
  constructor(config) {
    this.config = config;

    // 初始化 OpenAI 客户端
    const clientOptions = { apiKey: config.api_key };
    if (config.base_url) {
      clientOptions.baseURL = config.base_url;
    }
    this.openaiClient = new OpenAI(clientOptions);

    // 解析 MCP 服务器配置
    const { mcpServers, stdioMcpServers } = this._resolveMcpServers(config);

    // 初始化 MCP 工具执行器
    this.mcpToolExecute = new McpToolExecute({
      mcp_servers: mcpServers,
      stdio_mcp_servers: stdioMcpServers
    });

    // 初始化各个组件
    this.messageManager = new MessageManager();
    this.aiRequestHandler = new AiRequestHandler(this.openaiClient, this.messageManager);
    this.toolResultProcessor = new ToolResultProcessor(this.messageManager, this.aiRequestHandler);
    this.aiClient = new AiClient(
      this.aiRequestHandler,
      this.mcpToolExecute,
      this.toolResultProcessor,
      this.messageManager
    );

    // 设置系统提示
    if (this.config.system_prompt) {
      this.aiClient.setSystemPrompt(this.config.system_prompt);
    }

    logger.info(`[AGENT] 初始化完成 - 模型: ${config.model_name}, 工具数: ${this.mcpToolExecute.getTools().length}`);
  }

  /**
   * 初始化 Agent（异步初始化工具）
   */
  async init() {
    await this.mcpToolExecute.init();
    logger.info(`[AGENT] 工具初始化完成，共 ${this.mcpToolExecute.getTools().length} 个工具`);
  }

  /**
   * 解析 MCP 服务器配置
   */
  _resolveMcpServers(config) {
    // 如果已提供配置，直接使用
    if (config.mcp_servers.length > 0 || config.stdio_mcp_servers.length > 0) {
      return {
        mcpServers: config.mcp_servers,
        stdioMcpServers: config.stdio_mcp_servers
      };
    }

    // 否则尝试根据 user_id 加载
    const { httpServers, stdioServers } = this._loadMcpConfigsForUser(config.user_id);

    // 转换为 Agent 需要的结构
    const mcpServers = Object.entries(httpServers).map(([name, cfg]) => ({
      name,
      url: cfg.url
    }));

    const stdioMcpServers = Object.entries(stdioServers).map(([name, cfg]) => {
      const server = {
        name,
        command: cfg.command
      };
      if (cfg.args && cfg.args.length > 0) {
        server.args = cfg.args;
      }
      if (cfg.env && Object.keys(cfg.env).length > 0) {
        server.env = cfg.env;
      }
      if (cfg.cwd) {
        server.cwd = cfg.cwd;
      }
      return server;
    });

    return { mcpServers, stdioMcpServers };
  }

  /**
   * 按用户加载 MCP 配置
   */
  _loadMcpConfigsForUser(userId) {
    try {
      const db = getDatabaseSync();

      let query = 'SELECT * FROM mcp_configs WHERE enabled = 1';
      const params = [];

      if (userId) {
        query += ' AND user_id = ?';
        params.push(userId);
      }

      const configs = db.fetchallSync(query, params);

      const httpServers = {};
      const stdioServers = {};

      for (const config of configs) {
        const serverName = config.name;
        const serverAlias = `${serverName}_${config.id.substring(0, 8)}`;
        const command = config.command;
        const serverType = config.type || 'stdio';

        // 解析 args
        let args = [];
        if (config.args) {
          if (typeof config.args === 'string') {
            try {
              const parsed = JSON.parse(config.args);
              if (Array.isArray(parsed)) {
                args = parsed.map(a => String(a).trim()).filter(a => a);
              }
            } catch (e) {
              args = config.args.trim().split(/\s+/).filter(a => a);
            }
          } else if (Array.isArray(config.args)) {
            args = config.args.map(a => String(a).trim()).filter(a => a);
          }
        }

        // 解析 env
        let env = {};
        if (config.env) {
          if (typeof config.env === 'string') {
            try {
              const parsed = JSON.parse(config.env);
              if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                env = parsed;
              }
            } catch (e) {
              env = {};
            }
          } else if (config.env && typeof config.env === 'object' && !Array.isArray(config.env)) {
            env = config.env;
          }
        }

        if (serverType === 'http') {
          const serverEntry = {
            url: command
          };
          if (args.length > 0) {
            serverEntry.args = args;
          }
          if (Object.keys(env).length > 0) {
            serverEntry.env = env;
          }
          httpServers[serverAlias] = serverEntry;
        } else {
          let cwd = config.cwd;

          // 读取激活的配置档案并覆盖 args/env/cwd
          try {
            const activeProfile = db.fetchoneSync(
              'SELECT * FROM mcp_config_profiles WHERE mcp_config_id = ? AND enabled = 1',
              [config.id]
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
                  logger.info(`[AGENT] 从档案加载 env: ${JSON.stringify(env)}`);
                }
              }

              // 档案的 cwd
              if (activeProfile.cwd) {
                cwd = activeProfile.cwd;
              }

              logger.info(`[AGENT] 应用配置档案: ${activeProfile.name} (id=${activeProfile.id}), env keys: ${Object.keys(env).join(', ')}`);
            }
          } catch (e) {
            logger.warn(`[AGENT] 加载配置档案失败: ${e.message}`);
          }

          const serverEntry = {
            command
          };
          if (args.length > 0) {
            serverEntry.args = args;
          }
          if (Object.keys(env).length > 0) {
            serverEntry.env = env;
          }
          if (cwd) {
            serverEntry.cwd = cwd;
          }

          stdioServers[serverAlias] = serverEntry;
        }
      }

      logger.info(`[AGENT] 加载 MCP 配置完成: HTTP ${Object.keys(httpServers).length} 个, STDIO ${Object.keys(stdioServers).length} 个 (user_id=${userId})`);

      return { httpServers, stdioServers };
    } catch (error) {
      logger.error(`[AGENT] 加载 MCP 配置失败: ${error.message}`);
      return { httpServers: {}, stdioServers: {} };
    }
  }

  /**
   * 运行 Agent，处理消息并返回结果
   */
  async run(messages, options = {}) {
    const {
      session_id = null,
      tools = null,
      use_tools = true,
      on_chunk = null,
      on_thinking_chunk = null,
      on_tools_start = null,
      on_tools_stream = null,
      on_tools_end = null,
      model_name = null,
      temperature = null,
      max_tokens = null
    } = options;

    try {
      // 生成会话 ID
      const sessionId = session_id || `agent_session_${Date.now()}`;

      logger.info(`[AGENT] 开始运行 - 会话ID: ${sessionId}, 消息数: ${messages.length}`);

      // 准备消息列表
      const preparedMessages = this._prepareMessages(messages);

      // 使用参数或配置中的值
      const actualModel = model_name || this.config.model_name;
      const actualTemperature = temperature !== null ? temperature : this.config.temperature;
      const actualMaxTokens = max_tokens || this.config.max_tokens;

      // 确定使用的工具
      let actualTools = null;
      if (use_tools) {
        actualTools = tools || this.mcpToolExecute.getAvailableTools();
      }

      logger.info(`[AGENT] 配置 - 模型: ${actualModel}, 温度: ${actualTemperature}, 工具数: ${actualTools ? actualTools.length : 0}`);

      // 如果没有工具，直接调用 AI
      if (!actualTools || actualTools.length === 0) {
        return await this._runWithoutTools(
          preparedMessages,
          sessionId,
          actualModel,
          actualTemperature,
          actualMaxTokens,
          on_chunk,
          on_thinking_chunk
        );
      }

      // 使用工具执行
      const result = await this.aiClient.processRequest(preparedMessages, sessionId, {
        model: actualModel,
        temperature: actualTemperature,
        maxTokens: actualMaxTokens,
        onChunk: on_chunk,
        onThinkingChunk: on_thinking_chunk,
        onToolsStart: on_tools_start,
        onToolsStream: on_tools_stream,
        onToolsEnd: on_tools_end
      });

      logger.info(`[AGENT] 运行完成 - 会话ID: ${sessionId}, 成功: ${result.success}`);

      return result;
    } catch (error) {
      const errorMessage = `Agent 运行失败: ${error.message}`;
      logger.error(`[AGENT] 错误: ${errorMessage}`, error);
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 简化的聊天接口
   */
  async chat(userMessage, options = {}) {
    const {
      session_id = null,
      conversation_history = null,
      ...kwargs
    } = options;

    // 生成会话 ID
    const sessionId = session_id || `agent_session_${Date.now()}`;

    // 保存用户消息到数据库
    try {
      this.messageManager.saveUserMessage(sessionId, userMessage);
    } catch (error) {
      logger.warn('保存用户消息失败，但继续执行聊天流程', error);
    }

    // 构建消息列表
    const messages = conversation_history || [];
    messages.push({ role: 'user', content: userMessage });

    return await this.run(messages, { session_id: sessionId, ...kwargs });
  }

  /**
   * 准备消息列表，添加系统提示词
   */
  _prepareMessages(messages) {
    const prepared = [];

    // 添加系统提示词（如果配置了）
    if (this.config.system_prompt) {
      prepared.push({ role: 'system', content: this.config.system_prompt });
    }

    // 添加其他消息
    prepared.push(...messages);

    return prepared;
  }

  /**
   * 不使用工具的简单执行
   */
  async _runWithoutTools(messages, sessionId, model, temperature, maxTokens, onChunk, onThinkingChunk) {
    try {
      logger.info(`[AGENT] 无工具模式运行 - 会话ID: ${sessionId}`);

      const response = await this.aiRequestHandler.handleRequest(messages, {
        tools: null,
        model,
        temperature,
        maxTokens,
        onChunk,
        onThinkingChunk
      });

      return {
        success: true,
        content: response.content,
        reasoning: response.reasoning,
        finish_reason: response.finish_reason,
        iteration: 1,
        has_tool_calls: false
      };
    } catch (error) {
      const errorMessage = `无工具执行失败: ${error.message}`;
      logger.error(`[AGENT] 错误: ${errorMessage}`, error);
      return {
        success: false,
        error: errorMessage
      };
    }
  }

  /**
   * 获取可用工具列表
   */
  getAvailableTools() {
    return this.mcpToolExecute.getAvailableTools();
  }

  /**
   * 获取对话历史
   */
  async getConversationHistory(sessionId, limit = null) {
    return await this.messageManager.getSessionMessages(sessionId, limit);
  }
}

/**
 * 创建 Agent 的便捷函数
 */
export function createAgent(options = {}) {
  const config = new AgentConfig(options);
  return new Agent(config);
}

/**
 * 构建 SSE 流式响应的异步生成器
 * 封装 Agent 的流式响应逻辑，减少路由层样板代码
 *
 * @param {string} sessionId - 会话 ID
 * @param {string} content - 用户消息内容
 * @param {Object} modelConfig - 模型配置
 * @param {string} userId - 用户 ID（可选）
 * @returns {AsyncGenerator<string>} SSE 事件流
 */
export async function* buildSseStream(sessionId, content, modelConfig = {}, userId = null) {
  try {
    const apiKey = modelConfig.api_key || process.env.OPENAI_API_KEY || '';
    const baseUrl = modelConfig.base_url || process.env.OPENAI_BASE_URL;

    // 计算系统提示词
    let effectiveSystemPrompt = modelConfig.system_prompt || null;

    // TODO: 支持根据 user_id 加载激活的系统上下文
    // 这里可以查询 system_contexts 表获取用户激活的系统上下文

    // 创建 Agent
    const agent = createAgent({
      api_key: apiKey,
      base_url: baseUrl,
      model_name: modelConfig.model_name || 'gpt-4',
      system_prompt: effectiveSystemPrompt,
      temperature: modelConfig.temperature !== undefined ? modelConfig.temperature : 0.7,
      max_tokens: modelConfig.max_tokens,
      user_id: userId
    });

    // 初始化 Agent
    await agent.init();

    // 事件队列
    const eventQueue = [];
    let resolveWait = null;
    let aiCompleted = false;
    let aiError = null;
    let aiResult = null;

    // 添加事件到队列
    const pushEvent = (type, data) => {
      eventQueue.push({ type, data });
      if (resolveWait) {
        resolveWait();
        resolveWait = null;
      }
    };

    // 等待事件
    const waitForEvent = () => {
      return new Promise(resolve => {
        if (eventQueue.length > 0 || aiCompleted) {
          resolve();
        } else {
          resolveWait = resolve;
        }
      });
    };

    // 定义回调函数
    const onChunk = (chunk) => {
      pushEvent('chunk', chunk);
    };

    const onThinkingChunk = (text) => {
      pushEvent('thinking', text);
    };

    const onToolsStart = (toolCalls) => {
      pushEvent('tools_start', { tool_calls: toolCalls });
    };

    const onToolsStream = (result) => {
      pushEvent('tools_stream', result);
    };

    const onToolsEnd = (toolResults) => {
      pushEvent('tools_end', { tool_results: toolResults });
    };

    // 启动 AI 处理（异步）
    const aiPromise = (async () => {
      try {
        const model = modelConfig.model_name || 'gpt-4';
        const temperature = modelConfig.temperature !== undefined ? modelConfig.temperature : 0.7;
        const maxTokens = modelConfig.max_tokens || null;
        const useTools = modelConfig.use_tools !== false;

        aiResult = await agent.chat(content, {
          session_id: sessionId,
          model_name: model,
          temperature,
          max_tokens: maxTokens,
          use_tools: useTools,
          on_chunk: onChunk,
          on_thinking_chunk: onThinkingChunk,
          on_tools_start: onToolsStart,
          on_tools_stream: onToolsStream,
          on_tools_end: onToolsEnd
        });
      } catch (error) {
        aiError = error;
        logger.error(`[SSE_STREAM] AI 处理错误: ${error.message}`, error);
      } finally {
        aiCompleted = true;
        pushEvent('ai_completed', null);
      }
    })();

    // 发送 start 事件
    const startEvent = {
      type: 'start',
      session_id: sessionId,
      timestamp: new Date().toISOString()
    };
    yield `data: ${JSON.stringify(startEvent)}\n\n`;

    // 主循环：处理事件队列
    let completed = false;
    let lastHeartbeat = Date.now();
    const heartbeatInterval = 30000; // 30 秒

    while (!completed) {
      // 等待事件或超时
      const timeoutPromise = new Promise(resolve => setTimeout(resolve, 2000));
      await Promise.race([waitForEvent(), timeoutPromise]);

      // 处理队列中的所有事件
      while (eventQueue.length > 0) {
        const event = eventQueue.shift();
        const eventData = {
          timestamp: new Date().toISOString()
        };

        switch (event.type) {
          case 'chunk':
            eventData.type = 'chunk';
            eventData.content = event.data;
            yield `data: ${JSON.stringify(eventData)}\n\n`;
            break;

          case 'thinking':
            eventData.type = 'thinking';
            eventData.content = event.data;
            yield `data: ${JSON.stringify(eventData)}\n\n`;
            break;

          case 'tools_start':
            eventData.type = 'tools_start';
            eventData.data = event.data;
            yield `data: ${JSON.stringify(eventData)}\n\n`;
            break;

          case 'tools_stream':
            eventData.type = 'tools_stream';
            eventData.data = event.data;
            yield `data: ${JSON.stringify(eventData)}\n\n`;
            break;

          case 'tools_end':
            eventData.type = 'tools_end';
            eventData.data = event.data;
            yield `data: ${JSON.stringify(eventData)}\n\n`;
            break;

          case 'ai_completed':
            completed = true;
            break;
        }
      }

      // 检查是否需要发送心跳
      if (!completed && eventQueue.length === 0) {
        const now = Date.now();
        if (now - lastHeartbeat > heartbeatInterval) {
          const heartbeat = {
            type: 'heartbeat',
            timestamp: new Date().toISOString()
          };
          yield `data: ${JSON.stringify(heartbeat)}\n\n`;
          lastHeartbeat = now;
        }

        // 检查 AI 是否已完成
        if (aiCompleted) {
          completed = true;
        }
      }
    }

    // 等待 AI Promise 完成
    await aiPromise;

    // 发送最终事件
    if (aiError) {
      const errorEvent = {
        type: 'error',
        error: aiError.message,
        timestamp: new Date().toISOString()
      };
      yield `data: ${JSON.stringify(errorEvent)}\n\n`;
    } else {
      const completeEvent = {
        type: 'complete',
        result: aiResult,
        timestamp: new Date().toISOString()
      };
      yield `data: ${JSON.stringify(completeEvent)}\n\n`;
    }

  } catch (error) {
    logger.error(`[SSE_STREAM] 创建流响应错误: ${error.message}`, error);
    const errorEvent = {
      type: 'error',
      error: error.message,
      timestamp: new Date().toISOString()
    };
    yield `data: ${JSON.stringify(errorEvent)}\n\n`;
  }
}

/**
 * 根据 agent_id 加载模型配置
 *
 * @param {string} agentId - 智能体 ID
 * @returns {Object} 模型配置
 */
export async function loadModelConfigForAgent(agentId) {
  try {
    const db = getDatabaseSync();

    // 查询智能体配置
    const agent = db.fetchoneSync(
      'SELECT * FROM agents WHERE id = ? AND enabled = 1',
      [agentId]
    );

    if (!agent) {
      throw new Error('智能体不存在或未启用');
    }

    const aiModelId = agent.ai_model_config_id;
    if (!aiModelId) {
      throw new Error('智能体缺少模型配置');
    }

    // 查询模型配置
    const modelCfg = db.fetchoneSync(
      'SELECT * FROM ai_model_configs WHERE id = ? AND enabled = 1',
      [aiModelId]
    );

    if (!modelCfg) {
      throw new Error('模型配置不可用或未启用');
    }

    // 获取系统提示词
    let systemPrompt = null;
    const systemContextId = agent.system_context_id;
    if (systemContextId) {
      const sc = db.fetchoneSync(
        'SELECT * FROM system_contexts WHERE id = ?',
        [systemContextId]
      );
      if (sc) {
        const isActive = sc.is_active !== undefined ? sc.is_active : (sc.isActive !== undefined ? sc.isActive : true);
        if (isActive) {
          systemPrompt = sc.content;
        }
      }
    }

    return {
      model_name: modelCfg.model,
      api_key: modelCfg.api_key,
      base_url: modelCfg.base_url,
      temperature: 0.7,
      max_tokens: 4000,
      system_prompt: systemPrompt
    };
  } catch (error) {
    logger.error(`[AGENT] 加载 agent 模型配置失败: ${error.message}`);
    throw error;
  }
}

/**
 * 根据 agent_id 构建 SSE 流
 *
 * @param {string} sessionId - 会话 ID
 * @param {string} content - 用户消息内容
 * @param {string} agentId - 智能体 ID
 * @param {string} userId - 用户 ID（可选）
 * @returns {AsyncGenerator<string>} SSE 事件流
 */
export async function* buildSseStreamFromAgentId(sessionId, content, agentId, userId = null) {
  const modelConfig = await loadModelConfigForAgent(agentId);
  yield* buildSseStream(sessionId, content, modelConfig, userId);
}
