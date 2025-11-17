import React, { useEffect, useRef, useState } from 'react';
import { useChatStore } from '../lib/store';
import { ChatStoreProvider } from '../lib/store/ChatStoreContext';
import { createChatStoreWithBackend } from '../lib/store/createChatStoreWithBackend';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { SessionList } from './SessionList';
import { ThemeToggle } from './ThemeToggle';
import McpManager from './McpManager';
import AiModelManager from './AiModelManager';
import SystemContextEditor from './SystemContextEditor';
import AgentManager from './AgentManager';
import ApplicationsPanel from '@/components/ApplicationsPanel';
import { cn } from '../lib/utils';
import ApiClient from '../lib/api/client';

export interface StandaloneChatInterfaceProps {
  className?: string;
  apiBaseUrl?: string;
  port?: number;
  userId?: string;
  projectId?: string;
  showMcpManager?: boolean;
  showAiModelManager?: boolean;
  showSystemContextEditor?: boolean;
  showAgentManager?: boolean;
  // 控制是否显示“应用列表”按钮
  showApplicationsButton?: boolean;
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
  showMcpManager = true,
  showAiModelManager = true,
  showSystemContextEditor = true,
  showAgentManager = true,
  showApplicationsButton = true,
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
      return createChatStoreWithBackend(customApiClient, {
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
    agents,
    selectedAgentId,
    setSelectedAgent,
    loadAgents,
    abortCurrentConversation,
    applications,
    selectedApplicationId,
    setSelectedApplication,
  } = store();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  
  // 模态框状态
  const [mcpManagerOpen, setMcpManagerOpen] = useState(false);
  const [aiModelManagerOpen, setAiModelManagerOpen] = useState(false);
  const [systemContextEditorOpen, setSystemContextEditorOpen] = useState(false);
  const [agentManagerOpen, setAgentManagerOpen] = useState(false);
  const [showAppPanel, setShowAppPanel] = useState(false);
  // 移除未使用的应用面板宽度状态
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const selectedApp = React.useMemo(() => {
    if (!applications || !selectedApplicationId) return null as any;
    return applications.find((a: any) => a.id === selectedApplicationId) || null;
  }, [applications, selectedApplicationId]);

  // 在关闭或切换应用时，主动清理 iframe，终止网络请求
  useEffect(() => {
    return () => {
      try {
        if (iframeRef.current) {
          // 将 src 置空/置为 about:blank 以便立即终止网络活动
          iframeRef.current.src = 'about:blank';
        }
      } catch {}
    };
  }, [selectedApplicationId]);

  // 移除未使用的拖拽状态与处理函数

  // 初始化加载会话、AI模型与智能体配置
  useEffect(() => {
    // React 18 开发模式副作用双执行，使用一次性保护避免重复请求
    const didInit = (window as any).__standaloneChatInterfaceDidInit__ ?? false;
    if (didInit) return;
    (window as any).__standaloneChatInterfaceDidInit__ = true;

    loadSessions();
    loadAiModelConfigs();
    loadAgents();
  }, [loadSessions, loadAiModelConfigs, loadAgents]);

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
    <ChatStoreProvider userId={userId} projectId={projectId} customApiClient={customApiClient}>
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
        
        <div className="flex items-center gap-2">
          {/* 应用列表按钮（弹窗） */}
          {showApplicationsButton && (
            <button
              onClick={() => setShowAppPanel(true)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
              title="打开应用列表"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 5h6v14H4z" strokeWidth="2" />
                <path d="M12 5h8v14h-8z" strokeWidth="2" />
              </svg>
            </button>
          )}
          {/* 已移除应用管理按钮 */}
          {/* MCP服务管理按钮 */}
          {showMcpManager && (
            <button
              onClick={() => setMcpManagerOpen(true)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
              title="MCP服务管理"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          )}

          {/* AI模型管理按钮 */}
          {showAiModelManager && (
            <button
              onClick={() => setAiModelManagerOpen(true)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
              title="AI配置管理"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
              </svg>
            </button>
          )}

          {/* 系统上下文编辑器按钮 */}
          {showSystemContextEditor && (
            <button
              onClick={() => setSystemContextEditorOpen(true)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
              title="System Prompt编辑器"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </button>
          )}

          {/* 智能体管理按钮 */}
          {showAgentManager && (
            <button
              onClick={() => setAgentManagerOpen(true)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
              title="智能体管理"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6M9 16h6M6 8h12a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2v-8a2 2 0 012-2z" />
              </svg>
            </button>
          )}

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

      {/* 主区域：右侧聊天（已移除左侧应用抽屉） */}
      <div className="flex-1 flex overflow-hidden">
        {/* 右侧消息列表 */}
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
      </div>

      {/* 选中应用的嵌入视图（iframe） */}
      {selectedApp && selectedApp.url && (
        <div className="fixed right-6 bottom-28 w-[70vw] max-w-[1100px] h-[70vh] bg-card rounded-lg border border-border shadow-xl z-40 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-7 h-7 rounded-full overflow-hidden bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center shrink-0">
                {selectedApp.iconUrl ? (
                  <img src={selectedApp.iconUrl} alt={selectedApp.name} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-white text-xs font-bold">{selectedApp.name?.[0]?.toUpperCase?.() || 'A'}</span>
                )}
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium text-foreground truncate">{selectedApp.name}</div>
                {selectedApp.url && (
                  <div className="text-xs text-muted-foreground truncate max-w-[50vw]">{selectedApp.url}</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                className="px-3 py-1.5 text-xs rounded bg-muted hover:bg-accent"
                title="在新窗口打开"
                onClick={() => {
                  try {
                    window.open(selectedApp.url, `_app_${selectedApp.id}`);
                  } catch {}
                }}
              >弹窗打开</button>
              <button
                onClick={() => setSelectedApplication(null)}
                className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
                title="关闭"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>
          <div className="flex-1 bg-background">
            <iframe
              src={selectedApp.url}
              title={selectedApp.name || 'Selected Application'}
              className="w-full h-full"
              key={selectedApp.id}
              ref={iframeRef}
              sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"
              onError={() => {
                try {
                  const evt = new CustomEvent('iframe-load-error', { detail: { appId: selectedApp.id, error: 'Iframe onError' } });
                  window.dispatchEvent(evt as any);
                } catch {}
              }}
              onLoad={(e) => {
                const iframe = e.currentTarget as HTMLIFrameElement;
                setTimeout(() => {
                  try {
                    const cw = iframe.contentWindow;
                    // 访问 title 以触发潜在的跨域/CSP错误
                    const _title = cw?.document?.title;
                    void _title;
                  } catch (err) {
                    try {
                      const evt = new CustomEvent('iframe-load-error', { detail: { appId: selectedApp.id, error: (err as any)?.message || 'SecurityError' } });
                      window.dispatchEvent(evt as any);
                    } catch {}
                  }
                }, 1000);
              }}
            />
          </div>
        </div>
      )}

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
          selectedAgentId={selectedAgentId}
          availableAgents={agents}
          onAgentChange={setSelectedAgent}
        />
      )}

      {/* 会话管理抽屉 */}
      <SessionList 
        isOpen={isSessionModalOpen} 
        onClose={() => setIsSessionModalOpen(false)} 
        store={store} 
      />

      {/* 应用列表（弹窗） */}
      <ApplicationsPanel
        isOpen={showAppPanel}
        onClose={() => setShowAppPanel(false)}
        title="应用列表"
        layout="modal"
      />

      {/* 已移除旧的 ApplicationManager 组件引用，改用上面的 ApplicationsPanel（弹窗模式） */}

      {/* MCP管理器模态框 */}
      {mcpManagerOpen && (
          <McpManager onClose={() => setMcpManagerOpen(false)} store={store} />
        )}

      {/* AI模型管理器模态框 */}
      {aiModelManagerOpen && (
          <AiModelManager onClose={() => setAiModelManagerOpen(false)} store={store} />
        )}

      {/* 智能体管理器模态框 */}
      {showAgentManager && agentManagerOpen && (
          <AgentManager onClose={() => setAgentManagerOpen(false)} store={store} />
        )}

      {/* 系统上下文编辑器模态框 */}
      {systemContextEditorOpen && (
        <SystemContextEditor 
          onClose={() => setSystemContextEditorOpen(false)} 
          store={store}
        />
      )}
      </div>
    </ChatStoreProvider>
  );
};

export default StandaloneChatInterface;