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

  useEffect(() => {
    try {
      // 统一使用环境变量控制后端 API 基础地址
      const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
      // 通过环境变量控制是否显示“应用列表”按钮（默认显示）
      const showApplicationsButton = (import.meta.env.VITE_SHOW_APPLICATIONS_BUTTON ?? 'true') === 'true';

      // 创建 AiChat 实例 - 完整功能版本
      const aiChat = new AiChat(
        'custom_user_127',            // 自定义用户ID
        'custom_project_456',         // 自定义项目ID
        apiBase,                      // 自定义API基础URL
        'h-full w-full',              // CSS类名
        true,                         // showMcpManager - 显示MCP服务管理
        true,                         // showAiModelManager - 显示AI配置管理
        true,                         // showSystemContextEditor - 显示System Prompt编辑器
        true,                         // showAgentManager - 显示智能体管理
        true        // showApplicationsButton - 显示应用列表按钮（可隐藏）
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
      console.log('  - 用户ID:', config.userId, '(期望: custom_user_125)');
      console.log('  - 项目ID:', config.projectId, '(期望: custom_project_456)');
      
      // 验证 API 客户端是否使用了正确的 baseUrl
      const apiClient = aiChat.getApiClient();
      console.log('  - API客户端baseUrl:', apiClient.getBaseUrl());
      console.log('  - 显示应用列表按钮:', showApplicationsButton);
      
      // 验证参数是否正确传递
      const isUserIdCorrect = config.userId === 'custom_user_125';
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

      // 加载应用列表，并订阅所选应用实时变化
      const store = aiChat.getStore();
      store.getState().loadApplications().catch(err => {
      
        console.warn('⚠️ 加载应用列表失败:', err);
      });
      debugger
      const unsubscribe = aiChat.subscribeSelectedApplication((app) => {
        setSelectedApp(app);
      });

      // 检测 Electron 环境（用于外部渲染 webview）
      const nav = typeof navigator !== 'undefined' ? navigator.userAgent.toLowerCase() : '';
      const isElectronDetected = typeof (window as any).process !== 'undefined' && !!(window as any).process.versions?.electron || nav.includes('electron');
      setIsElectron(!!isElectronDetected);

      // 清理订阅
      return () => {
        unsubscribe?.();
      };
    } catch (err) {
      console.error('❌ AiChat 实例创建失败:', err);
      setError(err instanceof Error ? err.message : '未知错误');
    }

    // 清理函数
    return () => {
      if (aiChatInstance) {
        console.log('🧹 清理 AiChat 实例');
        setAiChatInstance(null);
      }
    };
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
      <div className="h-full max-w-6xl mx-auto bg-white shadow-lg">
        {/* 使用 AiChat 实例的 render 方法 */}
        {aiChatInstance.render()}

        {/* 外部渲染：当前所选应用 */}
        <div className="border-t border-gray-200">
          <div className="px-4 py-2 text-sm text-gray-500 flex items-center gap-2">
            <span>当前应用:</span>
            {selectedApp ? (
              <span className="text-gray-800 font-medium">{selectedApp.name}</span>
            ) : (
              <span className="italic">未选择</span>
            )}
          </div>
          {selectedApp && (
            <div className="h-[360px] w-full bg-gray-50">
              {isElectron ? (
                // Electron 环境：使用 webview
                // @ts-ignore - 定义已在全局 d.ts 中
                <webview
                  src={selectedApp.url}
                  style={{ width: '100%', height: '100%' }}
                  allowpopups
                />
              ) : (
                // 浏览器环境：使用 iframe
                <iframe
                  src={selectedApp.url}
                  className="w-full h-full border-0"
                  sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                  referrerPolicy="no-referrer"
                />
              )}
            </div>
          )}
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