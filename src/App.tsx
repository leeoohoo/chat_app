import { useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { useTheme } from './hooks/useTheme';
import './styles/index.css';

function App() {
  const { actualTheme } = useTheme();

  // 确保主题正确应用
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(actualTheme);
  }, [actualTheme]);

  return (
    <div className="App">
      <ChatInterface />
    </div>
  );
}

export default App;