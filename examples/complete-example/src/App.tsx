/// <reference types="react" />
/// <reference types="react-dom" />
/// <reference types="vite/client" />

import  { useEffect, useState } from 'react';
import { AiChat } from '@leeoohoo/aichat';
import type { Application } from '@leeoohoo/aichat';
import '@leeoohoo/aichat/styles';

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

  // 处理拖动调整左侧面板宽度
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      const minWidth = 200;
      const maxWidth = window.innerWidth * 0.7;
      const newWidth = Math.min(Math.max(e.clientX, minWidth), maxWidth);
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

      // 统一使用环境变量控制后端 API 基础地址
      const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

      // 创建 AiChat 实例 - 完整功能版本
      // 最后一个参数是应用选择回调函数
      const aiChat = new AiChat(
        'custom_user_127',
        'custom_project_456',
        apiBase,
        'h-full w-full',
        true,  // showMcpManager
        true,  // showAiModelManager
        true,  // showSystemContextEditor
        true,  // showAgentManager
        (app) => {  // onApplicationSelect 回调
          console.log('[App] 📢 应用被选择:', app);
          setSelectedApp(app);

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
      <div className="h-full max-w-6xl mx-auto bg-white shadow-lg flex">
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
                  onClick={() => setSelectedApp(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="flex-1 bg-gray-50">
                {isElectron ? (
                  // Electron 环境：使用 webview
                  // @ts-ignore - 定义已在全局 d.ts 中
                  <webview
                    key={selectedApp.url}
                    src={selectedApp.url}
                    style={{ width: '100%', height: '100%' }}
                    {...({ allowpopups: true } as any)}
                  />
                ) : (
                  // 浏览器环境：使用 iframe
                  <iframe
                    key={selectedApp.url}
                    src={selectedApp.url}
                    className="w-full h-full border-0"
                    sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                    referrerPolicy="no-referrer"
                  />
                )}
              </div>
            </div>

            {/* 可拖动的分隔条 */}
            <div
              className="w-1 bg-gray-300 hover:bg-blue-500 cursor-col-resize flex-shrink-0 transition-colors"
              onMouseDown={() => setIsDragging(true)}
              title="拖动调整大小"
            />
          </>
        )}

        {/* 右侧：聊天界面 */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* 使用 AiChat 实例的 render 方法 */}
          {aiChatInstance.render()}
        </div>
      </div>

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