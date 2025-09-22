import React from 'react';
import { StandaloneChatInterface } from '../components/StandaloneChatInterface';
import { createChatStore } from './store/createChatStore';
import ApiClient from './api/client';

export interface AiChatConfig {
  userId: string;
  projectId: string;
  configUrl?: string;
  className?: string;
}

/**
 * AiChat 类 - 支持通过构造函数实例化的聊天组件
 * 
 * 使用方式:
 * ```typescript
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
  private configUrl: string;
  private apiClient: ApiClient;
  private store: ReturnType<typeof createChatStore>;
  private className?: string;

  constructor(userId: string, projectId: string, configUrl?: string, className?: string) {
    this.userId = userId;
    this.projectId = projectId;
    this.configUrl = configUrl || '/api';
    this.className = className;

    console.log('🔧 AiChat Constructor - configUrl:', this.configUrl);

    // 创建自定义的 API 客户端
    this.apiClient = new ApiClient(this.configUrl);
    
    // 创建自定义的 store，传入 userId、projectId 和 configUrl
    this.store = createChatStore(this.apiClient, {
      userId: this.userId,
      projectId: this.projectId,
      configUrl: this.configUrl
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
      configUrl: this.configUrl
    });
  }

  /**
   * 获取当前配置
   */
  getConfig(): AiChatConfig {
    return {
      userId: this.userId,
      projectId: this.projectId,
      configUrl: this.configUrl,
      className: this.className
    };
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<AiChatConfig>): void {
    if (config.userId) this.userId = config.userId;
    if (config.projectId) this.projectId = config.projectId;
    if (config.configUrl) {
      this.configUrl = config.configUrl;
      this.apiClient = new ApiClient(this.configUrl);
      this.store = createChatStore(this.apiClient, {
        userId: this.userId,
        projectId: this.projectId,
        configUrl: this.configUrl
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
  configUrl: string;
}

const AiChatComponent: React.FC<AiChatComponentProps> = ({
  className,
  userId,
  projectId,
  configUrl
}) => {
  return (
    <StandaloneChatInterface 
      className={className}
      apiBaseUrl={configUrl}
      userId={userId}
      projectId={projectId}
    />
  );
};

export default AiChat;