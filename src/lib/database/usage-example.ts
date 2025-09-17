// 使用示例：展示如何使用数据库适配器替代HTTP API调用

// 原来的方式 - 通过HTTP API
import { apiClient } from '../api/client';
import { conversationsApi } from '../api';

// 新的方式 - 使用适配器（自动选择HTTP API或直接数据库）
import { databaseAdapter } from './adapter';

// 示例1：获取所有会话
export async function getAllSessionsExample() {
  // 原来的方式
  const sessionsOld = await apiClient.getSessions();
  
  // 新的方式 - 自动根据环境选择
  const sessionsNew = await databaseAdapter.getAllSessions();
  
  console.log('原方式获取的会话:', sessionsOld);
  console.log('新方式获取的会话:', sessionsNew);
}

// 示例2：创建新会话
export async function createSessionExample() {
  const sessionData = {
    id: `session_${Date.now()}`,
    title: '新的聊天会话'
  };
  
  // 原来的方式
  const sessionOld = await apiClient.createSession(sessionData);
  
  // 新的方式
  const sessionNew = await databaseAdapter.createSession(sessionData.id, sessionData.title);
  
  console.log('原方式创建的会话:', sessionOld);
  console.log('新方式创建的会话:', sessionNew);
}

// 示例3：获取会话消息
export async function getSessionMessagesExample(sessionId: string) {
  // 原来的方式
  const messagesOld = await conversationsApi.getMessages(sessionId, {});
  
  // 新的方式
  const messagesNew = await databaseAdapter.getSessionMessages(sessionId);
  
  console.log('原方式获取的消息:', messagesOld);
  console.log('新方式获取的消息:', messagesNew);
}

// 示例4：创建消息
export async function createMessageExample(sessionId: string) {
  const messageData = {
    id: `msg_${Date.now()}`,
    session_id: sessionId,
    role: 'user',
    content: '这是一条测试消息',
    metadata: JSON.stringify({ timestamp: Date.now() })
  };
  
  // 原来的方式
  const messageOld = await conversationsApi.saveMessage(sessionId, {
    ...messageData,
    sessionId: messageData.session_id,
    metadata: JSON.parse(messageData.metadata)
  });
  
  // 新的方式
  const messageNew = await databaseAdapter.createMessage(messageData);
  
  console.log('原方式创建的消息:', messageOld);
  console.log('新方式创建的消息:', messageNew);
}

// 示例5：在不同环境中的使用
export function environmentExample() {
  // 检测当前环境
  const isServer = typeof window === 'undefined';
  const isElectron = typeof window !== 'undefined' && (window as any).electronAPI;
  const isBrowser = typeof window !== 'undefined' && !(window as any).electronAPI;
  
  console.log('当前环境:', {
    isServer,
    isElectron,
    isBrowser
  });
  
  if (isServer || isElectron) {
    console.log('将使用直接数据库访问模式');
    // 在这种环境下，databaseAdapter 会自动使用 DirectDatabaseAdapter
    // 直接访问 SQLite 数据库，无需HTTP请求
  } else {
    console.log('将使用HTTP API访问模式');
    // 在浏览器环境下，databaseAdapter 会使用 HttpApiAdapter
    // 通过HTTP请求访问后端API
  }
}

// 示例6：在React组件中的使用
export function ReactComponentExample() {
  // 在React组件中，你可以这样使用：
  /*
  import { databaseAdapter } from '../lib/database/adapter';
  import { useState, useEffect } from 'react';
  
  function ChatComponent() {
    const [sessions, setSessions] = useState([]);
    const [messages, setMessages] = useState([]);
    
    useEffect(() => {
      // 加载会话列表
      databaseAdapter.getAllSessions().then(setSessions);
    }, []);
    
    const handleSessionSelect = async (sessionId: string) => {
      // 加载会话消息
      const sessionMessages = await databaseAdapter.getSessionMessages(sessionId);
      setMessages(sessionMessages);
    };
    
    const handleSendMessage = async (content: string, sessionId: string) => {
      // 创建新消息
      const newMessage = await databaseAdapter.createMessage({
        id: `msg_${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content
      });
      
      // 更新消息列表
      setMessages(prev => [...prev, newMessage]);
    };
    
    return (
      <div>
        {sessions.map(session => (
          <div key={session.id} onClick={() => handleSessionSelect(session.id)}>
            {session.title}
          </div>
        ))}
        
        <div>
          {messages.map(message => (
            <div key={message.id}>
              <strong>{message.role}:</strong> {message.content}
            </div>
          ))}
        </div>
      </div>
    );
  }
  */
  
  console.log('React组件使用示例已在注释中提供');
}

// 示例7：迁移现有代码
export function migrationExample() {
  console.log(`
  迁移指南：
  
  1. 替换直接的 apiClient 调用：
     // 原来
     const sessions = await apiClient.getSessions();
     
     // 现在
     const sessions = await databaseAdapter.getAllSessions();
  
  2. 替换 conversationsApi 调用：
     // 原来
     const messages = await conversationsApi.getMessages(sessionId, {});
     
     // 现在
     const messages = await databaseAdapter.getSessionMessages(sessionId);
  
  3. 统一数据格式：
     适配器会自动处理数据格式转换，确保返回的数据格式一致
  
  4. 环境自适应：
     无需修改业务逻辑代码，适配器会根据运行环境自动选择最佳的数据访问方式
  `);
}

// 示例8：性能对比
export async function performanceComparisonExample(sessionId: string) {
  console.log('开始性能对比测试...');
  
  // HTTP API 方式
  const startHttp = Date.now();
  await apiClient.getSessionMessages(sessionId);
  const httpTime = Date.now() - startHttp;
  
  // 适配器方式（在服务器环境中会使用直接数据库访问）
  const startAdapter = Date.now();
  await databaseAdapter.getSessionMessages(sessionId);
  const adapterTime = Date.now() - startAdapter;
  
  console.log(`HTTP API 耗时: ${httpTime}ms`);
  console.log(`适配器耗时: ${adapterTime}ms`);
  console.log(`性能提升: ${((httpTime - adapterTime) / httpTime * 100).toFixed(2)}%`);
}