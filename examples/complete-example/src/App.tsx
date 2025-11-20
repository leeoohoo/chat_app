/// <reference types="react" />
/// <reference types="react-dom" />
/// <reference types="vite/client" />

import  { useEffect, useState, useRef, ReactNode } from 'react';
import { AiChat } from '@leeoohoo/aichat';
import type { Application } from '@leeoohoo/aichat';
import '@leeoohoo/aichat/styles';
import { registerMcpManagerPlugin } from './plugins/McpManagerPlugin';
import PluginLauncher from './components/PluginLauncher';

// 应用窗口缩放配置：调整此值来控制应用内容的缩放比例
// 值越大，内容显示越小；值越小，内容显示越大
// 建议范围：1600-2400
const WEBVIEW_BASE_WIDTH = 1080;

/**
 * 完整使用示例 - 使用 AiChat 类实例化
 * 展示如何通过 new AiChat() 的方式使用AI聊天组件
 */
function App() {
  const [aiChatInstance, setAiChatInstance] = useState<AiChat | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [isElectron, setIsElectron] = useState<boolean>(false);
  const [leftPanelWidth, setLeftPanelWidth] = useState(384);
  const [isDragging, setIsDragging] = useState(false);
  const [isAppLoading, setIsAppLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  // webview 引用与嵌入错误状态（仅 Electron 环境使用）
  const webviewRef = useRef<any>(null);
  const [embedError, setEmbedError] = useState<string | null>(null);

  // =============== 插件机制：注入自定义组件 ===============
  // 允许用户在运行时向窗口挂载 __AICHAT_PLUGINS 或通过 registerAiChatPlugin 动态注册
  type ChatPlugin = {
    id: string;
    name: string;
    icon?: ReactNode;
    render: (ctx: { aiChat: AiChat }) => ReactNode;
  };

  const [plugins, setPlugins] = useState<ChatPlugin[]>(() => {
    const injected = (typeof window !== 'undefined' && (window as any).__AICHAT_PLUGINS) || [];
    return Array.isArray(injected) ? injected : [];
  });

  // 提供全局注册函数，便于外部注入组件
  useEffect(() => {
    (window as any).registerAiChatPlugin = (plugin: ChatPlugin) => {
      setPlugins((prev: ChatPlugin[]) => {
        if (prev.some(p => p.id === plugin.id)) return prev; // 去重
        return [...prev, plugin];
      });
    };
    // 在注册函数可用后，注入 MCP 管理插件（去重）
    try { registerMcpManagerPlugin(); } catch {}
  }, []);

  // 无内联：插件 UI 由 PluginLauncher 组件负责


  // 处理拖动调整左侧面板宽度
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      // 获取容器的左边界位置
      const containerRect = containerRef.current.getBoundingClientRect();
      const relativeX = e.clientX - containerRect.left;

      const minWidth = 200;
      const maxWidth = containerRect.width * 0.7;
      const newWidth = Math.min(Math.max(relativeX, minWidth), maxWidth);

      setLeftPanelWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging]);

  // 检测 Electron 环境
  useEffect(() => {
    const checkElectron = async () => {
      const nav = typeof navigator !== 'undefined' ? navigator.userAgent.toLowerCase() : '';
      const hasElectronProcess = typeof (window as any).process !== 'undefined' && !!(window as any).process.versions?.electron;
      const hasElectronAPI = typeof (window as any).electronAPI !== 'undefined';
      const isElectronEnv = hasElectronProcess || nav.includes('electron') || hasElectronAPI;

      console.log('[App] Electron detection:', { hasElectronProcess, hasElectronAPI, isElectronEnv });
      setIsElectron(isElectronEnv);
    };

    checkElectron();
  }, []);

  useEffect(() => {
    try {
      // 先检测 Electron 环境
      const nav = typeof navigator !== 'undefined' ? navigator.userAgent.toLowerCase() : '';
      const hasElectronProcess = typeof (window as any).process !== 'undefined' && !!(window as any).process.versions?.electron;
      const hasElectronAPI = typeof (window as any).electronAPI !== 'undefined';
      const isElectronEnv = hasElectronProcess || nav.includes('electron') || hasElectronAPI;

      console.log('[App] Electron detection:', { hasElectronProcess, hasElectronAPI, isElectronEnv });
      setIsElectron(isElectronEnv);

      const apiBase = import.meta.env.VITE_API_BASE || '/api';

      // 创建 AiChat 实例 - 完整功能版本
      // 最后一个参数是应用选择回调函数
      const aiChat = new AiChat(
        'custom_user_127',
        'custom_project_456',
        apiBase,
        'h-full w-full',
        false, // showMcpManager（由插件替代原生面板）
        true,  // showAiModelManager
        true,  // showSystemContextEditor
        true,  // showAgentManager
        (app) => {  // onApplicationSelect 回调
          console.log('[App] 📢 应用被选择:', app);
          setSelectedApp(app);
          setIsAppLoading(true); // 开始加载
          setEmbedError(null);

          // 检测 Electron 环境并处理
          const hasElectronAPI = typeof (window as any).electronAPI !== 'undefined';
          const hasElectronProcess = typeof (window as any).process !== 'undefined' && !!(window as any).process.versions?.electron;
          const currentIsElectron = hasElectronAPI || hasElectronProcess;

          console.log('[App] 🔍 环境检测:', {
            hasElectronAPI,
            hasElectronProcess,
            currentIsElectron,
            appData: { id: app.id, name: app.name, url: app.url }
          });

          // ✨ 在这里你可以自己决定如何处理应用打开
          if (currentIsElectron && hasElectronAPI) {
            console.log('[App] Electron 环境 - 可以调用 electronAPI.openAppWindow');
            // 取消注释下面的代码来启用自动打开：
            /*
            (window as any).electronAPI.openAppWindow({
              id: app.id,
              name: app.name,
              url: app.url,
              iconUrl: app.iconUrl,
            }).then((result: any) => {
              if (result.success) {
                console.log('[App] ✅ Electron 窗口打开成功:', app.name);
              }
            });
            */
          } else if (!currentIsElectron) {
            console.log('[App] 浏览器环境 - 应用选择已记录:', app.name);
            // 🔧 在浏览器环境，你可以选择：
            // - 使用 window.open 打开新窗口
            // - 在页面底部的 iframe 中显示
            // - 或者其他自定义行为
          }
        }
      );

      
      // 其他配置示例：

      // 1. 简化聊天版本（隐藏所有管理模块）
      // const simpleChatInstance = new AiChat(
      //   'simple_user', 'simple_project', 'http://localhost:8000/api', 'h-full w-full',
      //   false, false, false, false
      // );

      // 2. 只显示AI配置管理
      // const aiConfigOnlyInstance = new AiChat(
      //   'config_user', 'config_project', 'http://localhost:8000/api', 'h-full w-full',
      //   false, true, false, false
      // );

      // 3. 只显示MCP服务管理
      // const mcpOnlyInstance = new AiChat(
      //   'mcp_user', 'mcp_project', 'http://localhost:8000/api', 'h-full w-full',
      //   true, false, false, false
      // );

      // 4. 显示AI配置和System Prompt编辑器，隐藏MCP
      // const aiAndSystemInstance = new AiChat(
      //   'ai_system_user', 'ai_system_project', 'http://localhost:8000/api', 'h-full w-full',
      //   false, true, true, false
      // );

      setAiChatInstance(aiChat);
      setIsInitialized(true);
      setError(null);

      // 如果用户通过 window.__AICHAT_PLUGINS 注入了插件但没有图标，默认生成一个文本图标
      setPlugins((prev) => prev.map(p => ({
        ...p,
        icon: p.icon || <span className="text-xs">{p.name}</span>
      })));

      console.log('🎉 AiChat 实例创建成功！');
      console.log('配置信息:', aiChat.getConfig());

      // 验证自定义参数是否被正确使用
      const config = aiChat.getConfig();
      console.log('✅ 验证自定义参数:');
      console.log('  - 用户ID:', config.userId, '(期望: custom_user_127)');
      console.log('  - 项目ID:', config.projectId, '(期望: custom_project_456)');

      // 验证 API 客户端是否使用了正确的 baseUrl
      const apiClient = aiChat.getApiClient();
      console.log('  - API客户端baseUrl:', apiClient.getBaseUrl());
      console.log('  - 是否提供应用选择回调:', !!config.onApplicationSelect);

      // 验证参数是否正确传递
      const isUserIdCorrect = config.userId === 'custom_user_127';
      const isProjectIdCorrect = config.projectId === 'custom_project_456';
      const isApiClientBaseUrlCorrect = apiClient.getBaseUrl() === apiBase;

      console.log('🔍 参数验证结果:');
      console.log('  ✅ 用户ID正确:', isUserIdCorrect);
      console.log('  ✅ 项目ID正确:', isProjectIdCorrect);
      console.log('  ✅ API客户端URL正确:', isApiClientBaseUrlCorrect);

      if (isUserIdCorrect && isProjectIdCorrect && isApiClientBaseUrlCorrect) {
        console.log('🎉 所有自定义参数都被正确传递和使用！');
      } else {
        console.warn('⚠️ 某些参数可能没有被正确传递');
      }
    } catch (err) {
      console.error('❌ AiChat 实例创建失败:', err);
      setError(err instanceof Error ? err.message : '未知错误');
    }
  }, []);

  // 监听 Electron webview 的加载事件，正确关闭加载动画并捕获失败
  useEffect(() => {
    if (!isElectron || !selectedApp) return;

    // 等待 webview 元素渲染到 DOM
    const id = requestAnimationFrame(() => {
      const el = webviewRef.current as any | null;
      if (!el) return;

      const onDomReady = () => {
        console.log('[webview] dom-ready');
        setIsAppLoading(false);
      };
      const onDidFinish = () => {
        console.log('[webview] did-finish-load');
        setIsAppLoading(false);
      };
      const onDidFail = (e: any) => {
        // 常见原因：X-Frame-Options / CSP frame-ancestors 限制
        const code = e?.errorCode;
        const desc = e?.errorDescription || 'unknown';
        console.warn('[webview] did-fail-load', code, desc);
        setIsAppLoading(false);
        setEmbedError(`无法在内嵌窗口中加载（${desc}）。可尝试在新窗口打开。`);
      };

      try {
        el.addEventListener('dom-ready', onDomReady);
        el.addEventListener('did-finish-load', onDidFinish);
        el.addEventListener('did-fail-load', onDidFail);

        // 超时兜底：10 秒仍未完成则提示外部打开
        const timeout = setTimeout(() => {
          if (isAppLoading) {
            console.warn('[webview] load timeout');
            setIsAppLoading(false);
            setEmbedError('加载超时，可能被目标站点禁止内嵌。可尝试在新窗口打开。');
          }
        }, 10000);

        return () => {
          clearTimeout(timeout);
          try { el.removeEventListener('dom-ready', onDomReady); } catch {}
          try { el.removeEventListener('did-finish-load', onDidFinish); } catch {}
          try { el.removeEventListener('did-fail-load', onDidFail); } catch {}
        };
      } catch (err) {
        console.warn('[webview] attach listeners failed:', err);
      }
    });

    return () => cancelAnimationFrame(id);
  }, [isElectron, selectedApp, isAppLoading]);

  // 插件按钮/菜单逻辑已移动到 PluginLauncher 组件

  // 浏览器环境的兜底超时处理（例如被 X-Frame-Options/CSP 拒绝时）
  useEffect(() => {
    if (isElectron || !selectedApp) return;

    const timeout = setTimeout(() => {
      if (isAppLoading) {
        console.warn('[iframe] load timeout');
        setIsAppLoading(false);
        setEmbedError('加载超时，目标站点可能禁止被 iframe 内嵌。可尝试在新窗口打开。');
      }
    }, 10000);

    return () => clearTimeout(timeout);
  }, [isElectron, selectedApp, isAppLoading]);

  if (error) {
    return (
      <div className="h-screen w-full bg-gray-50 flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold mb-2">初始化失败</h2>
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!isInitialized || !aiChatInstance) {
    return (
      <div className="h-screen w-full bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在初始化 AiChat...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full bg-gray-50">
      {/* 插件入口/菜单/弹窗（独立组件） */}
      <PluginLauncher aiChat={aiChatInstance} plugins={plugins} />
      {/* 拖动时的遮罩层，防止iframe捕获鼠标事件 */}
      {isDragging && (
        <div className="fixed inset-0 z-50 cursor-col-resize" />
      )}

      <div ref={containerRef} className="h-full max-w-6xl mx-auto bg-white shadow-lg flex">
        {/* 左侧：选中的应用 */}
        {selectedApp && (
          <>
            <div
              className="border-r border-gray-200 flex flex-col"
              style={{ width: `${leftPanelWidth}px` }}
            >
              <div className="px-4 py-2 border-b border-gray-200 text-sm text-gray-700 flex items-center justify-between">
                <span className="font-medium">{selectedApp.name}</span>
                <button
                  onClick={() => {
                    setSelectedApp(null);
                    setIsAppLoading(false); // 重置加载状态
                  }}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="flex-1 bg-gray-50 relative overflow-hidden">
                {/* 加载动画 */}
                {(isAppLoading || embedError) && (
                  <div className="absolute inset-0 bg-white/90 z-20 flex items-center justify-center px-4">
                    <div className="text-center">
                      {isAppLoading && (
                        <>
                          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                          <p className="text-gray-600 text-sm">正在加载应用...</p>
                        </>
                      )}
                      {embedError && (
                        <>
                          <p className="text-red-600 text-sm mb-3">{embedError}</p>
                          <div className="flex items-center justify-center space-x-3">
                            <button
                              className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm"
                              onClick={() => {
                                if (!selectedApp) return;
                                // Electron：建议走原生窗口；浏览器：新标签页
                                const hasAPI = typeof (window as any).electronAPI !== 'undefined';
                                if (hasAPI) {
                                  (window as any).electronAPI.openAppWindow({
                                    id: selectedApp.id,
                                    name: selectedApp.name,
                                    url: selectedApp.url,
                                    iconUrl: selectedApp.iconUrl,
                                  });
                                } else {
                                  window.open(selectedApp.url, '_blank', 'noopener,noreferrer');
                                }
                              }}
                            >在新窗口打开</button>
                            <button
                              className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded text-sm"
                              onClick={() => setEmbedError(null)}
                            >关闭提示</button>
                          </div>
                        </>
                      )}
                      <p className="text-gray-400 text-xs mt-2">{selectedApp?.name}</p>
                    </div>
                  </div>
                )}

                {(() => {
                  const baseWidth = WEBVIEW_BASE_WIDTH;
                  const scale = leftPanelWidth / baseWidth;

                  if (isElectron) {
                    // Electron 环境：使用 webview，通过 CSS transform 缩放
                    return (
                      <div className="w-full h-full overflow-hidden">
                        {/* @ts-ignore - 定义已在全局 d.ts 中 */}
                        <webview
                          key={selectedApp.url}
                          ref={webviewRef}
                          src={selectedApp.url}
                          style={{
                            width: `${baseWidth}px`,
                            height: `${100 / scale}%`,
                            transform: `scale(${scale})`,
                            transformOrigin: 'top left'
                          }}
                          // 伪装为常见 Chrome UA，避免部分站点拒绝 Electron UA
                          useragent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                          allowpopups
                        />
                      </div>
                    );
                  } else {
                    // 浏览器环境：使用 iframe，添加缩放功能
                    return (
                      <div className="w-full h-full overflow-hidden">
                        <iframe
                          key={selectedApp.url}
                          src={selectedApp.url}
                          className="border-0"
                          style={{
                            width: `${baseWidth}px`,
                            height: `${100 / scale}%`,
                            transform: `scale(${scale})`,
                            transformOrigin: 'top left'
                          }}
                          sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                          referrerPolicy="no-referrer"
                          onLoad={() => {
                            console.log('[iframe] Content loaded');
                            setIsAppLoading(false);
                          }}
                        />
                      </div>
                    );
                  }
                })()}
              </div>
            </div>

            {/* 可拖动的分隔条 */}
            <div
              className="w-2 bg-gray-300 hover:bg-blue-500 cursor-col-resize flex-shrink-0 transition-all relative group z-10"
              onMouseDown={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              title="拖动调整大小"
            >
              {/* 拖动指示器 - 更大更明显，默认显示 */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 transition-all pointer-events-none">
                <div className="flex flex-col items-center justify-center space-y-1 bg-white rounded-full p-2 shadow-md border border-gray-200 opacity-70 group-hover:opacity-100 group-hover:scale-110">
                  <div className="flex space-x-0.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 group-hover:bg-blue-500" />
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 group-hover:bg-blue-500" />
                  </div>
                  <div className="flex space-x-0.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 group-hover:bg-blue-500" />
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 group-hover:bg-blue-500" />
                  </div>
                  <div className="flex space-x-0.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 group-hover:bg-blue-500" />
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400 group-hover:bg-blue-500" />
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* 右侧：聊天界面 */}
        <div className="flex-1 flex flex-col min-w-0 shadow-[-4px_0_10px_rgba(0,0,0,0.1)]" style={{ borderLeft: '2px solid #e5e7eb' }}>
          {/* 使用 AiChat 实例的 render 方法 */}
          {aiChatInstance.render()}
        </div>
      </div>

      {/* Header 内的插件按钮（Portal 注入到主题按钮左侧） */}
      {/* 插件 UI 已交由 PluginLauncher 组件处理 */}

      {/* 插件 UI 已交由 PluginLauncher 组件处理 */}

      {/* 应用信息 */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-black text-white p-2 rounded text-xs max-w-xs">
          <div>AI聊天组件示例 (AiChat 类)</div>
          <div>版本: 1.0.0</div>
          <div>开发模式</div>
          <div className="mt-1 text-yellow-300">
            使用 new AiChat() 方式
          </div>
          <div className="mt-1 text-green-300 text-xs">
            ✅ 实例化成功
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
