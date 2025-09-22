import React, { useEffect, useRef, useState } from 'react';
import { useChatStore } from '../lib/store';
import { createChatStore } from '../lib/store/createChatStore';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { SessionList } from './SessionList';
import { ThemeToggle } from './ThemeToggle';
import McpManager from './McpManager';
import AiModelManager from './AiModelManager';
import SystemContextEditor from './SystemContextEditor';
import { cn } from '../lib/utils';
import ApiClient from '../lib/api/client';

export interface StandaloneChatInterfaceProps {
  className?: string;
  apiBaseUrl?: string;
  port?: number;
  userId?: string;
  projectId?: string;
}

/**
 * 完全独立的聊天界面组件
 * 支持自定义API端口和基础URL
 */
export const StandaloneChatInterface: React.FC<StandaloneChatInterfaceProps> = ({
  className,
  apiBaseUrl,
  port,
  userId,
  projectId,
}) => {
  // 根据传入的port或apiBaseUrl创建自定义的API基础URL
  const customApiBaseUrl = React.useMemo(() => {
    if (apiBaseUrl) {
      return apiBaseUrl;
    }
    if (port) {
      return `http://localhost:${port}/api`;
    }
    return undefined;
  }, [apiBaseUrl, port]);

  // 创建自定义的ApiClient实例
  const customApiClient = React.useMemo(() => {
    if (customApiBaseUrl) {
      return new ApiClient(customApiBaseUrl);
    }
    return undefined;
  }, [customApiBaseUrl]);

  // Create custom store if we have custom parameters or custom API client
  const customStore = React.useMemo(() => {
    if (customApiClient || userId || projectId) {
      return createChatStore(customApiClient, {
        userId,
        projectId,
        configUrl: customApiBaseUrl
      });
    }
    return null;
  }, [customApiClient, userId, projectId, customApiBaseUrl]);
  // Use custom store if available, otherwise use default store
  const store = customStore || useChatStore;
  
  const {
    currentSession,
    messages,
    isLoading,
    isStreaming,
    error,
    loadSessions,
    sendMessage,
    clearError,
    aiModelConfigs,
    selectedModelId,
    setSelectedModel,
    loadAiModelConfigs,
    abortCurrentConversation,
  } = store();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [showMcpManager, setShowMcpManager] = useState(false);
  const [showAiModelManager, setShowAiModelManager] = useState(false);
  const [showSystemContextEditor, setShowSystemContextEditor] = useState(false);

  // 初始化加载会话和AI模型配置
  useEffect(() => {
    loadSessions();
    loadAiModelConfigs();
  }, [loadSessions, loadAiModelConfigs]);

  // 自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming]);

  // 处理消息发送 - 完全内部处理，不需要外部回调
  const handleMessageSend = async (content: string, attachments?: File[]) => {
    try {
      await sendMessage(content, attachments);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div className={cn(
      'flex flex-col h-screen bg-background text-foreground',
      className
    )}>
      {/* 头部 - 包含会话按钮和主题切换 */}
      <div className="flex items-center justify-between p-4 bg-card border-b border-border">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setIsSessionModalOpen(true)}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="打开会话列表"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          
          {currentSession && (
            <div className="flex-1 min-w-0">
              <h1 className="text-lg font-semibold text-foreground truncate">
                {currentSession.title}
              </h1>
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowMcpManager(true)}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="MCP 服务器管理"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
            </svg>
          </button>
          <button
            onClick={() => setShowAiModelManager(true)}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="AI 模型管理"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </button>
          <button
            onClick={() => setShowSystemContextEditor(true)}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="系统上下文设置"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <ThemeToggle />
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm text-destructive">{error}</p>
            <button
              onClick={clearError}
              className="text-destructive hover:text-destructive/80 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* 消息列表 */}
      <div className="flex-1 overflow-hidden">
        {currentSession ? (
          <MessageList
            messages={messages}
            isLoading={isLoading}
            isStreaming={isStreaming}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center">
              <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p className="text-lg mb-2">欢迎使用AI聊天助手</p>
              <p className="text-sm">点击左上角按钮创建新会话开始对话</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      {currentSession && (
        <InputArea
          onSend={handleMessageSend}
          onStop={abortCurrentConversation}
          disabled={isLoading || isStreaming}
          isStreaming={isStreaming}
          selectedModelId={selectedModelId}
          availableModels={aiModelConfigs}
          onModelChange={setSelectedModel}
          showModelSelector={true}
        />
      )}

      {/* 会话管理抽屉 */}
      <SessionList 
        isOpen={isSessionModalOpen} 
        onClose={() => setIsSessionModalOpen(false)} 
        store={store} 
      />

      {/* MCP管理器模态框 */}
      {showMcpManager && (
          <McpManager onClose={() => setShowMcpManager(false)} store={store} />
        )}

      {/* AI模型管理器模态框 */}
      {showAiModelManager && (
          <AiModelManager onClose={() => setShowAiModelManager(false)} store={store} />
        )}

      {/* 系统上下文编辑器模态框 */}
      {showSystemContextEditor && (
        <SystemContextEditor 
          onClose={() => setShowSystemContextEditor(false)} 
          store={store}
        />
      )}
    </div>
  );
};

export default StandaloneChatInterface;