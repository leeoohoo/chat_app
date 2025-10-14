// 测试后端集成的store功能
import { createChatStoreWithBackend } from './lib/store/createChatStoreWithBackend';

// 创建store实例
const store = createChatStoreWithBackend();

// 测试基本功能
async function testBackendStore() {
    console.log('🧪 开始测试后端集成的store...');
    
    try {
        // 测试1: 加载会话
        console.log('📋 测试加载会话...');
        await store.getState().loadSessions();
        console.log('✅ 会话加载成功');
        
        // 测试2: 加载AI模型配置
        console.log('🤖 测试加载AI模型配置...');
        await store.getState().loadAiModelConfigs();
        console.log('✅ AI模型配置加载成功');
        
        // 测试3: 加载MCP配置
        console.log('🔧 测试加载MCP配置...');
        await store.getState().loadMcpConfigs();
        console.log('✅ MCP配置加载成功');
        
        // 测试4: 加载系统上下文
        console.log('📝 测试加载系统上下文...');
        await store.getState().loadSystemContexts();
        console.log('✅ 系统上下文加载成功');
        
        // 获取当前状态
        const state = store.getState();
        console.log('📊 当前状态:', {
            sessions: state.sessions.length,
            aiModelConfigs: state.aiModelConfigs.length,
            mcpConfigs: state.mcpConfigs.length,
            systemContexts: state.systemContexts.length
        });
        
        console.log('🎉 所有测试通过！后端集成store工作正常');
        
    } catch (error) {
        console.error('❌ 测试失败:', error);
    }
}

// 如果直接运行此文件，执行测试
if (typeof window === 'undefined') {
    testBackendStore();
}

export { testBackendStore };