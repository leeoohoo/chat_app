import React from 'react';
import { StandaloneChatInterface } from '../components/StandaloneChatInterface';
import { createChatStoreWithBackend } from './store/createChatStoreWithBackend';
import ApiClient from './api/client';

export interface AiChatConfig {
  userId: string;
  projectId: string;
  configUrl?: string;
  className?: string;
  showMcpManager?: boolean;
  showAiModelManager?: boolean;
  showSystemContextEditor?: boolean;
  showAgentManager?: boolean;
  showApplicationsButton?: boolean;
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
  private store: ReturnType<typeof createChatStoreWithBackend>;
  private className?: string;
  private showMcpManager: boolean;
  private showAiModelManager: boolean;
  private showSystemContextEditor: boolean;
  private showAgentManager: boolean;
  private showApplicationsButton: boolean;

  constructor(
    userId: string, 
    projectId: string, 
    configUrl?: string, 
    className?: string,
    showMcpManager: boolean = true,
    showAiModelManager: boolean = true,
    showSystemContextEditor: boolean = true,
    showAgentManager: boolean = true,
    showApplicationsButton: boolean = true
  ) {
    this.userId = userId;
    this.projectId = projectId;
    this.configUrl = configUrl || '/api';
    this.className = className;
    this.showMcpManager = showMcpManager;
    this.showAiModelManager = showAiModelManager;
    this.showSystemContextEditor = showSystemContextEditor;
    this.showAgentManager = showAgentManager;
    this.showApplicationsButton = showApplicationsButton;

    console.log('🔧 AiChat Constructor - configUrl:', this.configUrl);
    console.log('🔧 AiChat Constructor - Module Controls:', {
      showMcpManager: this.showMcpManager,
      showAiModelManager: this.showAiModelManager,
      showSystemContextEditor: this.showSystemContextEditor,
      showAgentManager: this.showAgentManager,
      showApplicationsButton: this.showApplicationsButton
    });

    // 创建自定义的 API 客户端
    this.apiClient = new ApiClient(this.configUrl);
    
    // 创建自定义的 store，传入 userId、projectId 和 configUrl
    this.store = createChatStoreWithBackend(this.apiClient, {
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
      configUrl: this.configUrl,
      showMcpManager: this.showMcpManager,
      showAiModelManager: this.showAiModelManager,
      showSystemContextEditor: this.showSystemContextEditor,
      showAgentManager: this.showAgentManager,
      showApplicationsButton: this.showApplicationsButton
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
      className: this.className,
      showMcpManager: this.showMcpManager,
      showAiModelManager: this.showAiModelManager,
      showSystemContextEditor: this.showSystemContextEditor,
      showAgentManager: this.showAgentManager,
      showApplicationsButton: this.showApplicationsButton
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
      this.store = createChatStoreWithBackend(this.apiClient, {
        userId: this.userId,
        projectId: this.projectId,
        configUrl: this.configUrl
      });
    }
    if (config.className !== undefined) this.className = config.className;
    if (config.showMcpManager !== undefined) this.showMcpManager = config.showMcpManager;
    if (config.showAiModelManager !== undefined) this.showAiModelManager = config.showAiModelManager;
    if (config.showSystemContextEditor !== undefined) this.showSystemContextEditor = config.showSystemContextEditor;
    if (config.showAgentManager !== undefined) this.showAgentManager = config.showAgentManager;
    if (config.showApplicationsButton !== undefined) this.showApplicationsButton = config.showApplicationsButton;
  }

  /**
   * 获取 store 实例（用于高级用法）
   */
  getStore(): import('./store/createChatStoreWithBackend').ChatStore {
    return this.store;
  }

  /**
   * 获取 API 客户端实例（用于高级用法）
   */
  getApiClient(): ApiClient {
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
  showMcpManager?: boolean;
  showAiModelManager?: boolean;
  showSystemContextEditor?: boolean;
  showAgentManager?: boolean;
  showApplicationsButton?: boolean;
}

const AiChatComponent: React.FC<AiChatComponentProps> = ({
  className,
  userId,
  projectId,
  configUrl,
  showMcpManager,
  showAiModelManager,
  showSystemContextEditor,
  showAgentManager,
  showApplicationsButton
}) => {
  return (
    <StandaloneChatInterface 
      className={className}
      apiBaseUrl={configUrl}
      userId={userId}
      projectId={projectId}
      showMcpManager={showMcpManager}
      showAiModelManager={showAiModelManager}
      showSystemContextEditor={showSystemContextEditor}
      showAgentManager={showAgentManager}
      showApplicationsButton={showApplicationsButton}
    />
  );
};

export default AiChat;