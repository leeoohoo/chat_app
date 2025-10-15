#!/usr/bin/env python3
"""
测试流式响应功能的脚本
验证修复后的消息保存是否正常工作
"""

import asyncio
import aiohttp
import json
import uuid

async def test_streaming_response():
    """测试流式响应功能"""
    
    # 创建一个新的会话
    session_id = str(uuid.uuid4())
    
    # 首先创建会话
    async with aiohttp.ClientSession() as session:
        # 创建会话
        create_session_url = f"http://localhost:8000/api/sessions"
        create_session_data = {
            "id": session_id,
            "title": "测试流式响应",
            "userId": "test_user"
        }
        
        async with session.post(create_session_url, json=create_session_data) as resp:
            if resp.status != 200:
                print(f"❌ 创建会话失败: {resp.status}")
                return
            print(f"✅ 会话创建成功: {session_id}")
        
        # 发送消息
        message_url = f"http://localhost:8000/api/sessions/{session_id}/messages"
        message_data = {
            "sessionId": session_id,
            "content": "你好，请简单介绍一下你自己",
            "role": "user"
        }
        
        async with session.post(message_url, json=message_data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                print(f"❌ 发送消息失败: {resp.status}")
                print(f"错误详情: {error_text}")
                return
            print(f"✅ 用户消息发送成功")
        
        # 测试流式响应
        stream_url = f"http://localhost:8000/api/chat/stream"
        stream_data = {
            "session_id": session_id,
            "content": "你好，请简单介绍一下你自己"
        }
        
        print(f"🔄 开始测试流式响应...")
        
        async with session.post(
            stream_url, 
            json=stream_data,
            headers={"Accept": "text/event-stream"}
        ) as resp:
            if resp.status != 200:
                print(f"❌ 流式响应请求失败: {resp.status}")
                text = await resp.text()
                print(f"错误内容: {text}")
                return
            
            print(f"✅ 流式响应开始 (状态码: {resp.status})")
            
            chunk_count = 0
            content_chunks = []
            events_received = []
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                print(f"🔍 原始行: {repr(line)}")
                
                if not line:
                    continue
                
                if line.startswith('data: '):
                    data_str = line[6:]  # 移除 'data: ' 前缀
                    print(f"🔍 数据字符串: {repr(data_str)}")
                    
                    if data_str == '[DONE]':
                        print(f"🎯 流式响应完成")
                        break
                    
                    try:
                        data = json.loads(data_str)
                        event_type = data.get('type')
                        events_received.append(event_type)
                        print(f"🔍 解析的事件: {data}")
                        
                        if event_type == 'chunk':
                            chunk_count += 1
                            content = data.get('data', {}).get('content', '')
                            if content:
                                content_chunks.append(content)
                                print(f"📝 接收到内容块 {chunk_count}: {content[:50]}...")
                        
                        elif event_type == 'complete':
                            print(f"✅ 接收到完成事件")
                        
                        elif event_type == 'error':
                            print(f"❌ 接收到错误事件: {data.get('data', {})}")
                        
                        else:
                            print(f"📡 接收到事件: {event_type}")
                    
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON解析错误: {e}, 数据: {data_str}")
                else:
                    print(f"🔍 非数据行: {line}")
            
            # 输出测试结果
            print(f"\n📊 测试结果:")
            print(f"   - 接收到的内容块数量: {chunk_count}")
            print(f"   - 接收到的事件类型: {events_received}")
            print(f"   - 完整内容长度: {len(''.join(content_chunks))}")
            
            if chunk_count > 0 and 'complete' in events_received:
                print(f"🎉 流式响应测试成功！")
            else:
                print(f"❌ 流式响应测试失败")

if __name__ == "__main__":
    asyncio.run(test_streaming_response())