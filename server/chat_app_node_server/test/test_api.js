/**
 * API 测试脚本
 */

const baseUrl = 'http://localhost:3001';

async function testAPI() {
  console.log('开始测试 API...\n');

  try {
    // 1. 测试健康检查
    console.log('1. 测试健康检查端点...');
    const healthRes = await fetch(`${baseUrl}/health`);
    const healthData = await healthRes.json();
    console.log('✓ 健康检查成功:', healthData);
    console.log('');

    // 2. 创建会话
    console.log('2. 创建新会话...');
    const createSessionRes = await fetch(`${baseUrl}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: 'Python 编程讨论',
        description: '讨论 Python 最佳实践',
        user_id: 'user_123',
        project_id: 'project_456'
      })
    });
    const session = await createSessionRes.json();
    console.log('✓ 会话创建成功:', session);
    console.log('');

    const sessionId = session.id;

    // 3. 获取会话列表
    console.log('3. 获取会话列表...');
    const sessionsRes = await fetch(`${baseUrl}/api/sessions`);
    const sessions = await sessionsRes.json();
    console.log(`✓ 获取到 ${sessions.length} 个会话`);
    console.log('');

    // 4. 创建消息
    console.log('4. 创建用户消息...');
    const createMsgRes = await fetch(`${baseUrl}/api/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: sessionId,
        role: 'user',
        content: '你好，请帮我分析一段代码'
      })
    });
    const userMsg = await createMsgRes.json();
    console.log('✓ 用户消息创建成功:', userMsg);
    console.log('');

    // 5. 创建助手消息
    console.log('5. 创建助手消息...');
    const createAssistantMsgRes = await fetch(`${baseUrl}/api/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: sessionId,
        role: 'assistant',
        content: '当然可以！请把代码发给我。'
      })
    });
    const assistantMsg = await createAssistantMsgRes.json();
    console.log('✓ 助手消息创建成功:', assistantMsg);
    console.log('');

    // 6. 获取会话的所有消息
    console.log('6. 获取会话的所有消息...');
    const messagesRes = await fetch(`${baseUrl}/api/messages?session_id=${sessionId}`);
    const messages = await messagesRes.json();
    console.log(`✓ 获取到 ${messages.length} 条消息:`);
    messages.forEach((msg, idx) => {
      console.log(`  ${idx + 1}. [${msg.role}] ${msg.content}`);
    });
    console.log('');

    // 7. 更新会话
    console.log('7. 更新会话...');
    const updateSessionRes = await fetch(`${baseUrl}/api/sessions/${sessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: 'Python 编程讨论 - 已更新',
        description: '讨论 Python 最佳实践和代码审查'
      })
    });
    const updatedSession = await updateSessionRes.json();
    console.log('✓ 会话更新成功:', updatedSession.title);
    console.log('');

    // 8. 获取特定会话
    console.log('8. 获取特定会话...');
    const getSessionRes = await fetch(`${baseUrl}/api/sessions/${sessionId}`);
    const retrievedSession = await getSessionRes.json();
    console.log('✓ 会话获取成功:', retrievedSession.title);
    console.log('');

    console.log('✅ 所有测试通过！\n');

    // 清理（可选）
    console.log('清理测试数据...');
    await fetch(`${baseUrl}/api/sessions/${sessionId}`, { method: 'DELETE' });
    console.log('✓ 测试数据已清理');

  } catch (error) {
    console.error('❌ 测试失败:', error);
    process.exit(1);
  }
}

// 运行测试
console.log('请确保服务器已启动（npm start）\n');
testAPI();
