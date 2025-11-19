/**
 * 主应用入口 - Express 服务器
 * 复刻自 Python: app/main.py
 */

import express from 'express';
import cors from 'cors';
import { config } from './utils/config.js';
import { logger } from './utils/logger.js';
import { getDatabase } from './models/database-factory.js';

// 导入路由
import sessionsRouter from './api/sessions.js';
import messagesRouter from './api/messages.js';
import chatV2Router from './api/chat-v2.js';
import agentsRouter from './api/agents.js';
import applicationsRouter from './api/applications.js';
import configsRouter from './api/configs.js';
import chatAgentV2Router from './api/chat-agent-v2.js';

// 计时器
const startTime = Date.now();

const logStep = (step) => {
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
  console.log(`[${elapsed}s] ${step}`);
};

logStep('程序开始启动');

// 创建 Express 应用
const app = express();

// 中间件
app.use(cors({
  origin: config.CORS_ORIGINS,
  credentials: true
}));

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// 性能监控中间件
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info(`[perf] ${req.method} ${req.path} -> ${duration}ms`);
  });

  next();
});

// 注册路由
app.use('/api/sessions', sessionsRouter);
app.use('/api/messages', messagesRouter);
app.use('/api', chatV2Router);
app.use('/api/agents', agentsRouter);
app.use('/api/applications', applicationsRouter);
app.use('/api', configsRouter);
app.use('/api/v2', chatAgentV2Router);

logStep('路由注册完成');

// 健康检查端点
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// 根路径
app.get('/', (req, res) => {
  res.json({
    name: 'Chat App Node Server',
    version: '1.0.0',
    description: 'Node.js 聊天应用服务器 - 完全复刻自 Python FastAPI 版本',
    endpoints: {
      health: '/health',
      sessions: '/api/sessions',
      messages: '/api/messages'
    }
  });
});

// 错误处理中间件
app.use((err, req, res, next) => {
  logger.error('未处理的错误:', err);

  res.status(err.status || 500).json({
    error: {
      message: err.message || '服务器内部错误',
      ...(config.NODE_ENV === 'development' && { stack: err.stack })
    }
  });
});

// 404 处理
app.use((req, res) => {
  res.status(404).json({
    error: {
      message: '请求的资源不存在',
      path: req.path
    }
  });
});

/**
 * 启动服务器
 */
async function startServer() {
  try {
    logStep('开始初始化数据库');

    // 初始化数据库
    const db = await getDatabase();
    logger.info('数据库初始化完成');

    logStep('数据库初始化完成');

    // 打印配置信息
    config.print();

    // 启动服务器
    const server = app.listen(config.PORT, config.HOST, () => {
      logStep('程序启动完成');
      logger.info(`服务器运行在 http://${config.HOST}:${config.PORT}`);
      logger.info(`健康检查: http://${config.HOST}:${config.PORT}/health`);
      logger.info(`环境: ${config.NODE_ENV}`);
    });

    // 优雅关闭
    const gracefulShutdown = async (signal) => {
      logger.info(`收到 ${signal} 信号，开始优雅关闭...`);

      server.close(async () => {
        logger.info('HTTP 服务器已关闭');

        try {
          await db.close();
          logger.info('数据库连接已关闭');
          process.exit(0);
        } catch (err) {
          logger.error('关闭数据库连接时出错:', err);
          process.exit(1);
        }
      });

      // 强制关闭超时
      setTimeout(() => {
        logger.error('强制关闭服务器（超时）');
        process.exit(1);
      }, 10000);
    };

    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  } catch (error) {
    logger.error('启动服务器失败:', error);
    process.exit(1);
  }
}

// 启动服务器
startServer();

export default app;
