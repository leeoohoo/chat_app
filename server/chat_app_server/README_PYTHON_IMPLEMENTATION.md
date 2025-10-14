# Python聊天服务器实现

这是基于TypeScript版本的Python实现，提供了完整的流式聊天API接口。

## 架构概述

### 核心组件

1. **AiClient** (`app/services/ai_client.py`)
   - 负责与OpenAI API交互
   - 处理流式响应和工具调用
   - 管理对话流程

2. **AiRequestHandler** (`app/services/ai_request_handler.py`)
   - 处理OpenAI API请求
   - 格式化消息和处理流式响应
   - 管理请求中止状态

3. **MessageManager** (`app/services/message_manager.py`)
   - 统一的消息保存管理器
   - 避免重复保存消息
   - 提供消息缓存功能

4. **ToolResultProcessor** (`app/services/tool_result_processor.py`)
   - 处理工具执行结果
   - 生成内容摘要（当结果过长时）
   - 支持流式摘要输出

5. **McpToolExecute** (`app/services/mcp_tool_execute.py`)
   - MCP工具执行器
   - 支持流式和非流式工具执行
   - 管理工具注册和调用

6. **AiServer** (`app/services/ai_server.py`)
   - 协调所有组件
   - 提供统一的聊天接口
   - 处理回调事件

## API接口

### 流式聊天接口

#### POST `/api/chat/stream`
发送用户消息并返回AI的流式响应。

**请求体：**
```json
{
  "session_id": "string",
  "content": "string",
  "model_config": {
    "model_name": "string",
    "temperature": 0.7,
    "max_tokens": 1000,
    "api_key": "string",
    "base_url": "string"
  }
}
```

**响应：** Server-Sent Events (SSE) 格式

#### POST `/api/chat/stream/direct`
直接发送消息列表并返回AI的流式响应（不保存用户消息）。

**请求体：**
```json
{
  "session_id": "string",
  "messages": [
    {
      "role": "user|assistant|system",
      "content": "string"
    }
  ],
  "model_config": {
    "model_name": "string",
    "temperature": 0.7,
    "max_tokens": 1000,
    "api_key": "string",
    "base_url": "string"
  }
}
```

### 其他接口

- `GET /api/tools` - 获取可用工具列表
- `GET /api/servers` - 获取MCP服务器信息
- `POST /api/chat/abort` - 中止当前聊天请求
- `GET /health` - 健康检查

## 流式数据格式

与前端兼容的SSE事件类型：

### chunk
```json
{
  "type": "chunk",
  "data": {
    "content": "文本内容"
  }
}
```

### tool_call
```json
{
  "type": "tool_call",
  "data": {
    "tool_call_id": "string",
    "tool_name": "string",
    "arguments": {}
  }
}
```

### tool_result
```json
{
  "type": "tool_result",
  "data": {
    "tool_call_id": "string",
    "result": "工具执行结果"
  }
}
```

### tool_stream_chunk
```json
{
  "type": "tool_stream_chunk",
  "data": {
    "tool_call_id": "string",
    "content": "流式工具输出"
  }
}
```

### complete
```json
{
  "type": "complete",
  "data": {
    "message": "完整的消息对象"
  }
}
```

### error
```json
{
  "type": "error",
  "data": {
    "error": "错误信息"
  }
}
```

## 安装和运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务器
```bash
python -m app.main
```

服务器将在 `http://localhost:8000` 启动。

### 3. 测试API
```bash
python test_client.py
```

## 配置

### 环境变量
- `PORT` - 服务器端口（默认：8000）
- `OPENAI_API_KEY` - OpenAI API密钥
- `OPENAI_BASE_URL` - OpenAI API基础URL

### 模型配置
每个请求都可以包含 `model_config` 参数：

```json
{
  "model_name": "gpt-3.5-turbo",
  "temperature": 0.7,
  "max_tokens": 1000,
  "api_key": "your-api-key",
  "base_url": "https://api.openai.com/v1"
}
```

## 工具系统

### 注册工具
```python
from app.services.mcp_tool_execute import McpToolExecute, ToolInfo

executor = McpToolExecute()

# 定义工具信息
tool_info = ToolInfo(
    name="my_tool",
    description="工具描述",
    input_schema={
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        }
    },
    supports_streaming=True
)

# 注册工具处理器
async def my_tool_handler(arguments, on_chunk=None, on_complete=None, on_error=None):
    # 工具逻辑
    result = f"处理参数: {arguments.get('param')}"
    
    if on_chunk:
        on_chunk(result)
    if on_complete:
        on_complete(result)
    
    return result

executor.register_tool_handler("my_tool", my_tool_handler)
```

## 与前端集成

这个Python实现完全兼容现有的前端代码。前端的 `createChatStore.ts` 中的回调函数可以直接处理Python服务器返回的流式数据。

### 前端使用示例
```javascript
// 发送流式聊天请求
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    session_id: 'session_001',
    content: '你好',
    model_config: {
      model_name: 'gpt-3.5-turbo',
      temperature: 0.7,
      max_tokens: 1000,
      api_key: 'your-api-key',
      base_url: 'https://api.openai.com/v1'
    }
  })
});

// 处理SSE流
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      switch (data.type) {
        case 'chunk':
          // 处理文本块
          console.log('内容:', data.data.content);
          break;
        case 'tool_call':
          // 处理工具调用
          console.log('工具调用:', data.data);
          break;
        case 'complete':
          // 对话完成
          console.log('完成');
          break;
      }
    }
  }
}
```

## 注意事项

1. **API密钥安全**：不要在代码中硬编码API密钥，使用环境变量或配置文件。

2. **错误处理**：所有API调用都包含适当的错误处理和日志记录。

3. **性能优化**：消息管理器包含缓存机制，避免重复保存。

4. **流式处理**：支持真正的流式响应，提供实时用户体验。

5. **工具扩展**：可以轻松添加新的MCP工具和处理器。

## 开发和调试

### 日志配置
日志级别设置为 `INFO`，可以通过修改 `logging.basicConfig` 来调整。

### 调试模式
在开发环境中，可以启用FastAPI的自动重载：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 测试
使用提供的 `test_client.py` 来测试各个API接口的功能。