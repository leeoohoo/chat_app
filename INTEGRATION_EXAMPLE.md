# 集成示例

这个文档展示了如何在不同类型的项目中集成 `@ai-chat/react-component`。

## 1. 在新的 React 项目中使用

### 创建新项目

```bash
# 使用 Vite 创建 React 项目
npm create vite@latest my-chat-app -- --template react-ts
cd my-chat-app
npm install

# 安装 AI Chat 组件
npm install @ai-chat/react-component

# 安装 Tailwind CSS（如果还没有）
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 配置 Tailwind CSS

在 `tailwind.config.js` 中：

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@ai-chat/react-component/dist/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

在 `src/index.css` 中：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 使用组件

在 `src/App.tsx` 中：

```tsx
import React from 'react';
import AIChatComponent from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';
import './App.css';

function App() {
  return (
    <div className="h-screen w-full bg-gray-50">
      <div className="container mx-auto h-full max-w-6xl">
        <AIChatComponent className="h-full" />
      </div>
    </div>
  );
}

export default App;
```

## 2. 在现有项目中集成

### 作为页面组件

```tsx
import React from 'react';
import { StandaloneChatInterface } from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

const ChatPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900 py-4">
            AI 助手
          </h1>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-lg h-[600px]">
          <StandaloneChatInterface className="h-full" />
        </div>
      </main>
    </div>
  );
};

export default ChatPage;
```

### 作为模态框组件

```tsx
import React, { useState } from 'react';
import { StandaloneChatInterface } from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

const ChatModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
      >
        💬 AI 助手
      </button>

      {/* 模态框 */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* 背景遮罩 */}
          <div 
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={() => setIsOpen(false)}
          />
          
          {/* 聊天界面 */}
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-4xl h-[80vh] m-4">
            <div className="flex justify-between items-center p-4 border-b">
              <h2 className="text-lg font-semibold">AI 助手</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            
            <div className="h-[calc(80vh-4rem)]">
              <StandaloneChatInterface className="h-full" />
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ChatModal;
```

## 3. 高级集成 - 自定义状态管理

```tsx
import React, { useEffect } from 'react';
import { 
  ChatInterface, 
  MessageList,
  InputArea,
  SessionList,
  useChatStore,
  ThemeToggle 
} from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

const CustomChatApp: React.FC = () => {
  const { 
    sessions, 
    currentSession, 
    messages,
    createSession, 
    switchSession,
    sendMessage,
    isLoading
  } = useChatStore();

  // 初始化默认会话
  useEffect(() => {
    if (sessions.length === 0) {
      createSession('默认对话');
    }
  }, [sessions.length, createSession]);

  const handleSendMessage = async (content: string) => {
    if (!currentSession) return;
    
    try {
      await sendMessage({
        content,
        sessionId: currentSession.id,
        role: 'user'
      });
    } catch (error) {
      console.error('发送消息失败:', error);
    }
  };

  return (
    <div className="h-screen flex bg-gray-100">
      {/* 侧边栏 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-xl font-bold">AI 助手</h1>
            <ThemeToggle />
          </div>
          
          <button
            onClick={() => createSession('新对话')}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
          >
            + 新建对话
          </button>
        </div>
        
        <div className="flex-1 overflow-hidden">
          <SessionList 
            sessions={sessions}
            currentSessionId={currentSession?.id}
            onSessionSelect={switchSession}
          />
        </div>
      </div>

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col">
        {currentSession ? (
          <>
            {/* 聊天头部 */}
            <div className="bg-white border-b border-gray-200 p-4">
              <h2 className="text-lg font-semibold">
                {currentSession.title}
              </h2>
            </div>
            
            {/* 消息列表 */}
            <div className="flex-1 overflow-hidden">
              <MessageList 
                messages={messages}
                isLoading={isLoading}
              />
            </div>
            
            {/* 输入区域 */}
            <div className="bg-white border-t border-gray-200">
              <InputArea 
                onSendMessage={handleSendMessage}
                disabled={isLoading}
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-gray-500">请选择或创建一个对话</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomChatApp;
```

## 4. 环境配置

### 环境变量

创建 `.env.local` 文件：

```env
# OpenAI API 配置
VITE_OPENAI_API_KEY=your_openai_api_key_here
VITE_OPENAI_BASE_URL=https://api.openai.com/v1

# 后端服务配置（如果需要）
VITE_API_BASE_URL=http://localhost:3001
```

### 启动后端服务（可选）

如果需要完整功能（包括数据持久化），需要启动后端服务：

```bash
# 在组件库项目目录中
npm run dev:server
```

## 5. 部署注意事项

1. **静态部署**: 组件可以在纯前端环境中使用，但某些功能（如数据持久化）需要后端支持
2. **API 密钥**: 确保在生产环境中正确配置 API 密钥
3. **CORS**: 如果使用自定义后端，确保正确配置 CORS
4. **样式**: 确保 Tailwind CSS 正确配置并包含组件样式

## 故障排除

### 常见问题

1. **样式不显示**: 确保导入了 `@ai-chat/react-component/styles`
2. **Tailwind 类不生效**: 检查 `tailwind.config.js` 中的 `content` 配置
3. **TypeScript 错误**: 确保安装了正确的类型定义
4. **API 调用失败**: 检查环境变量和网络连接

### 调试技巧

```tsx
import { useChatStore } from '@ai-chat/react-component';

// 在组件中添加调试信息
const DebugInfo = () => {
  const store = useChatStore();
  
  if (process.env.NODE_ENV === 'development') {
    console.log('Chat Store State:', {
      sessions: store.sessions,
      currentSession: store.currentSession,
      messages: store.messages,
      isLoading: store.isLoading
    });
  }
  
  return null;
};
```