/// <reference types="react" />
/// <reference types="react-dom" />

import React, { useEffect, useRef, useState } from 'react';
import { AiChat } from '@leeoohoo/aichat';
import '@leeoohoo/aichat/styles';

/**
 * 完整使用示例 - 使用 AiChat 类实例化
 * 展示如何通过 new AiChat() 的方式使用AI聊天组件
 */
function App() {
  const [aiChatInstance, setAiChatInstance] = useState<AiChat | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      // 创建 AiChat 实例 - 使用自定义参数测试
      const aiChat = new AiChat(
        'custom_user_125',            // 自定义用户ID
        'custom_project_456',         // 自定义项目ID
        'http://localhost:8000/api',  // 自定义API基础URL
        'h-full w-full'               // CSS类名
      );

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
      console.log('  - API URL:', config.baseUrl, '(期望: http://localhost:8000/api)');
      
      // 验证 API 客户端是否使用了正确的 baseUrl
      const apiClient = aiChat.getApiClient();
      console.log('  - API客户端baseUrl:', apiClient.getBaseUrl());
      
      // 验证参数是否正确传递
      const isUserIdCorrect = config.userId === 'custom_user_125';
      const isProjectIdCorrect = config.projectId === 'custom_project_456';
      const isBaseUrlCorrect = config.baseUrl === 'http://localhost:8000/api';
      const isApiClientBaseUrlCorrect = apiClient.getBaseUrl() === 'http://localhost:8000/api';
      
      console.log('🔍 参数验证结果:');
      console.log('  ✅ 用户ID正确:', isUserIdCorrect);
      console.log('  ✅ 项目ID正确:', isProjectIdCorrect);
      console.log('  ✅ API URL正确:', isBaseUrlCorrect);
      console.log('  ✅ API客户端URL正确:', isApiClientBaseUrlCorrect);
      
      if (isUserIdCorrect && isProjectIdCorrect && isBaseUrlCorrect && isApiClientBaseUrlCorrect) {
        console.log('🎉 所有自定义参数都被正确传递和使用！');
      } else {
        console.warn('⚠️ 某些参数可能没有被正确传递');
      }
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