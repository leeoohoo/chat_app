import { ReactNode } from 'react';

// 基础消息类型
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';
export type MessageStatus = 'pending' | 'streaming' | 'completed' | 'error';
export type AttachmentType = 'image' | 'file' | 'audio';

// 主题类型
export type Theme = 'light' | 'dark' | 'auto';

// 消息接口
export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  rawContent?: string;
  summary?: string; // AI生成的内容总结
  tokensUsed?: number;
  status: MessageStatus;
  createdAt: Date;
  updatedAt?: Date;
  metadata?: {
    attachments?: Attachment[];
    toolCalls?: ToolCall[];
    contentSegments?: ContentSegment[];
    currentSegmentIndex?: number;
    model?: string;
    summary?: string; // AI生成的内容总结（也可以存储在这里）
    [key: string]: any;
  };
}

// 会话接口
export interface Session {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
  tokenUsage: number;
  tags?: string | null;
  pinned: boolean;
  archived: boolean;
  metadata?: string | null;
}

// 系统上下文接口
export interface SystemContext {
  id: string;
  name: string;
  content: string;
  userId: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// 附件接口
export interface Attachment {
  id: string;
  messageId: string;
  type: AttachmentType;
  name: string;
  url: string;
  size: number;
  mimeType: string;
  createdAt: Date;
}

// 工具调用接口
export interface ToolCall {
  id: string;
  messageId: string;
  name: string;
  arguments: Record<string, any>;
  result?: any;
  error?: string;
  createdAt: Date;
}

// 内容分段接口
export interface ContentSegment {
  content: string | ToolCall;
  type: 'text' | 'tool_call';
  toolCallId?: string;
}

// 聊天配置
export interface ChatConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string;
  enableMcp: boolean;
}

// MCP配置接口
export interface McpConfig {
  id: string;
  name: string;
  command: string;
  enabled: boolean;
  config?: any;
  createdAt: Date;
  updatedAt: Date;
}

// AI模型配置接口
export interface AiModelConfig {
  id: string;
  name: string;
  base_url: string;
  api_key: string;
  model_name: string;
  enabled: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// AI客户端配置
export interface AiClientConfig {
  apiKey: string;
  baseUrl?: string;
  model: string;
  temperature: number;
  maxTokens: number;
  systemPrompt?: string;
  enableStreaming: boolean;
}

// MCP工具配置
export interface McpToolConfig {
  name: string;
  command: string;
  enabled: boolean;
  timeout: number;
  retryCount: number;
}

// 流式响应接口
export interface StreamResponse {
  content: string;
  done: boolean;
  error?: string;
  metadata?: Record<string, any>;
}

// 错误类型
export interface ChatError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// 查询选项
export interface QueryOptions {
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  filters?: Record<string, any>;
}

// 搜索结果
export interface SearchResult<T> {
  items: T[];
  total: number;
  hasMore: boolean;
}

// 组件Props类型
export interface ChatInterfaceProps {
  className?: string;
  onSessionChange?: (sessionId: string) => void;
  onMessageSend?: (content: string, attachments?: Attachment[]) => void;
  customRenderer?: {
    renderMessage?: (message: Message) => ReactNode;
    renderAttachment?: (attachment: Attachment) => ReactNode;
    renderToolCall?: (toolCall: ToolCall) => ReactNode;
  };
}

export interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  onMessageEdit?: (messageId: string, content: string) => void;
  onMessageDelete?: (messageId: string) => void;
  customRenderer?: {
    renderMessage?: (message: Message) => ReactNode;
    renderAttachment?: (attachment: Attachment) => ReactNode;
  };
}

export interface InputAreaProps {
  onSend: (content: string, attachments?: File[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  maxLength?: number;
  allowAttachments?: boolean;
  supportedFileTypes?: string[];
  showModelSelector?: boolean;
  selectedModelId?: string | null;
  availableModels?: AiModelConfig[];
  onModelChange?: (modelId: string | null) => void;
}

export interface SessionListProps {
  isOpen?: boolean;
  onClose?: () => void;
  store?: any;
}

// 事件类型
export interface ChatEvents {
  onMessageReceived: (message: Message) => void;
  onMessageUpdated: (message: Message) => void;
  onSessionCreated: (session: Session) => void;
  onSessionUpdated: (session: Session) => void;
  onError: (error: ChatError) => void;
}

// 插件接口
export interface ChatPlugin {
  name: string;
  version: string;
  initialize: (config: Record<string, any>) => Promise<void>;
  destroy: () => Promise<void>;
  onMessage?: (message: Message) => Promise<Message | null>;
  onToolCall?: (toolCall: ToolCall) => Promise<any>;
}

// 数据库相关类型
export interface DatabaseOperations {
  // 会话操作
  createSession: (title: string) => Promise<Session>;
  getSession: (id: string) => Promise<Session | null>;
  updateSession: (id: string, updates: Partial<Session>) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  listSessions: () => Promise<Session[]>;

  // 消息操作
  createMessage: (message: Omit<Message, 'id' | 'createdAt'>) => Promise<Message>;
  getMessage: (id: string) => Promise<Message | null>;
  updateMessage: (id: string, updates: Partial<Message>) => Promise<void>;
  deleteMessage: (id: string) => Promise<void>;
  getSessionMessages: (sessionId: string) => Promise<Message[]>;
}

// 导出所有类型
export type {
  ReactNode,
};