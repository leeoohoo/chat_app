import React, { createContext, useContext, ReactNode } from 'react';
import { createChatStoreWithConfig, useChatStore } from './index';
import type ApiClient from '../api/client';

// Store类型定义
type ChatStore = typeof useChatStore;

// Context接口
interface ChatStoreContextType {
  store: ChatStore;
}

// 创建Context
const ChatStoreContext = createContext<ChatStoreContextType | null>(null);

// Provider Props
interface ChatStoreProviderProps {
  children: ReactNode;
  userId?: string;
  projectId?: string;
  customApiClient?: ApiClient;
}

// Provider组件
export const ChatStoreProvider: React.FC<ChatStoreProviderProps> = ({
  children,
  userId,
  projectId,
  customApiClient
}) => {
  // 根据是否有自定义参数决定使用哪个store
  const store = React.useMemo(() => {
    if (userId || projectId || customApiClient) {
      console.log('🏪 创建自定义store:', { userId, projectId, hasCustomApiClient: !!customApiClient });
      return createChatStoreWithConfig(
        userId || 'default-user',
        projectId || 'default-project',
        customApiClient
      );
    } else {
      console.log('🏪 使用默认store');
      return useChatStore;
    }
  }, [userId, projectId, customApiClient]);

  return (
    <ChatStoreContext.Provider value={{ store }}>
      {children}
    </ChatStoreContext.Provider>
  );
};

// Hook来使用Context
export const useChatStoreContext = (): ChatStore => {
  const context = useContext(ChatStoreContext);
  if (!context) {
    throw new Error('useChatStoreContext must be used within a ChatStoreProvider');
  }
  return context.store;
};

// 为了向后兼容，导出一个hook来获取store的状态和方法
export const useChatStoreFromContext = () => {
  const store = useChatStoreContext();
  return store();
};