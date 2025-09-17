# AI Chat React Component 使用指南

这是一个完整的 React AI 聊天组件库，支持会话管理、MCP 协议和 SQLite 持久化。

## 安装

```bash
npm install @ai-chat/react-component
```

## 基本使用

### 1. 最简单的使用方式（推荐）

```tsx
import React from 'react';
import AIChatComponent from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

function App() {
  return (
    <div className="h-screen">
      <AIChatComponent />
    </div>
  );
}

export default App;
```

### 2. 使用具名导入

```tsx
import React from 'react';
import { StandaloneChatInterface } from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

function App() {
  return (
    <div className="h-screen">
      <StandaloneChatInterface />
    </div>
  );
}

export default App;
```

### 3. 高级用法 - 自定义配置

```tsx
import React from 'react';
import { 
  ChatInterface, 
  useChatStore, 
  ThemeToggle 
} from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

function App() {
  const { 
    sessions, 
    currentSession, 
    createSession, 
    switchSession 
  } = useChatStore();

  return (
    <div className="h-screen flex">
      {/* 侧边栏 */}
      <div className="w-64 bg-gray-100 p-4">
        <ThemeToggle />
        <button 
          onClick={() => createSession('新对话')}
          className="w-full mt-4 p-2 bg-blue-500 text-white rounded"
        >
          新建对话
        </button>
        
        {/* 会话列表 */}
        <div className="mt-4">
          {sessions.map(session => (
            <div 
              key={session.id}
              onClick={() => switchSession(session.id)}
              className={`p-2 cursor-pointer rounded ${
                currentSession?.id === session.id 
                  ? 'bg-blue-200' 
                  : 'hover:bg-gray-200'
              }`}
            >
              {session.title}
            </div>
          ))}
        </div>
      </div>
      
      {/* 聊天界面 */}
      <div className="flex-1">
        <ChatInterface />
      </div>
    </div>
  );
}

export default App;
```

## 组件说明

### 主要组件

- **`StandaloneChatInterface`** (推荐): 完整的独立聊天界面，包含所有功能
- **`ChatInterface`**: 核心聊天界面组件
- **`MessageList`**: 消息列表组件
- **`InputArea`**: 输入区域组件
- **`SessionList`**: 会话列表组件
- **`ThemeToggle`**: 主题切换组件

### 管理组件

- **`AiModelManager`**: AI 模型管理
- **`McpManager`**: MCP 配置管理
- **`SystemContextEditor`**: 系统上下文编辑器

### 工具组件

- **`MarkdownRenderer`**: Markdown 渲染器
- **`AttachmentRenderer`**: 附件渲染器
- **`ToolCallRenderer`**: 工具调用渲染器
- **`LoadingSpinner`**: 加载动画
- **`ErrorBoundary`**: 错误边界

## Hooks

- **`useTheme`**: 主题管理
- **`useChatStore`**: 聊天状态管理

## 样式

组件使用 Tailwind CSS 构建，你需要在项目中引入样式文件：

```tsx
import '@ai-chat/react-component/styles';
```

## TypeScript 支持

组件库完全支持 TypeScript，所有类型都已导出：

```tsx
import type { 
  ChatConfig,
  AiModelConfig,
  McpConfig,
  Theme,
  Message,
  Session
} from '@ai-chat/react-component';
```

## 注意事项

1. 确保你的项目已安装 React 18+
2. 组件需要在支持 Tailwind CSS 的环境中使用
3. 某些功能需要后端 API 支持
4. 数据库功能需要在 Node.js 环境中运行

## 完整示例

查看 `examples/` 目录获取更多完整的使用示例。