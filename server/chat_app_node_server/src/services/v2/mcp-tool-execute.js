/**
 * MCP 工具执行器 - 使用 @modelcontextprotocol/sdk
 * 完全复刻自 Python: app/services/v2/mcp_tool_execute.py
 *
 * 支持：
 * - HTTP MCP 服务器
 * - STDIO MCP 服务器
 * - 工具列表构建（带服务器前缀）
 * - 工具执行（同步和异步）
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { spawn } from 'child_process';
import { logger } from '../../utils/logger.js';

/**
 * 提取 MCP 返回结果中的文本内容
 */
function toText(result) {
  try {
    // 兼容不同版本的 MCP SDK 返回格式
    if (typeof result === 'string') {
      return result;
    }

    // 检查 content 数组
    if (result.content && Array.isArray(result.content)) {
      const textContent = result.content.find(c => c.type === 'text');
      if (textContent) {
        return textContent.text || textContent.value || '';
      }
    }

    // 检查 text 属性
    if (result.text) {
      return typeof result.text === 'function' ? result.text() : result.text;
    }

    // 检查 value 属性
    if (result.value) {
      return result.value;
    }

    // 最后尝试 JSON 序列化
    return JSON.stringify(result);
  } catch (error) {
    logger.error('提取文本内容失败:', error);
    return String(result);
  }
}

/**
 * MCP 工具执行器类
 */
export class McpToolExecute {
  constructor(options = {}) {
    this.mcp_servers = options.mcp_servers || [];           // HTTP 服务器列表
    this.stdio_mcp_servers = options.stdio_mcp_servers || []; // STDIO 服务器列表
    this.config_dir = options.config_dir || null;

    this.tools = [];                    // OpenAI 格式的工具列表
    this.tool_metadata = new Map();     // 工具元数据映射
    this.active_clients = new Map();    // 活跃的客户端连接
  }

  /**
   * 初始化并构建工具列表
   */
  async init() {
    await this.buildTools();
  }

  /**
   * 构建工具列表（支持 HTTP 和 STDIO）
   */
  async buildTools() {
    try {
      this.tools = [];
      this.tool_metadata.clear();

      // 1. 处理 HTTP 服务器
      for (const mcpServer of this.mcp_servers) {
        const serverName = mcpServer.name;
        const serverUrl = mcpServer.url;

        if (!serverName || !serverUrl) {
          logger.warn(`跳过无效的 HTTP 服务器配置: ${JSON.stringify(mcpServer)}`);
          continue;
        }

        try {
          await this._buildToolsFromHttpServer(serverName, serverUrl);
        } catch (error) {
          logger.error(`构建 HTTP 服务器工具失败 (${serverName}):`, error);
        }
      }

      // 2. 处理 STDIO 服务器
      for (const stdioServer of this.stdio_mcp_servers) {
        const serverName = stdioServer.name;

        if (!serverName || !stdioServer.command) {
          logger.warn(`跳过无效的 STDIO 服务器配置: ${JSON.stringify(stdioServer)}`);
          continue;
        }

        try {
          await this._buildToolsFromStdioServer(serverName, stdioServer);
        } catch (error) {
          logger.error(`构建 STDIO 服务器工具失败 (${serverName}):`, error);
        }
      }

      logger.info(`MCP 工具构建完成，共 ${this.tools.length} 个工具`);
    } catch (error) {
      logger.error('构建工具列表失败:', error);
      this.tools = [];
    }
  }

  /**
   * 从 HTTP 服务器构建工具
   */
  async _buildToolsFromHttpServer(serverName, serverUrl) {
    let transport;
    let client;
    let transportType = 'streamable'; // 默认尝试 StreamableHTTP

    // 先尝试 StreamableHTTP，失败则回退到 SSE
    try {
      transport = new StreamableHTTPClientTransport(new URL(serverUrl));
      client = new Client({
        name: `mcp-client-${serverName}`,
        version: '1.0.0'
      }, {
        capabilities: {}
      });
      await client.connect(transport);
      logger.info(`使用 StreamableHTTP 连接到 ${serverName}`);
    } catch (streamableError) {
      logger.warn(`StreamableHTTP 连接失败，尝试 SSE: ${streamableError.message}`);

      // 回退到 SSE
      try {
        transport = new SSEClientTransport(new URL(serverUrl));
        client = new Client({
          name: `mcp-client-${serverName}`,
          version: '1.0.0'
        }, {
          capabilities: {}
        });
        await client.connect(transport);
        transportType = 'sse';
        logger.info(`使用 SSE 连接到 ${serverName}`);
      } catch (sseError) {
        throw new Error(`无法连接到 HTTP 服务器 ${serverName}: StreamableHTTP(${streamableError.message}), SSE(${sseError.message})`);
      }
    }

    try {
      // 列出工具
      const { tools } = await client.listTools();

      for (const tool of tools) {
        const toolName = tool.name;
        if (!toolName) continue;

        const prefixedName = `${serverName}_${toolName}`;

        // 存储元数据（包含传输类型）
        this.tool_metadata.set(prefixedName, {
          original_name: toolName,
          server_name: serverName,
          server_url: serverUrl,
          server_type: 'http',
          transport_type: transportType,
          tool_info: tool
        });

        // 转换为 OpenAI 格式
        const openaiTool = {
          type: 'function',
          function: {
            name: prefixedName,
            description: tool.description || '',
            parameters: tool.inputSchema || {
              type: 'object',
              properties: {},
              required: []
            }
          }
        };

        this.tools.push(openaiTool);
      }

      logger.info(`从 HTTP 服务器 ${serverName} 加载了 ${tools.length} 个工具 (${transportType})`);
    } finally {
      await client.close();
    }
  }

  /**
   * 从 STDIO 服务器构建工具
   */
  async _buildToolsFromStdioServer(serverName, stdioConfig) {
    const config = this._makeStdioServerConfig(stdioConfig);
    if (!config) {
      logger.warn(`STDIO 服务器配置无效: ${serverName}`);
      return;
    }

    // 创建 STDIO 客户端传输
    const transportOptions = {
      command: config.command,
      args: config.args || [],
      env: {
        ...process.env,
        ...(config.env || {})
      }
    };

    if (config.cwd) {
      transportOptions.cwd = config.cwd;
    }

    const transport = new StdioClientTransport(transportOptions);

    const client = new Client({
      name: `mcp-client-${serverName}`,
      version: '1.0.0'
    }, {
      capabilities: {}
    });

    try {
      await client.connect(transport);

      // 列出工具
      const { tools } = await client.listTools();

      for (const tool of tools) {
        const toolName = tool.name;
        if (!toolName) continue;

        const prefixedName = `${serverName}_${toolName}`;

        // 存储元数据
        this.tool_metadata.set(prefixedName, {
          original_name: toolName,
          server_name: serverName,
          server_type: 'stdio',
          server_config: config,
          tool_info: tool
        });

        // 转换为 OpenAI 格式
        const openaiTool = {
          type: 'function',
          function: {
            name: prefixedName,
            description: tool.description || '',
            parameters: tool.inputSchema || {
              type: 'object',
              properties: {},
              required: []
            }
          }
        };

        this.tools.push(openaiTool);
      }

      logger.info(`从 STDIO 服务器 ${serverName} 加载了 ${tools.length} 个工具`);
    } finally {
      await client.close();
    }
  }

  /**
   * 规范化 STDIO 服务器配置
   */
  _makeStdioServerConfig(stdioServer) {
    const serverName = stdioServer.name;
    const command = stdioServer.command;

    if (!serverName || !command) {
      return null;
    }

    // 处理 args
    let args = [];
    if (stdioServer.args) {
      if (typeof stdioServer.args === 'string') {
        // 如果是字符串，尝试 JSON 解析
        try {
          const parsed = JSON.parse(stdioServer.args);
          if (Array.isArray(parsed)) {
            args = parsed.map(a => String(a).trim()).filter(a => a);
          }
        } catch (e) {
          // 不是 JSON，按空格分割
          args = stdioServer.args.trim().split(/\s+/).filter(a => a);
        }
      } else if (Array.isArray(stdioServer.args)) {
        args = stdioServer.args.map(a => String(a).trim()).filter(a => a);
      }
    }

    // 处理 env
    let env = {};
    if (stdioServer.env) {
      if (typeof stdioServer.env === 'string') {
        try {
          const parsed = JSON.parse(stdioServer.env);
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            env = parsed;
          }
        } catch (e) {
          env = {};
        }
      } else if (stdioServer.env && typeof stdioServer.env === 'object' && !Array.isArray(stdioServer.env)) {
        env = stdioServer.env;
      }
    }

    const config = {
      command
    };

    if (args.length > 0) {
      config.args = args;
    }
    if (stdioServer.cwd) {
      config.cwd = stdioServer.cwd;
    }
    if (env && Object.keys(env).length > 0) {
      config.env = env;
    }

    logger.info(`[MCP_TOOL] 构建 STDIO 配置: ${serverName}, command=${config.command}, args=${JSON.stringify(config.args || [])}, env keys=${Object.keys(config.env || {}).join(', ')}`);

    return config;
  }

  /**
   * 查找工具信息
   */
  findToolInfo(toolName) {
    return this.tool_metadata.get(toolName);
  }

  /**
   * 调用单个 MCP 工具
   */
  async _callMcpToolOnce(toolName, arguments_) {
    const args = arguments_ || {};

    const info = this.findToolInfo(toolName);
    if (!info) {
      throw new Error(`工具未找到: ${toolName}`);
    }

    const originalName = info.original_name;

    // 创建客户端并执行
    if (info.server_type === 'stdio') {
      const config = info.server_config;
      const transportOptions = {
        command: config.command,
        args: config.args || [],
        env: {
          ...process.env,
          ...(config.env || {})
        }
      };

      if (config.cwd) {
        transportOptions.cwd = config.cwd;
      }

      // 记录工具调用的 env 信息
      const configEnvKeys = Object.keys(config.env || {});
      logger.info(`[MCP_TOOL] 调用工具: ${toolName}, 原名: ${originalName}, config env keys: ${configEnvKeys.join(', ')}`);
      if (configEnvKeys.length > 0) {
        logger.info(`[MCP_TOOL] 传递给工具的 env: ${JSON.stringify(config.env)}`);
      }

      const transport = new StdioClientTransport(transportOptions);

      const client = new Client({
        name: `mcp-client-${info.server_name}`,
        version: '1.0.0'
      }, {
        capabilities: {}
      });

      try {
        await client.connect(transport);
        const result = await client.callTool({
          name: originalName,
          arguments: args
        });
        return toText(result);
      } finally {
        await client.close();
      }
    } else {
      // HTTP - 根据 transport_type 选择传输方式
      let transport;
      if (info.transport_type === 'sse') {
        transport = new SSEClientTransport(new URL(info.server_url));
      } else {
        transport = new StreamableHTTPClientTransport(new URL(info.server_url));
      }

      const client = new Client({
        name: `mcp-client-${info.server_name}`,
        version: '1.0.0'
      }, {
        capabilities: {}
      });

      try {
        await client.connect(transport);
        const result = await client.callTool({
          name: originalName,
          arguments: args
        });
        return toText(result);
      } finally {
        await client.close();
      }
    }
  }

  /**
   * 执行多个工具调用
   */
  async executeToolsStream(toolCalls, onToolResult = null) {
    const results = [];

    for (const toolCall of toolCalls) {
      try {
        const functionInfo = toolCall.function || {};
        const toolName = functionInfo.name;
        let argumentsStr = functionInfo.arguments || '{}';

        if (!toolName) {
          const result = {
            tool_call_id: toolCall.id || '',
            name: 'unknown',
            success: false,
            is_error: true,
            content: '工具名称不能为空'
          };
          results.push(result);
          if (onToolResult) {
            onToolResult(result);
          }
          continue;
        }

        // 解析参数
        let args;
        try {
          if (typeof argumentsStr === 'string') {
            args = argumentsStr ? JSON.parse(argumentsStr) : {};
          } else {
            args = argumentsStr;
          }
        } catch (e) {
          const result = {
            tool_call_id: toolCall.id || '',
            name: toolName,
            success: false,
            is_error: true,
            content: `参数解析失败: ${e.message}`
          };
          results.push(result);
          if (onToolResult) {
            onToolResult(result);
          }
          continue;
        }

        // 执行工具
        const text = await this._callMcpToolOnce(toolName, args);
        const finalResult = {
          tool_call_id: toolCall.id || '',
          name: toolName,
          success: true,
          is_error: false,
          content: text
        };
        results.push(finalResult);
        if (onToolResult) {
          onToolResult(finalResult);
        }
      } catch (error) {
        const errorResult = {
          tool_call_id: toolCall.id || '',
          name: toolCall.function?.name || 'unknown',
          success: false,
          is_error: true,
          content: `工具执行失败: ${error.message}`
        };
        results.push(errorResult);
        if (onToolResult) {
          onToolResult(errorResult);
        }
      }
    }

    return results;
  }

  /**
   * 执行单个工具调用
   */
  async executeSingleToolStream(toolCall, onToolStream = null) {
    try {
      const functionInfo = toolCall.function || {};
      const toolName = functionInfo.name;
      let argumentsStr = functionInfo.arguments || '{}';
      const toolCallId = toolCall.id || '';

      if (!toolName) {
        const result = {
          tool_call_id: toolCallId,
          name: 'unknown',
          success: false,
          is_error: true,
          content: '工具名称不能为空'
        };
        if (onToolStream) {
          onToolStream(result);
        }
        return result;
      }

      // 解析参数
      let args;
      try {
        if (typeof argumentsStr === 'string') {
          args = argumentsStr ? JSON.parse(argumentsStr) : {};
        } else {
          args = argumentsStr;
        }
      } catch (e) {
        const result = {
          tool_call_id: toolCallId,
          name: toolName,
          success: false,
          is_error: true,
          content: `参数解析失败: ${e.message}`
        };
        if (onToolStream) {
          onToolStream(result);
        }
        return result;
      }

      // 执行工具
      const text = await this._callMcpToolOnce(toolName, args);
      const result = {
        tool_call_id: toolCallId,
        name: toolName,
        success: true,
        is_error: false,
        content: text
      };

      if (onToolStream) {
        logger.info(`[MCP_TOOL] 工具执行成功: ${toolName} (tool_call_id=${toolCallId}), 内容长度=${text.length}`);
        onToolStream(result);
      }

      return result;
    } catch (error) {
      const errorResult = {
        tool_call_id: toolCall.id || '',
        name: toolCall.function?.name || 'unknown',
        success: false,
        is_error: true,
        content: `工具执行失败: ${error.message}`
      };

      if (onToolStream) {
        logger.error(`[MCP_TOOL] 工具执行失败: ${errorResult.name} (tool_call_id=${errorResult.tool_call_id}) - ${errorResult.content}`);
        onToolStream(errorResult);
      }

      return errorResult;
    }
  }

  /**
   * 获取可用工具列表（OpenAI 格式）
   */
  getAvailableTools() {
    return this.tools;
  }

  /**
   * 别名方法
   */
  getTools() {
    return this.tools;
  }

  /**
   * 验证工具调用
   */
  validateToolCall(toolCall) {
    try {
      const functionInfo = toolCall.function || {};
      if (!functionInfo.name) {
        throw new Error('工具名称缺失');
      }
      return { is_valid: true, error_message: null };
    } catch (error) {
      return { is_valid: false, error_message: `验证失败: ${error.message}` };
    }
  }

  /**
   * 获取工具执行统计
   */
  getToolExecutionStats(results) {
    const total = results.length;
    const success = results.filter(r => r.success).length;
    const error = total - success;

    return {
      total_count: total,
      success_count: success,
      error_count: error,
      success_rate: total > 0 ? success / total : 0
    };
  }

  /**
   * 清理资源
   */
  async cleanup() {
    // 关闭所有活跃的客户端连接
    for (const [name, client] of this.active_clients.entries()) {
      try {
        await client.close();
        logger.info(`关闭 MCP 客户端: ${name}`);
      } catch (error) {
        logger.error(`关闭 MCP 客户端失败 (${name}):`, error);
      }
    }
    this.active_clients.clear();
  }
}
