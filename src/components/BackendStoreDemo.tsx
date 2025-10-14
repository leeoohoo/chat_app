import React, { useState, useEffect } from 'react';
import { createChatStoreWithBackend } from '../lib/store/createChatStoreWithBackend';

// 创建store实例
const backendStore = createChatStoreWithBackend();

export const BackendStoreDemo: React.FC = () => {
    const [testResults, setTestResults] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [storeState, setStoreState] = useState<any>(null);

    // 订阅store状态变化
    useEffect(() => {
        const unsubscribe = backendStore.subscribe((state) => {
            const selectedModel = state.selectedModelId 
                ? state.aiModelConfigs.find(model => model.id === state.selectedModelId)
                : null;
            
            setStoreState({
                sessions: state.sessions.length,
                messages: state.messages.length,
                aiModelConfigs: state.aiModelConfigs.length,
                mcpConfigs: state.mcpConfigs.length,
                systemContexts: state.systemContexts.length,
                selectedModel: selectedModel ? selectedModel.name : '未选择',
                isLoading: state.isLoading,
                isStreaming: state.isStreaming,
                error: state.error
            });
        });

        return unsubscribe;
    }, []);

    const addTestResult = (message: string) => {
        setTestResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
    };

    const testBackendIntegration = async () => {
        setIsLoading(true);
        setTestResults([]);
        
        try {
            addTestResult('🧪 开始测试后端集成...');
            
            // 测试1: 加载会话
            addTestResult('📋 测试加载会话...');
            await backendStore.getState().loadSessions();
            addTestResult('✅ 会话加载成功');
            
            // 测试2: 加载AI模型配置
            addTestResult('🤖 测试加载AI模型配置...');
            await backendStore.getState().loadAiModelConfigs();
            addTestResult('✅ AI模型配置加载成功');
            
            // 测试3: 加载MCP配置
            addTestResult('🔧 测试加载MCP配置...');
            await backendStore.getState().loadMcpConfigs();
            addTestResult('✅ MCP配置加载成功');
            
            // 测试4: 加载系统上下文
            addTestResult('📝 测试加载系统上下文...');
            await backendStore.getState().loadSystemContexts();
            addTestResult('✅ 系统上下文加载成功');
            
            addTestResult('🎉 所有测试通过！后端集成store工作正常');
            
        } catch (error) {
            addTestResult(`❌ 测试失败: ${error instanceof Error ? error.message : String(error)}`);
        } finally {
            setIsLoading(false);
        }
    };

    const testSendMessage = async () => {
        try {
            addTestResult('💬 测试发送消息...');
            
            // 首先确保有一个会话
            const state = backendStore.getState();
            if (state.sessions.length === 0) {
                addTestResult('📝 创建新会话...');
                await state.createSession('测试会话');
            }
            
            // 选择第一个会话
            if (state.sessions.length > 0) {
                await state.selectSession(state.sessions[0].id);
                addTestResult('📋 已选择会话');
                
                // 确保选择了AI模型
                if (!state.selectedModelId && state.aiModelConfigs.length > 0) {
                    const firstEnabledModel = state.aiModelConfigs.find(model => model.enabled);
                    if (firstEnabledModel) {
                        state.setSelectedModel(firstEnabledModel.id);
                        addTestResult(`🤖 已选择AI模型: ${firstEnabledModel.name}`);
                    } else {
                        addTestResult('❌ 没有可用的AI模型配置');
                        return;
                    }
                } else if (state.selectedModelId) {
                    const selectedModel = state.aiModelConfigs.find(model => model.id === state.selectedModelId);
                    addTestResult(`🤖 当前选择的AI模型: ${selectedModel?.name || '未知'}`);
                }
                
                // 发送测试消息
                await state.sendMessage('这是一条测试消息，用于验证后端API集成');
                addTestResult('✅ 消息发送成功');
            } else {
                addTestResult('❌ 无法创建或选择会话');
            }
            
        } catch (error) {
            addTestResult(`❌ 发送消息失败: ${error instanceof Error ? error.message : String(error)}`);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">后端集成Store测试</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 控制面板 */}
                <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-semibold mb-4">测试控制</h2>
                    <div className="space-y-3">
                        <button
                            onClick={testBackendIntegration}
                            disabled={isLoading}
                            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white px-4 py-2 rounded"
                        >
                            {isLoading ? '测试中...' : '测试后端集成'}
                        </button>
                        
                        <button
                            onClick={testSendMessage}
                            disabled={isLoading}
                            className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white px-4 py-2 rounded"
                        >
                            测试发送消息
                        </button>
                    </div>
                </div>
                
                {/* 状态显示 */}
                <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-semibold mb-4">Store状态</h2>
                    {storeState && (
                        <div className="space-y-2 text-sm">
                            <div>会话数量: {storeState.sessions}</div>
                            <div>消息数量: {storeState.messages}</div>
                            <div>AI模型配置: {storeState.aiModelConfigs}</div>
                            <div>当前选择模型: {storeState.selectedModel}</div>
                            <div>MCP配置: {storeState.mcpConfigs}</div>
                            <div>系统上下文: {storeState.systemContexts}</div>
                            <div>加载中: {storeState.isLoading ? '是' : '否'}</div>
                            <div>流式传输: {storeState.isStreaming ? '是' : '否'}</div>
                            {storeState.error && (
                                <div className="text-red-500">错误: {storeState.error}</div>
                            )}
                        </div>
                    )}
                </div>
            </div>
            
            {/* 测试结果 */}
            <div className="mt-6 bg-white rounded-lg shadow p-4">
                <h2 className="text-lg font-semibold mb-4">测试结果</h2>
                <div className="bg-gray-100 rounded p-3 h-64 overflow-y-auto">
                    {testResults.length === 0 ? (
                        <div className="text-gray-500">点击上方按钮开始测试...</div>
                    ) : (
                        testResults.map((result, index) => (
                            <div key={index} className="text-sm mb-1 font-mono">
                                {result}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};