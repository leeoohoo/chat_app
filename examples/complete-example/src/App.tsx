// import React from 'react';
import { StandaloneChatInterface } from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

/**
 * 完整使用示例 - 独立聊天组件
 * 展示如何在实际项目中使用AI聊天组件
 */
function App() {
  return (
    <div className="h-screen w-full bg-gray-50">
      <div className="h-full max-w-6xl mx-auto bg-white shadow-lg">
        <StandaloneChatInterface className="h-full" />
      </div>
      
      {/* 应用信息 */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-black text-white p-2 rounded text-xs max-w-xs">
          <div>AI聊天组件示例</div>
          <div>版本: 1.0.0</div>
          <div>开发模式</div>
        </div>
      )}
    </div>
  );
}

export default App;