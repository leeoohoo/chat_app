/**
 * 流式聊天测试脚本
 */

const baseUrl = 'http://localhost:3001';

async function testStreamChat() {
  console.log('开始测试流式聊天 API...\n');

  try {
    // 1. 创建测试会话
    console.log('1. 创建测试会话...');
    const createSessionRes = await fetch(`${baseUrl}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: '流式聊天测试',
        description: '测试 Chat API v2'
      })
    });
    const session = await createSessionRes.json();
    console.log(`✓ 会话创建成功: ${session.id}\n`);

    const sessionId = session.id;

    // 2. 测试状态端点
    console.log('2. 测试状态端点...');
    const statusRes = await fetch(`${baseUrl}/api/agent_v2/status`);
    const status = await statusRes.json();
    console.log('✓ 状态:', status);
    console.log('');

    // 3. 测试流式聊天（不使用工具）
    console.log('3. 测试流式聊天（不使用 OpenAI，仅测试流程）...');
    console.log('发送消息: "你好"\n');

    const chatRes = await fetch(`${baseUrl}/api/agent_v2/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        content: '你好',
        ai_model_config: {
          model_name: 'gpt-4o-mini',
          temperature: 0.7,
          use_tools: false
        }
      })
    });

    if (!chatRes.ok) {
      const error = await chatRes.json();
      throw new Error(error.error || '请求失败');
    }

    // 处理 SSE 流
    console.log('接收流式响应：\n');
    const reader = chatRes.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';
    let receivedChunks = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // 保留最后一行（可能不完整）
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6);

          if (dataStr === '[DONE]') {
            console.log('\n✓ 流式响应结束');
            break;
          }

          try {
            const data = JSON.parse(dataStr);

            switch (data.type) {
              case 'start':
                console.log(`[${data.type}] 会话: ${data.session_id}`);
                break;
              case 'chunk':
                process.stdout.write(data.content);
                receivedChunks++;
                break;
              case 'thinking':
                console.log(`\n[思考] ${data.content}`);
                break;
              case 'tools_start':
                console.log(`\n[工具调用开始] ${data.data.tool_calls.length} 个工具`);
                break;
              case 'tools_stream':
                console.log(`[工具流] ${data.data.name}: ${data.data.content?.substring(0, 50)}...`);
                break;
              case 'tools_end':
                console.log(`[工具调用完成] ${data.data.tool_results.length} 个结果`);
                break;
              case 'complete':
                console.log(`\n\n[完成] 迭代次数: ${data.result?.iteration || 0}`);
                break;
              case 'error':
                console.error(`\n[错误] ${data.data.error}`);
                break;
              default:
                console.log(`[${data.type}]`, data);
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }

    console.log(`\n接收到 ${receivedChunks} 个文本块\n`);

    // 4. 验证消息已保存
    console.log('4. 验证消息已保存到数据库...');
    const messagesRes = await fetch(`${baseUrl}/api/messages?session_id=${sessionId}`);
    const messages = await messagesRes.json();
    console.log(`✓ 会话包含 ${messages.length} 条消息:`);
    messages.forEach((msg, idx) => {
      console.log(`  ${idx + 1}. [${msg.role}] ${msg.content?.substring(0, 50)}${msg.content?.length > 50 ? '...' : ''}`);
    });
    console.log('');

    // 清理
    console.log('清理测试数据...');
    await fetch(`${baseUrl}/api/sessions/${sessionId}`, { method: 'DELETE' });
    console.log('✓ 测试数据已清理\n');

    console.log('✅ 流式聊天测试完成！\n');

  } catch (error) {
    console.error('\n❌ 测试失败:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// 运行测试
console.log('请确保：');
console.log('1. 服务器已启动（npm start）');
console.log('2. 已设置 OPENAI_API_KEY 环境变量\n');

testStreamChat();
