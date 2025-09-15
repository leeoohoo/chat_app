import React, { useState, useEffect } from 'react';
import { useChatStore, useSessions, useCurrentSession, useSidebarOpen } from '../lib/store';
import { SessionList } from './SessionList';

// 简化的图标组件
const Bars3Icon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
  </svg>
);

const XMarkIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
);

interface SessionManagerProps {
  children?: React.ReactNode;
}

export const SessionManager: React.FC<SessionManagerProps> = ({ children }) => {
  const sessions = useSessions();
  const currentSession = useCurrentSession();
  const sidebarOpen = useSidebarOpen();
  const store = useChatStore();
  const { loadSessions, toggleSidebar } = store;
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 检测移动设备
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 加载会话列表
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleToggleSidebar = () => {
    if (isMobile) {
      setIsModalOpen(!isModalOpen);
    } else {
      toggleSidebar();
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* 桌面端侧边栏 */}
      {!isMobile && sidebarOpen && (
        <div className="w-80 flex-shrink-0">
          <SessionList />
        </div>
      )}

      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部栏 */}
        <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <button
              onClick={handleToggleSidebar}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title={isMobile ? '打开会话列表' : sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
            >
              <Bars3Icon className="w-5 h-5" />
            </button>
            
            {currentSession && (
              <div className="flex-1 min-w-0">
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                  {currentSession.title}
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {sessions.length} 个会话
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 聊天内容 */}
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </div>

      {/* 移动端模态框 */}
      {isModalOpen && isMobile && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* 背景遮罩 */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-25 transition-opacity"
            onClick={handleCloseModal}
          />
          
          {/* 模态框内容 */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white dark:bg-gray-900 shadow-xl transition-all">
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  会话管理
                </h3>
                <button
                  onClick={handleCloseModal}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-5 h-5" />
                </button>
              </div>
              <div className="h-96">
                <SessionList onClose={handleCloseModal} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};