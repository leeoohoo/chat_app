import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { useTheme } from './hooks/useTheme';
import { ChatStoreProvider } from './lib/store/ChatStoreContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import './styles/index.css';

interface AppProps {
  userId?: string;
  projectId?: string;
}

function App({ userId = 'custom_user_123', projectId = 'custom_project_456' }: AppProps = {}) {
  const { actualTheme } = useTheme();

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
          <ChatInterface />
        </div>
      </ChatStoreProvider>
    </ErrorBoundary>
  );
}

export default App;