// AI 请求代理模块
// 使用 OpenAI SDK 处理请求

import OpenAI from 'openai';
import streamManager from './streamManager.js';

/**
 * 通用 AI API 代理处理器
 * 使用 OpenAI SDK 处理请求，支持多种 AI 服务提供商
 * 支持两种模式:
 * 1. OpenAI客户端模式: 使用Authorization头部和x-target-url头部
 * 2. 自定义头部模式: 使用x-base-url和x-api-key头部
 */
export async function handleChatProxy(req, res) {
  try {
    const { messages, model = 'gpt-3.5-turbo', stream = true, sessionId } = req.body;
    
    // 生成会话ID（如果没有提供）
    const currentSessionId = sessionId || uuidv4();
    
    console.log('🤖 通用AI代理请求:', {
      method: req.method,
      headers: {
        'content-type': req.headers['content-type'],
        'user-agent': req.headers['user-agent'],
        'authorization': req.headers['authorization'] ? 'Present' : 'Missing',
        'x-target-url': req.headers['x-target-url'] ? 'Present' : 'Missing',
        'x-base-url': req.headers['x-base-url'] ? 'Present' : 'Missing',
        'x-api-key': req.headers['x-api-key'] ? 'Present' : 'Missing'
      }
    });

    let baseURL, apiKey;

    // 模式1: OpenAI客户端模式 (优先)
    if (req.headers['authorization'] && req.headers['x-target-url']) {
      baseURL = req.headers['x-target-url'];
      apiKey = req.headers['authorization'].replace('Bearer ', '');
      console.log('🔧 使用OpenAI客户端模式');
    }
    // 模式2: 自定义头部模式
    else if (req.headers['x-base-url'] && req.headers['x-api-key']) {
      baseURL = req.headers['x-base-url'];
      apiKey = req.headers['x-api-key'];
      console.log('🔧 使用自定义头部模式');
    }
    // 模式3: 直接从Authorization头部提取，使用默认目标URL
    else if (req.headers['authorization']) {
      baseURL = process.env.DEFAULT_TARGET_URL || 'https://api.openai.com/v1';
      apiKey = req.headers['authorization'].replace('Bearer ', '');
      console.log('🔧 使用默认目标URL模式:', baseURL);
    }
    else {
      return res.status(400).json({
        error: '缺少必需的认证信息。请提供以下任一组合:\n' +
               '1. Authorization + x-target-url 头部\n' +
               '2. x-base-url + x-api-key 头部\n' +
               '3. 仅 Authorization 头部（使用默认目标）',
        code: 'MISSING_AUTH_INFO'
      });
    }

    console.log('🚀 使用OpenAI SDK请求:', baseURL);
    
    // 创建 OpenAI 客户端
    const openai = new OpenAI({
      apiKey: apiKey,
      baseURL: baseURL
    });

    // 检查是否是流式请求
    const isStreamRequest = req.body.stream === true;
    
    if (isStreamRequest) {
      console.log(`📡 处理流式请求，会话ID: ${currentSessionId}`);
      
      // 设置流式响应头
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Headers', '*');
      res.setHeader('X-Session-Id', currentSessionId); // 返回会话ID给前端
      
      // 创建AbortController用于中断控制
      const abortController = new AbortController();
      
      // 只在响应被销毁时检测客户端断开
      res.on('close', () => {
        console.log(`🔌 StreamManager: 响应连接关闭 ${currentSessionId}`);
        if (!abortController.signal.aborted) {
          abortController.abort();
        }
      });

      // 注册到流式会话管理器
      streamManager.registerStream(currentSessionId, res, abortController, {
        model: req.body.model,
        messageCount: req.body.messages?.length || 0,
        userAgent: req.headers['user-agent']
      });
      
      try {
        // 使用 OpenAI SDK 发送流式请求
        const stream = await openai.chat.completions.create({
          ...req.body,
          stream: true
        }, {
          signal: abortController.signal // 传入中断信号
        });

        // 转发流式响应
        for await (const chunk of stream) {
          // 检查是否被中断或客户端断开
          if (abortController.signal.aborted || res.destroyed) {
            console.log(`🛑 流式请求被中断，会话ID: ${currentSessionId}`);
            break;
          }
          
          const data = `data: ${JSON.stringify(chunk)}\n\n`;
          try {
            res.write(data);
          } catch (writeError) {
            console.log(`🔌 写入响应失败，客户端可能已断开，会话ID: ${currentSessionId}`);
            if (!abortController.signal.aborted) {
              abortController.abort();
            }
            break;
          }
        }
        
        // 只有在没有被中断且连接正常的情况下才发送完成信号
        if (!abortController.signal.aborted && !res.destroyed && res.writable) {
          try {
            res.write('data: [DONE]\n\n');
            res.end();
            console.log(`✅ 流式请求处理完成，会话ID: ${currentSessionId}`);
          } catch (endError) {
            console.log(`🔌 发送完成信号失败，客户端可能已断开，会话ID: ${currentSessionId}`);
          }
        } else {
          console.log(`🔌 跳过发送完成信号，连接状态异常，会话ID: ${currentSessionId}`);
        }
        
      } catch (error) {
        console.error(`❌ 流式请求处理失败，会话ID: ${currentSessionId}`, error);
        
        // 检查是否是中断导致的错误
        if (abortController.signal.aborted) {
          console.log(`🛑 流式请求被用户中断，会话ID: ${currentSessionId}`);
          // 用户中断时不发送任何数据，直接结束
        } else {
          if (!res.destroyed) {
            res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
            res.end();
          }
        }
      } finally {
        // 确保会话被清理
        streamManager.unregisterStream(currentSessionId);
      }
    } else {
      console.log('📡 处理非流式请求');
      
      try {
        // 使用 OpenAI SDK 发送非流式请求
        const response = await openai.chat.completions.create({
          ...req.body,
          stream: false
        });

        console.log('✅ AI代理请求成功，返回JSON数据');
        res.json(response);
        
      } catch (error) {
        console.error('❌ API 错误响应:', error);
        
        // 处理 OpenAI SDK 错误
        if (error.status) {
          res.status(error.status).json({
            error: error.message,
            code: error.code || 'API_ERROR',
            type: error.type
          });
        } else {
          res.status(500).json({
            error: '请求处理失败',
            code: 'INTERNAL_ERROR',
            details: error.message
          });
        }
      }
    }
    
  } catch (error) {
    console.error('❌ AI代理请求失败:', error);
    
    // 区分不同类型的错误
    if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
      return res.status(503).json({
        error: '无法连接到目标API服务',
        code: 'CONNECTION_ERROR',
        details: error.message
      });
    }
    
    if (error.name === 'AbortError') {
      return res.status(408).json({
        error: '请求超时',
        code: 'TIMEOUT_ERROR',
        details: error.message
      });
    }
    
    if (error.name === 'TypeError' && error.message.includes('Invalid URL')) {
      return res.status(400).json({
        error: '无效的目标URL',
        code: 'INVALID_URL',
        details: error.message
      });
    }
    
    // 通用错误处理
    res.status(500).json({
      error: '代理服务器内部错误',
      code: 'INTERNAL_ERROR',
      details: error.message
    });
  }
}

/**
 * 健康检查处理器
 */
export function handleHealthCheck(req, res) {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    proxy: {
      type: '通用AI API代理',
      description: '支持转发任意AI API请求，兼容OpenAI客户端',
      supported_modes: [
        {
          name: 'OpenAI客户端模式',
          description: '直接兼容OpenAI JavaScript/Python客户端',
          usage: {
            baseURL: 'http://localhost:3001/api/chat',
            headers: {
              'x-target-url': '实际的AI API端点URL'
            },
            example: `
// JavaScript示例
const openai = new OpenAI({
  apiKey: 'your-api-key',
  baseURL: 'http://localhost:3001/api/chat',
  defaultHeaders: {
    'x-target-url': 'https://api.openai.com/v1/chat/completions'
  }
});`
          }
        },
        {
          name: '自定义头部模式',
          description: '使用自定义头部进行配置',
          usage: {
            endpoint: '/api/chat',
            method: 'POST (或其他HTTP方法)',
            required_headers: {
              'x-base-url': '目标API的完整URL',
              'x-api-key': 'API密钥'
            },
            example: {
              headers: {
                'Content-Type': 'application/json',
                'x-base-url': 'https://api.openai.com/v1/chat/completions',
                'x-api-key': 'your-api-key-here'
              }
            }
          }
        },
        {
          name: '默认目标模式',
          description: '仅提供Authorization头部，使用默认目标URL',
          usage: {
            endpoint: '/api/chat',
            method: 'POST',
            required_headers: {
              'Authorization': 'Bearer your-api-key'
            },
            note: '使用环境变量 DEFAULT_TARGET_URL 或默认的 OpenAI API'
          }
        }
      ]
    }
  });
}