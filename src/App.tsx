import { useEffect, useState } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { BackendStoreDemo } from './components/BackendStoreDemo';
import { useTheme } from './hooks/useTheme';
import { ChatStoreProvider } from './lib/store/ChatStoreContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import TestScope from './test-scope';
import './styles/index.css';

interface AppProps {
  userId?: string;
  projectId?: string;
}

function App({ userId = 'custom_user_123', projectId = 'custom_project_456' }: AppProps = {}) {
  const { actualTheme } = useTheme();
  const [showDemo, setShowDemo] = useState(false);

  // 调试日志
  console.log('🔍 App组件接收到的参数:', { userId, projectId });

  // 确保主题正确应用
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(actualTheme);
  }, [actualTheme]);

  return (
    <ErrorBoundary>
      <ChatStoreProvider userId={userId} projectId={projectId}>
        <div className="App">
          {/* 切换按钮 */}
          <div className="fixed top-4 right-4 z-50">
            <button
              onClick={() => setShowDemo(!showDemo)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded shadow-lg"
            >
              {showDemo ? '返回聊天' : '测试后端Store'}
            </button>
          </div>
          
          {showDemo ? (
            <BackendStoreDemo />
          ) : (
            <>
              <TestScope />
              <ChatInterface />
            </>
          )}
        </div>
      </ChatStoreProvider>
    </ErrorBoundary>
  );
}

export default App;