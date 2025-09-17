import React from 'react';
import { StandaloneChatInterface } from '../components/StandaloneChatInterface';
import { createChatStore } from './store/createChatStore';
import ApiClient from './api/client';

export interface AiChatConfig {
  userId: string;
  projectId: string;
  baseUrl?: string;
  className?: string;
}

/**
 * AiChat 类 - 支持通过构造函数实例化的聊天组件
 * 
 * 使用方式:
 * ```typescript
 * const aiChat = new AiChat('user123', 'project456', 'http://localhost:3001/api');
 * 
 * // 在React组件中使用
 * function App() {
 *   return <div>{aiChat.render()}</div>;
 * }
 * ```
 */
export class AiChat {
  private userId: string;
  private projectId: string;
  private baseUrl: string;
  private apiClient: ApiClient;
  private store: ReturnType<typeof createChatStore>;
  private className?: string;

  constructor(userId: string, projectId: string, baseUrl?: string, className?: string) {
    this.userId = userId;
    this.projectId = projectId;
    this.baseUrl = baseUrl || 'http://localhost:3001/api';
    this.className = className;

    // 创建自定义的 API 客户端
    this.apiClient = new ApiClient(this.baseUrl);
    
    // 创建自定义的 store，传入 userId 和 projectId
    this.store = createChatStore(this.apiClient, {
      userId: this.userId,
      projectId: this.projectId
    });
  }

  /**
   * 渲染聊天界面
   * @returns React 元素
   */
  render(): React.ReactElement {
    return React.createElement(AiChatComponent, {
      className: this.className,
      userId: this.userId,
      projectId: this.projectId,
      baseUrl: this.baseUrl
    });
  }

  /**
   * 获取当前配置
   */
  getConfig(): AiChatConfig {
    return {
      userId: this.userId,
      projectId: this.projectId,
      baseUrl: this.baseUrl,
      className: this.className
    };
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<AiChatConfig>): void {
    if (config.userId) this.userId = config.userId;
    if (config.projectId) this.projectId = config.projectId;
    if (config.baseUrl) {
      this.baseUrl = config.baseUrl;
      this.apiClient = new ApiClient(this.baseUrl);
      this.store = createChatStore(this.apiClient, {
        userId: this.userId,
        projectId: this.projectId
      });
    }
    if (config.className !== undefined) this.className = config.className;
  }

  /**
   * 获取 store 实例（用于高级用法）
   */
  getStore() {
    return this.store;
  }

  /**
   * 获取 API 客户端实例（用于高级用法）
   */
  getApiClient() {
    return this.apiClient;
  }
}

/**
 * 内部组件，用于渲染聊天界面
 */
interface AiChatComponentProps {
  className?: string;
  userId: string;
  projectId: string;
  baseUrl: string;
}

const AiChatComponent: React.FC<AiChatComponentProps> = ({
  className,
  userId,
  projectId,
  baseUrl
}) => {
  return (
    <StandaloneChatInterface 
      className={className}
      apiBaseUrl={baseUrl}
      userId={userId}
      projectId={projectId}
    />
  );
};

export default AiChat;