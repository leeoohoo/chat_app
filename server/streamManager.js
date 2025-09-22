// 流式会话管理器
// 管理正在进行的流式输出，支持按会话ID中断

class StreamManager {
  constructor() {
    // 存储正在进行的流式会话
    // key: sessionId, value: { response, abortController, startTime, metadata }
    this.activeStreams = new Map();
  }

  /**
   * 注册一个新的流式会话
   * @param {string} sessionId - 会话ID
   * @param {object} response - Express响应对象
   * @param {AbortController} abortController - 中断控制器
   * @param {object} metadata - 额外的元数据
   */
  registerStream(sessionId, response, abortController, metadata = {}) {
    console.log(`📡 StreamManager: 注册流式会话 ${sessionId}`);
    
    const streamInfo = {
      response,
      abortController,
      startTime: Date.now(),
      metadata: {
        ...metadata,
        userAgent: response.req?.headers['user-agent'],
        ip: response.req?.ip
      }
    };

    this.activeStreams.set(sessionId, streamInfo);
    
    // 监听响应结束事件，自动清理
    response.on('close', () => {
      console.log(`🔌 StreamManager: 响应连接关闭 ${sessionId}`);
      this.unregisterStream(sessionId);
    });
    
    response.on('finish', () => {
      console.log(`🔌 StreamManager: 响应完成 ${sessionId}`);
      this.unregisterStream(sessionId);
    });

    response.on('error', (error) => {
      console.log(`🔌 StreamManager: 响应错误 ${sessionId}:`, error.message);
      this.unregisterStream(sessionId);
    });

    // 只监听响应相关事件，避免误判正常请求

    console.log(`📡 StreamManager: 当前活跃流式会话数量: ${this.activeStreams.size}`);
  }

  /**
   * 注销流式会话
   * @param {string} sessionId - 会话ID
   */
  unregisterStream(sessionId) {
    if (this.activeStreams.has(sessionId)) {
      const streamInfo = this.activeStreams.get(sessionId);
      
      // 移除所有事件监听器，防止重复触发
      if (streamInfo && streamInfo.response) {
        streamInfo.response.removeAllListeners('close');
        streamInfo.response.removeAllListeners('finish');
        streamInfo.response.removeAllListeners('error');
      }
      
      console.log(`📡 StreamManager: 注销流式会话 ${sessionId}`);
      this.activeStreams.delete(sessionId);
      console.log(`📡 StreamManager: 当前活跃流式会话数量: ${this.activeStreams.size}`);
    }
  }

  /**
   * 中断指定会话的流式输出
   * @param {string} sessionId - 会话ID
   * @returns {boolean} - 是否成功中断
   */
  abortStream(sessionId) {
    const streamInfo = this.activeStreams.get(sessionId);
    
    if (!streamInfo) {
      console.log(`⚠️ StreamManager: 会话 ${sessionId} 不存在或已结束`);
      return false;
    }

    console.log(`🛑 StreamManager: 强制中断流式会话 ${sessionId}`);
    
    try {
      // 立即中断AbortController
      if (streamInfo.abortController && !streamInfo.abortController.signal.aborted) {
        streamInfo.abortController.abort();
      }

      // 直接强制关闭响应连接，不发送任何数据
      if (streamInfo.response && !streamInfo.response.destroyed) {
        streamInfo.response.destroy();
        console.log(`🛑 StreamManager: 连接已强制断开 ${sessionId}`);
      }

      // 立即清理会话
      this.unregisterStream(sessionId);
      
      return true;
    } catch (error) {
      console.error(`❌ StreamManager: 中断会话 ${sessionId} 时出错:`, error);
      // 即使出错也要清理会话
      this.unregisterStream(sessionId);
      return false;
    }
  }

  /**
   * 获取所有活跃的流式会话
   * @returns {Array} - 活跃会话列表
   */
  getActiveStreams() {
    const streams = [];
    for (const [sessionId, streamInfo] of this.activeStreams) {
      streams.push({
        sessionId,
        startTime: streamInfo.startTime,
        duration: Date.now() - streamInfo.startTime,
        metadata: streamInfo.metadata
      });
    }
    return streams;
  }

  /**
   * 检查指定会话是否正在流式输出
   * @param {string} sessionId - 会话ID
   * @returns {boolean} - 是否正在流式输出
   */
  isStreamActive(sessionId) {
    return this.activeStreams.has(sessionId);
  }

  /**
   * 清理所有流式会话（服务器关闭时使用）
   */
  cleanup() {
    console.log(`🧹 StreamManager: 清理所有流式会话，共 ${this.activeStreams.size} 个`);
    
    for (const [sessionId, streamInfo] of this.activeStreams) {
      try {
        if (streamInfo.abortController && !streamInfo.abortController.signal.aborted) {
          streamInfo.abortController.abort();
        }
        if (streamInfo.response && !streamInfo.response.destroyed) {
          streamInfo.response.end();
        }
      } catch (error) {
        console.error(`❌ StreamManager: 清理会话 ${sessionId} 时出错:`, error);
      }
    }
    
    this.activeStreams.clear();
    console.log(`🧹 StreamManager: 清理完成`);
  }
}

// 创建全局实例
const streamManager = new StreamManager();

// 优雅关闭处理
process.on('SIGINT', () => {
  console.log('🔄 收到SIGINT信号，正在清理流式会话...');
  streamManager.cleanup();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('🔄 收到SIGTERM信号，正在清理流式会话...');
  streamManager.cleanup();
  process.exit(0);
});

export default streamManager;