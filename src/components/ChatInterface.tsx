import React, { useEffect, useRef, useState } from 'react';
import { useChatStoreFromContext } from '../lib/store/ChatStoreContext';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { SessionList } from './SessionList';
import { ThemeToggle } from './ThemeToggle';
import McpManager from './McpManager';
import AiModelManager from './AiModelManager';
import SystemContextEditor from './SystemContextEditor';
import { cn } from '../lib/utils';
import type { ChatInterfaceProps } from '../types';

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  className,
  onMessageSend,
  customRenderer,
}) => {
  const {
    currentSession,
    messages,
    isLoading,
    isStreaming,
    error,
    loadSessions,
    // selectSession,
    sendMessage,
    clearError,
    aiModelConfigs,
    selectedModelId,
    setSelectedModel,
    loadAiModelConfigs,
  } = useChatStoreFromContext();

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

  // 处理会话切换
  // const handleSessionChange = async (sessionId: string) => {
  //   await selectSession(sessionId);
  //   onSessionChange?.(sessionId);
  // };

  // 处理消息发送
  const handleMessageSend = async (content: string, attachments?: File[]) => {
    try {
      await sendMessage(content, attachments);
      onMessageSend?.(content, []);
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
              customRenderer={customRenderer}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-muted-foreground mb-2">
                  欢迎使用 AI 聊天
                </h2>
                <p className="text-muted-foreground mb-4">
                  点击左上角按钮选择会话，或创建新的会话开始对话
                </p>
                <button
                  onClick={() => setIsSessionModalOpen(true)}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  打开会话列表
                </button>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        {currentSession && (
          <div className="border-t border-border">
            <InputArea
              onSend={handleMessageSend}
              disabled={isLoading || isStreaming}
              placeholder="输入消息..."
              showModelSelector={true}
              selectedModelId={selectedModelId}
              availableModels={aiModelConfigs}
              onModelChange={setSelectedModel}
            />
          </div>
        )}

        {/* 会话管理抽屉 */}
        <SessionList 
          isOpen={isSessionModalOpen} 
          onClose={() => setIsSessionModalOpen(false)} 
        />
        
        {/* MCP管理器 */}
        {showMcpManager && (
          <McpManager onClose={() => setShowMcpManager(false)} />
        )}
        
        {/* AI模型管理器 */}
        {showAiModelManager && (
          <AiModelManager onClose={() => setShowAiModelManager(false)} />
        )}
        
        {/* 系统上下文编辑器 */}
        {showSystemContextEditor && (
          <SystemContextEditor onClose={() => setShowSystemContextEditor(false)} />
        )}
    </div>
  );
};

export default ChatInterface;