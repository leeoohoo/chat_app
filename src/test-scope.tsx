import React, { useEffect } from 'react';
import { useChatStoreFromContext } from './lib/store/ChatStoreContext';

const TestScope: React.FC = () => {
    const { loadSessions, createSession } = useChatStoreFromContext();
    
    useEffect(() => {
        console.log('🧪 开始作用域测试 - 使用Context中的store');
        
        // 测试loadSessions
        console.log('🔄 调用 loadSessions...');
        loadSessions();
        
        // 测试createSession
        setTimeout(() => {
            console.log('🔄 调用 createSession...');
            createSession('测试会话');
        }, 1000);
        
    }, [loadSessions, createSession]);

    return (
        <div style={{ padding: '20px' }}>
            <h1>作用域测试页面</h1>
            <p>请打开浏览器控制台查看调试日志</p>
            <p>查看 getSessionParams 函数是否能正确访问 userId 和 projectId</p>
        </div>
    );
};

export default TestScope;