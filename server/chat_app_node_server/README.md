# Chat App Node Server

Node.js 聊天应用服务器 - 完全复刻自 Python FastAPI 版本

## 🎉 项目简介

这是一个使用 Node.js 和 Express 构建的聊天应用服务器，**完全复刻**了 Python FastAPI 版本的架构和功能，包括核心的 MCP 工具系统和流式聊天功能。

### ✨ 核心特性

- ✅ **双数据库支持**: SQLite（默认）和 MongoDB 可无缝切换
- ✅ **模块化架构**: 清晰的分层设计（API → 服务 → 模型 → 数据库）
- ✅ **MCP 工具系统**: 使用 @modelcontextprotocol/sdk 支持 HTTP 和 STDIO MCP 服务器
- ✅ **流式聊天**: Server-Sent Events (SSE) 实时流式响应
- ✅ **递归工具调用**: AI 可以多次调用工具，直到获得完整答案
- ✅ **消息管理**: 完整的会话和消息持久化，支持缓存优化
- ✅ **AI 集成**: OpenAI API 集成，支持工具调用和推理内容
- ✅ **日志系统**: Winston 日志，支持文件轮转

## 🚀 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenAI API 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 服务器配置
PORT=3001
NODE_ENV=development
```

### 3. 启动服务器

```bash
npm start
```

或使用开发模式（自动重启）：

```bash
npm run dev
```

服务器将在 `http://localhost:3001` 启动。

## 📡 API 端点

### 健康检查

```
GET /health
```

### 会话管理

```
GET    /api/sessions              获取会话列表
POST   /api/sessions              创建新会话
GET    /api/sessions/:id          获取特定会话
PUT    /api/sessions/:id          更新会话
DELETE /api/sessions/:id          删除会话
```

### 消息管理

```
GET    /api/messages?session_id=xxx  获取会话的消息列表
POST   /api/messages                   创建新消息
GET    /api/messages/:id               获取特定消息
DELETE /api/messages/:id               删除消息
GET    /api/sessions/:session_id/messages  获取会话消息（Python路径格式）
POST   /api/sessions/:session_id/messages  创建新消息（Python路径格式）
```

### 智能体管理

```
GET    /api/agents                获取智能体列表
POST   /api/agents                创建新智能体
GET    /api/agents/:agent_id      获取特定智能体
PUT    /api/agents/:agent_id      更新智能体
DELETE /api/agents/:agent_id      删除智能体
POST   /api/agents/chat/stream    基于智能体ID的流式聊天
```

### 应用管理

```
GET    /api/applications                    获取应用列表
POST   /api/applications                    创建新应用
GET    /api/applications/:application_id    获取特定应用
PUT    /api/applications/:application_id    更新应用
DELETE /api/applications/:application_id    删除应用
```

### 配置管理

#### MCP配置

```
GET    /api/mcp-configs                              获取MCP配置列表
POST   /api/mcp-configs                              创建MCP配置
PUT    /api/mcp-configs/:config_id                   更新MCP配置
DELETE /api/mcp-configs/:config_id                   删除MCP配置
GET    /api/mcp-configs/:config_id/resource/config   读取MCP配置资源
POST   /api/mcp-configs/resource/config              通过命令读取MCP配置资源
```

#### MCP配置档案

```
GET    /api/mcp-configs/:config_id/profiles                        获取配置档案列表
POST   /api/mcp-configs/:config_id/profiles                        创建配置档案
PUT    /api/mcp-configs/:config_id/profiles/:profile_id            更新配置档案
DELETE /api/mcp-configs/:config_id/profiles/:profile_id            删除配置档案
POST   /api/mcp-configs/:config_id/profiles/:profile_id/activate   激活配置档案
```

#### AI模型配置

```
GET    /api/ai-model-configs                获取AI模型配置列表
POST   /api/ai-model-configs                创建AI模型配置
PUT    /api/ai-model-configs/:config_id     更新AI模型配置
DELETE /api/ai-model-configs/:config_id     删除AI模型配置
```

#### 系统上下文

```
GET    /api/system-contexts                        获取系统上下文列表
GET    /api/system-context/active                  获取活跃系统上下文
POST   /api/system-contexts                        创建系统上下文
PUT    /api/system-contexts/:context_id            更新系统上下文
DELETE /api/system-contexts/:context_id            删除系统上下文
POST   /api/system-contexts/:context_id/activate   激活系统上下文
```

### Chat API v2（核心功能）

```
POST   /api/agent_v2/chat/stream                   流式聊天（支持 MCP 工具调用）
POST   /api/agent_v2/chat/stream/simple            简化流式聊天（使用 Agent 封装）
GET    /api/agent_v2/tools                         获取可用工具列表
GET    /api/agent_v2/status                        获取服务器状态
POST   /api/agent_v2/session/:session_id/reset     重置指定会话
GET    /api/agent_v2/session/:session_id/config    获取会话配置
POST   /api/agent_v2/session/:session_id/config    更新会话配置
POST   /api/v2/chat/stream                         基于Agent的流式聊天（v2版本）
```

## 🛠️ 流式聊天使用示例

### 请求格式

```javascript
POST /api/agent_v2/chat/stream

{
  "session_id": "会话ID",
  "content": "用户消息",
  "ai_model_config": {
    "model_name": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4000,
    "use_tools": true,
    "api_key": "可选，覆盖环境变量",
    "base_url": "可选，覆盖环境变量"
  },
  "user_id": "可选，用于加载用户的 MCP 配置"
}
```

### 流式响应格式（SSE）

```
data: {"type": "start", "session_id": "...", "timestamp": "..."}

data: {"type": "chunk", "content": "文本内容", "timestamp": "..."}

data: {"type": "thinking", "content": "思考过程", "timestamp": "..."}

data: {"type": "tools_start", "data": {"tool_calls": [...]}, "timestamp": "..."}

data: {"type": "tools_stream", "data": {...}, "timestamp": "..."}

data: {"type": "tools_end", "data": {"tool_results": [...]}, "timestamp": "..."}

data: {"type": "complete", "result": {...}, "timestamp": "..."}

data: [DONE]
```

### 事件类型说明

- `start`: 流开始
- `chunk`: AI 回复的文本块（流式）
- `thinking`: 推理内容（用于 o1 等模型）
- `tools_start`: 工具调用开始
- `tools_stream`: 工具执行中（流式输出）
- `tools_end`: 工具执行完成
- `complete`: 对话完成
- `error`: 错误信息
- `[DONE]`: 流结束标记

## 🔧 项目结构

```
chat_app_node_server/
├── src/
│   ├── main.js                          # 应用入口
│   ├── models/                          # 数据模型层
│   │   ├── database-config.js               # 数据库配置
│   │   ├── database-interface.js            # 数据库接口
│   │   ├── database-factory.js              # 数据库工厂
│   │   ├── sqlite-adapter.js                # SQLite 适配器（WAL 优化）
│   │   ├── mongodb-adapter.js               # MongoDB 适配器
│   │   ├── session.js                       # 会话模型
│   │   ├── message.js                       # 消息模型
│   │   └── mcp-config.js                    # MCP 配置模型
│   ├── api/                             # API 路由层
│   │   ├── sessions.js                      # 会话路由
│   │   ├── messages.js                      # 消息路由
│   │   ├── agents.js                        # 智能体管理路由
│   │   ├── applications.js                  # 应用管理路由
│   │   ├── configs.js                       # 配置管理路由
│   │   ├── chat-v2.js                       # Chat API v2（核心）
│   │   └── chat-agent-v2.js                 # Chat API v2（Agent版本）
│   ├── services/v2/                     # 服务层 v2
│   │   ├── ai-server.js                     # AI 服务主类
│   │   ├── ai-client.js                     # AI 客户端（递归协调器）
│   │   ├── ai-request-handler.js            # AI 请求处理器
│   │   ├── message-manager.js               # 消息管理器
│   │   ├── mcp-tool-execute.js              # MCP 工具执行器
│   │   ├── tool-result-processor.js         # 工具结果处理器
│   │   └── agent.js                         # Agent 封装类
│   └── utils/                           # 工具函数
│       ├── config.js                        # 配置管理
│       └── logger.js                        # 日志系统
├── config/                              # 配置文件
│   └── database.json                        # 数据库配置
├── data/                                # 数据文件
├── logs/                                # 日志文件
├── test/                                # 测试脚本
│   ├── test_api.js                          # API 测试
│   └── test_stream_chat.js                  # 流式聊天测试
└── package.json
```

## 📦 核心依赖

- **@modelcontextprotocol/sdk**: MCP 工具协议（最新版）
- **express**: Web 框架
- **openai**: OpenAI API 客户端
- **better-sqlite3**: SQLite 数据库（高性能）
- **mongodb**: MongoDB 数据库
- **winston**: 日志系统
- **uuid**: UUID 生成
- **cors**: 跨域支持
- **dotenv**: 环境变量管理

## 🔌 MCP 工具系统

### 配置 MCP 服务器

MCP 配置存储在数据库中，支持两种类型：

#### 1. HTTP MCP 服务器

```json
{
  "name": "my_http_tool",
  "command": "http://localhost:8000/mcp",
  "type": "http",
  "enabled": true,
  "user_id": "user_123"
}
```

#### 2. STDIO MCP 服务器

```json
{
  "name": "my_stdio_tool",
  "command": "python",
  "type": "stdio",
  "args": ["-m", "my_mcp_server"],
  "env": {"API_KEY": "xxx"},
  "cwd": "/path/to/project",
  "enabled": true,
  "user_id": "user_123"
}
```

### 工具调用流程

1. **加载配置**: 从数据库加载启用的 MCP 配置
2. **初始化工具**: 使用 MCP SDK Client 连接服务器并列出工具
3. **工具注册**: 将工具转换为 OpenAI 格式并注册
4. **AI 调用**: AI 决定调用哪些工具
5. **执行工具**: 通过 MCP SDK 执行工具调用
6. **递归处理**: 将工具结果返回给 AI，继续对话
7. **完成**: AI 不再调用工具，返回最终答案

## 🤖 Agent 封装

Agent 模块提供了简化的高级接口，封装了所有复杂的配置和调用逻辑：

### 代码中使用 Agent

```javascript
import { createAgent, buildSseStream } from './services/v2/agent.js';

// 创建 Agent
const agent = createAgent({
  api_key: 'your-api-key',
  model_name: 'gpt-4',
  system_prompt: '你是一个有帮助的助手',
  temperature: 0.7,
  user_id: 'user_123'  // 自动加载用户的 MCP 配置
});

// 初始化（加载工具）
await agent.init();

// 简单聊天
const result = await agent.chat('你好', {
  session_id: 'session_123',
  use_tools: true,
  on_chunk: (chunk) => console.log(chunk)
});
```

### 使用简化端点

```javascript
POST /api/agent_v2/chat/stream/simple

{
  "session_id": "会话ID",
  "content": "用户消息",
  "ai_model_config": {
    "model_name": "gpt-4",
    "temperature": 0.7,
    "use_tools": true
  },
  "user_id": "可选",
  "agent_id": "可选，使用预配置的智能体"
}
```

## 🧪 测试

### 基础 API 测试

```bash
# 启动服务器
npm start

# 在另一个终端运行测试
node test/test_api.js
```

### 流式聊天测试

```bash
# 确保设置了 OPENAI_API_KEY
export OPENAI_API_KEY=your-api-key

# 运行流式聊天测试
node test/test_stream_chat.js
```

## 📊 数据库配置

### 默认配置（SQLite）

`config/database.json`:

```json
{
  "type": "sqlite",
  "sqlite": {
    "db_path": "data/chat_app.db",
    "timeout": 30000,
    "busyTimeout": 30000
  },
  "auto_migrate": true,
  "debug": false
}
```

### 切换到 MongoDB

修改 `config/database.json`:

```json
{
  "type": "mongodb",
  "mongodb": {
    "host": "localhost",
    "port": 27017,
    "database": "chat_app",
    "username": "your_username",
    "password": "your_password"
  }
}
```

## 🎯 核心实现亮点

### 1. 完整的 MCP 工具系统

使用官方 `@modelcontextprotocol/sdk`，完整实现：
- HTTP 和 STDIO 两种传输方式
- 工具发现和注册
- 工具执行和结果处理
- 错误处理和重试

### 2. 递归工具调用

`AiClient` 实现了完整的递归逻辑：
- AI 可以多次调用工具
- 自动传递工具结果给 AI
- 防止无限循环（最大 25 次迭代）
- 支持复杂的多步骤任务

### 3. 流式响应处理

使用 SSE（Server-Sent Events）：
- 实时传输 AI 回复
- 支持工具执行进度
- 心跳保活机制
- 错误处理和恢复

### 4. 数据库抽象层

完整的抽象层设计：
- 统一的数据库接口
- 工厂模式创建适配器
- 支持动态切换数据库
- SQLite WAL 优化
- MongoDB 连接池管理

### 5. Agent 封装

高级 Agent 接口：
- AgentConfig 和 Agent 类
- 自动根据 user_id 加载 MCP 配置
- `run()` 和 `chat()` 简化方法
- `buildSseStream()` 异步生成器
- 支持按 agent_id 加载预配置

## 📝 开发日志

### 已完成功能

- ✅ 项目初始化和依赖安装
- ✅ 数据库抽象层（支持 SQLite 和 MongoDB）
- ✅ 数据模型层（Session、Message、McpConfig）
- ✅ API 路由层（Sessions、Messages、Chat v2）
- ✅ 服务层 v2（完整的 AI 和工具系统）
- ✅ MCP 工具执行器（使用官方 SDK）
- ✅ 流式聊天功能
- ✅ 消息管理和缓存
- ✅ 日志系统
- ✅ 测试脚本

### 与 Python 版本对比

| 功能 | Python 版本 | Node.js 版本 | 状态 |
|-----|-----------|-------------|------|
| 数据库抽象 | ✅ | ✅ | 完全复刻 |
| SQLite 支持 | ✅ | ✅ | 完全复刻 |
| MongoDB 支持 | ✅ | ✅ | 完全复刻 |
| MCP 工具系统 | ✅ (fastmcp) | ✅ (@modelcontextprotocol/sdk) | 完全复刻 |
| 流式聊天 | ✅ | ✅ | 完全复刻 |
| 递归工具调用 | ✅ | ✅ | 完全复刻 |
| 消息管理 | ✅ | ✅ | 完全复刻 |
| 日志系统 | ✅ | ✅ | 完全复刻 |

## 🤝 贡献

这是一个从 Python FastAPI 版本完全复刻的项目，旨在提供 Node.js 版本的实现。

## 📄 许可证

MIT

---

**注意**: 本项目已完全复刻 Python 版本的核心功能，包括最重要的 MCP 工具系统和流式聊天功能。所有关键组件都已实现并可以正常工作。
