// 主要组件 - 独立聊天界面（推荐使用）
export { default as StandaloneChatInterface } from './components/StandaloneChatInterface';

// 其他组件（高级用法）
export { ChatInterface } from './components/ChatInterface';
export { MessageList } from './components/MessageList';
export { MessageItem } from './components/MessageItem';
export { InputArea } from './components/InputArea';
export { SessionList } from './components/SessionList';
export { ThemeToggle } from './components/ThemeToggle';
export { default as McpManager } from './components/McpManager';
export { default as AiModelManager } from './components/AiModelManager';
export { default as SystemContextEditor } from './components/SystemContextEditor';
export { AttachmentRenderer } from './components/AttachmentRenderer';
export { ToolCallRenderer } from './components/ToolCallRenderer';
export { MarkdownRenderer } from './components/MarkdownRenderer';
export { LoadingSpinner } from './components/LoadingSpinner';
export { ErrorBoundary } from './components/ErrorBoundary';

// UI组件导出
export * from './components/ui/icons';

// Hooks导出
export { useTheme } from './hooks/useTheme';

// Store导出
export { useChatStore } from './lib/store';

// 服务导出
export * from './lib/services';
export * from './lib/api';

// 数据库导出（避免类型冲突）
export { initDatabase, getDatabase } from './lib/database';

// 工具函数导出
export * from './lib/utils';

// 类型导出
export type * from './types';

// 样式导出
import './styles/index.css';

// 默认导出 - 独立聊天界面组件（推荐使用）
export { default } from './components/StandaloneChatInterface';

// Provider组件导出（如果存在）
// export * from './components/providers';

// 版本信息
export const version = '1.0.0';

// 配置类型
export type {
  ChatConfig,
  AiModelConfig,
  McpConfig,
  Theme,
  ChatInterfaceProps,
  MessageListProps,
  InputAreaProps,
  SessionListProps
} from './types';