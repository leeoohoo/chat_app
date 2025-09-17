import { createChatStore } from './createChatStore';
import type ApiClient from '../api/client';

// 默认的store实例（使用默认参数）
export const useChatStore = createChatStore();

// 创建带有自定义参数的store实例的函数
export function createChatStoreWithConfig(userId: string, projectId: string, customApiClient?: ApiClient) {
    return createChatStore(customApiClient, { userId, projectId });
}

// 导出选择器hooks
export const useCurrentSession = () => useChatStore((state) => state.currentSession);
export const useMessages = () => useChatStore((state) => state.messages);
export const useSessions = () => useChatStore((state) => state.sessions);
export const useIsLoading = () => useChatStore((state) => state.isLoading);
export const useIsStreaming = () => useChatStore((state) => state.isStreaming);
export const useTheme = () => useChatStore((state) => state.theme);
export const useSidebarOpen = () => useChatStore((state) => state.sidebarOpen);
export const useError = () => useChatStore((state) => state.error);
export const useAiModelConfigs = () => useChatStore((state) => state.aiModelConfigs);
export const useSelectedModelId = () => useChatStore((state) => state.selectedModelId);