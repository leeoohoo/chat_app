# @ai-chat/react-component

一个功能完整的React AI聊天组件，支持会话管理、MCP集成和SQLite持久化存储。

## 特性

- 🚀 **开箱即用** - 一个标签即可使用完整的AI聊天功能
- 💬 **会话管理** - 支持多会话切换、创建、删除和重命名
- 🤖 **AI模型支持** - 支持OpenAI GPT系列模型
- 🔧 **MCP集成** - 支持Model Context Protocol工具调用
- 💾 **数据持久化** - 基于SQLite的本地数据存储
- 🎨 **主题切换** - 支持明暗主题切换
- 📱 **响应式设计** - 适配各种屏幕尺寸
- 🔒 **类型安全** - 完整的TypeScript类型定义

## 🚀 快速开始

### 安装

```bash
npm install @ai-chat/react-component
# 或
yarn add @ai-chat/react-component
# 或
pnpm add @ai-chat/react-component
```

### 基础使用（推荐）

使用独立聊天组件，无需任何配置，开箱即用：

```tsx
import React from 'react';
import StandaloneChatInterface from '@ai-chat/react-component';
import '@ai-chat/react-component/styles';

function App() {
  return (
    <div className="h-screen w-full">
      <StandaloneChatInterface className="h-full" />
    </div>
  );
}

export default App;
```

## 高级配置

### 自定义事件处理

```tsx
import React from 'react';
import { ChatInterface, type Message, type Attachment } from '@ai-chat/react-component';

function App() {
  const handleMessageSend = (content: string, attachments?: Attachment[]) => {
    console.log('发送消息:', content, attachments);
  };

  const handleSessionChange = (sessionId: string) => {
    console.log('切换会话:', sessionId);
  };

  return (
    <ChatInterface
      onMessageSend={handleMessageSend}
      onSessionChange={handleSessionChange}
    />
  );
}
```

### 自定义渲染器

```tsx
import React from 'react';
import { ChatInterface, type Message, type Attachment } from '@ai-chat/react-component';

function App() {
  const customRenderer = {
    renderMessage: (message: Message) => (
      <div className="custom-message">
        {message.content}
      </div>
    ),
    renderAttachment: (attachment: Attachment) => (
      <div className="custom-attachment">
        {attachment.name}
      </div>
    ),
  };

  return (
    <ChatInterface customRenderer={customRenderer} />
  );
}
```

## 组件API

### ChatInterface

主要的聊天界面组件。

#### Props

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `className` | `string` | - | 自定义CSS类名 |
| `onMessageSend` | `(content: string, attachments?: Attachment[]) => void` | - | 消息发送回调 |
| `onSessionChange` | `(sessionId: string) => void` | - | 会话切换回调 |
| `customRenderer` | `CustomRenderer` | - | 自定义渲染器 |

### 其他组件

- `MessageList` - 消息列表组件
- `InputArea` - 输入区域组件
- `SessionList` - 会话列表组件
- `ThemeToggle` - 主题切换组件
- `McpManager` - MCP管理组件
- `AiModelManager` - AI模型管理组件

## Hooks

### useChatStore

聊天状态管理Hook。

```tsx
import { useChatStore } from '@ai-chat/react-component';

function MyComponent() {
  const {
    currentSession,
    messages,
    isLoading,
    sendMessage,
    createSession,
    switchSession,
  } = useChatStore();

  // 使用状态和方法
}
```

### useTheme

主题管理Hook。

```tsx
import { useTheme } from '@ai-chat/react-component';

function MyComponent() {
  const { theme, setTheme, actualTheme } = useTheme();

  return (
    <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
      切换到 {theme === 'light' ? '暗色' : '亮色'} 主题
    </button>
  );
}
```

## 配置

### 环境变量

在使用前，请确保设置以下环境变量：

```env
# OpenAI配置
VITE_OPENAI_API_KEY=your_openai_api_key
VITE_OPENAI_BASE_URL=https://api.openai.com/v1

# 服务器配置
VITE_API_BASE_URL=http://localhost:3001
```

### 数据库初始化

```tsx
import { initDatabase } from '@ai-chat/react-component';

// 在应用启动时初始化数据库
initDatabase().then(() => {
  console.log('数据库初始化完成');
});
```

## 样式定制

组件使用Tailwind CSS构建，你可以通过以下方式定制样式：

1. **覆盖CSS变量**

```css
:root {
  --chat-primary-color: #your-color;
  --chat-background-color: #your-background;
}
```

2. **使用自定义CSS类**

```tsx
<ChatInterface className="my-custom-chat" />
```

3. **主题定制**

```css
.dark {
  --chat-background: #1a1a1a;
  --chat-text: #ffffff;
}

.light {
  --chat-background: #ffffff;
  --chat-text: #000000;
}
```

## 类型定义

包含完整的TypeScript类型定义：

```tsx
import type {
  Message,
  Session,
  Attachment,
  ToolCall,
  ChatConfig,
  AiModelConfig,
  McpConfig,
  Theme,
  ChatInterfaceProps,
  MessageListProps,
  InputAreaProps,
  SessionListProps,
} from '@ai-chat/react-component';
```

## 许可证

MIT

## 贡献

欢迎提交Issue和Pull Request！

## 支持

如果你觉得这个项目有用，请给它一个⭐️！