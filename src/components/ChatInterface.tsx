import React, { useEffect, useRef, useState } from 'react';
import { useChatStoreFromContext } from '../lib/store/ChatStoreContext';
import { MessageList } from './MessageList';
import { InputArea } from './InputArea';
import { SessionList } from './SessionList';
import { ThemeToggle } from './ThemeToggle';
import McpManager from './McpManager';
import AiModelManager from './AiModelManager';
import SystemContextEditor from './SystemContextEditor';
import AgentManager from './AgentManager';
// 应用弹窗管理器由 ApplicationsPanel 直接承担
import ApplicationsPanel from './ApplicationsPanel';
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
    agents,
    selectedAgentId,
    setSelectedAgent,
    loadAgents,
    abortCurrentConversation,
    applications,
    selectedApplicationId,
  } = useChatStoreFromContext();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [showMcpManager, setShowMcpManager] = useState(false);
  const [showAiModelManager, setShowAiModelManager] = useState(false);
  const [showSystemContextEditor, setShowSystemContextEditor] = useState(false);
  const [showAgentManager, setShowAgentManager] = useState(false);
  const [showApplicationsPanel, setShowApplicationsPanel] = useState(false);
  const [applicationsPanelWidth, setApplicationsPanelWidth] = useState(260);
  const [isResizingAppsPanel, setIsResizingAppsPanel] = useState(false);
  const [iframeWidth, setIframeWidth] = useState(600);
  const [isResizingIframe, setIsResizingIframe] = useState(false);
  const [iframeScale, setIframeScale] = useState(1);
  const [targetWidth, setTargetWidth] = useState(1600);
  const [manualScaleOverride, setManualScaleOverride] = useState<number | null>(null);

  // 初始化加载会话、AI模型和智能体配置
  useEffect(() => {
    // React 18 在开发模式下会双调用副作用，这里加一次性保护
    const didInit = (window as any).__chatInterfaceDidInit__ ?? false;
    if (didInit) return;
    (window as any).__chatInterfaceDidInit__ = true;

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

  // 根据iframe宽度自动计算缩放比例
  useEffect(() => {
    if (manualScaleOverride !== null) {
      setIframeScale(manualScaleOverride);
    } else {
      const safetyFactor = 0.95; // 安全系数，避免出现滚动条
      const calculatedScale = (iframeWidth * safetyFactor) / targetWidth;
      setIframeScale(Math.min(1, calculatedScale)); // 最大不超过1
    }
  }, [iframeWidth, targetWidth, manualScaleOverride]);

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

  const startResizeAppsPanel = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsResizingAppsPanel(true);
    const startX = e.clientX;
    const startWidth = applicationsPanelWidth;
    const onMouseMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startX;
      const next = Math.min(420, Math.max(200, startWidth + delta));
      setApplicationsPanelWidth(next);
    };
    const onMouseUp = () => {
      setIsResizingAppsPanel(false);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  const startResizeIframe = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsResizingIframe(true);
    const startX = e.clientX;
    const startWidth = iframeWidth;
    const onMouseMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startX;
      const next = Math.min(1200, Math.max(400, startWidth + delta));
      setIframeWidth(next);
    };
    const onMouseUp = () => {
      setIsResizingIframe(false);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  // 获取选中应用的信息
  const selectedApp = applications?.find((app: any) => app.id === selectedApplicationId);

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
            onClick={() => setShowApplicationsPanel(true)}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="打开应用列表"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M4 5h6v14H4z" strokeWidth="2" />
              <path d="M12 5h8v14h-8z" strokeWidth="2" />
            </svg>
          </button>
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
            onClick={() => setShowAgentManager(true)}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
            title="智能体管理"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6M9 16h6M6 8h12a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2v-8a2 2 0 012-2z" />
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

        {/* 消息列表 + 左侧应用面板 + iframe */}
        <div className="flex flex-1 overflow-hidden">
          {/* 已移除左侧应用抽屉面板，改为弹窗 */}

          {/* iframe区域 - 显示选中的应用 */}
          {selectedApp && selectedApp.url && (
            <>
              <div
                className="shrink-0 border-r border-border bg-card flex flex-col"
                style={{ width: iframeWidth }}
              >
                {/* iframe头部 */}
                <div className="flex items-center justify-between p-2 border-b border-border bg-muted/30">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center overflow-hidden shrink-0">
                      {selectedApp.iconUrl ? (
                        <img src={selectedApp.iconUrl} alt={selectedApp.name} className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-white text-xs font-bold">
                          {selectedApp.name.charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-foreground truncate">{selectedApp.name}</div>
                      <div className="text-xs text-muted-foreground truncate">{selectedApp.url}</div>
                    </div>
                  </div>
                  {/* 缩放控制 */}
                  <div className="flex items-center space-x-1 ml-2">
                    <div className="flex items-center space-x-1 px-2 py-1 bg-background/50 rounded">
                      <span className="text-xs text-muted-foreground">缩放:</span>
                      <span className="text-xs font-mono text-foreground">{Math.round(iframeScale * 100)}%</span>
                    </div>
                    <div className="flex space-x-0.5">
                      <button
                        onClick={() => { setTargetWidth(1200); setManualScaleOverride(null); }}
                        className="px-1.5 py-0.5 text-xs bg-background hover:bg-accent rounded transition-colors"
                        title="小尺寸 (1200px)"
                      >S</button>
                      <button
                        onClick={() => { setTargetWidth(1600); setManualScaleOverride(null); }}
                        className="px-1.5 py-0.5 text-xs bg-background hover:bg-accent rounded transition-colors"
                        title="中尺寸 (1600px)"
                      >M</button>
                      <button
                        onClick={() => { setTargetWidth(1920); setManualScaleOverride(null); }}
                        className="px-1.5 py-0.5 text-xs bg-background hover:bg-accent rounded transition-colors"
                        title="大尺寸 (1920px)"
                      >L</button>
                      <button
                        onClick={() => { setTargetWidth(2560); setManualScaleOverride(null); }}
                        className="px-1.5 py-0.5 text-xs bg-background hover:bg-accent rounded transition-colors"
                        title="超大尺寸 (2560px)"
                      >XL</button>
                    </div>
                    <button
                      onClick={() => setManualScaleOverride(manualScaleOverride === null ? 1 : null)}
                      className={`px-2 py-0.5 text-xs rounded transition-colors ${
                        manualScaleOverride !== null ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-accent'
                      }`}
                      title={manualScaleOverride !== null ? '已锁定100%' : '锁定100%缩放'}
                    >
                      {manualScaleOverride !== null ? '🔒' : '🔓'}
                    </button>
                  </div>
                </div>
                {/* iframe内容 */}
                <div className="flex-1 relative bg-white overflow-hidden">
                  <div
                    style={{
                      transform: `scale(${iframeScale})`,
                      transformOrigin: 'top left',
                      width: `${targetWidth}px`,
                      height: `${100 / iframeScale}%`,
                    }}
                  >
                    <iframe
                      src={selectedApp.url}
                      className="w-full h-full border-0"
                      title={selectedApp.name}
                      sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
                      onError={() => {
                        console.error('iframe加载失败', selectedApp.id);
                        // 发送自定义事件通知ApplicationsPanel切换到弹窗模式
                        window.dispatchEvent(new CustomEvent('iframe-load-error', {
                          detail: { appId: selectedApp.id }
                        }));
                      }}
                      onLoad={(e) => {
                        setTimeout(() => {
                          try {
                            const iframe = e.currentTarget;
                            // 尝试访问iframe的contentWindow，如果被CSP阻止会抛出错误
                            if (iframe.contentWindow) {
                              const doc = iframe.contentWindow.document;
                              // 尝试访问document的某个属性，确保没有被CSP阻止
                              const title = doc.title;
                              console.log('iframe加载成功:', title);
                            }
                          } catch (err: any) {
                            // 只有真正的安全策略错误才触发弹窗
                            const isSecurityError =
                              err.name === 'SecurityError' ||
                              err.name === 'DOMException' ||
                              (err.message && (
                                err.message.includes('cross-origin') ||
                                err.message.includes('X-Frame-Options') ||
                                err.message.includes('frame-ancestors') ||
                                err.message.includes('Blocked a frame')
                              ));

                            if (isSecurityError) {
                              console.error('iframe被安全策略阻止:', err);
                              // 发送自定义事件通知ApplicationsPanel切换到弹窗模式
                              window.dispatchEvent(new CustomEvent('iframe-load-error', {
                                detail: { appId: selectedApp.id }
                              }));
                            } else {
                              console.warn('iframe访问失败，但可能不是CSP问题:', err);
                            }
                          }
                        }, 1000); // 增加延迟到1秒，给iframe更多加载时间
                      }}
                    />
                  </div>
                </div>
              </div>
              <div
                onMouseDown={startResizeIframe}
                className="w-1 cursor-col-resize bg-border hover:bg-primary transition-colors"
                title="拖动调整应用窗口宽度"
              />
            </>
          )}

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
        </div>

        {/* 输入区域 */}
        {currentSession && (
          <div className="border-t border-border">
            <InputArea
              onSend={handleMessageSend}
              onStop={abortCurrentConversation}
              disabled={isLoading}
              isStreaming={isStreaming}
              placeholder="输入消息..."
              showModelSelector={true}
              selectedModelId={selectedModelId}
              availableModels={aiModelConfigs}
              onModelChange={setSelectedModel}
              selectedAgentId={selectedAgentId}
              availableAgents={agents}
              onAgentChange={setSelectedAgent}
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

        {/* 智能体管理器 */}
        {showAgentManager && (
          <AgentManager onClose={() => setShowAgentManager(false)} />
        )}
        
        {/* AI模型管理器 */}
        {showAiModelManager && (
          <AiModelManager onClose={() => setShowAiModelManager(false)} />
        )}
        
        {/* 系统上下文编辑器 */}
        {showSystemContextEditor && (
          <SystemContextEditor onClose={() => setShowSystemContextEditor(false)} />
        )}

        {/* 应用列表（弹窗） */}
        <ApplicationsPanel
          isOpen={showApplicationsPanel}
          onClose={() => setShowApplicationsPanel(false)}
          title="应用列表"
          layout="modal"
        />

        {/* 拖动时的覆盖层，避免选中文本 */}
        {(isResizingAppsPanel || isResizingIframe) && (
          <div className="fixed inset-0 cursor-col-resize" style={{ zIndex: 50 }} />
        )}
    </div>
  );
};

export default ChatInterface;