# 聊天应用服务器

## 使用方法

1. 直接运行可执行文件：
   ```
   ./chat_app_server  # Linux/macOS
   chat_app_server.exe  # Windows
   ```

2. 服务器将在 http://localhost:8000 启动

3. API文档可在 http://localhost:8000/docs 查看

## 配置

服务器会自动创建 SQLite 数据库文件 `chat_app.db`

## 环境变量

- `OPENAI_API_KEY`: OpenAI API密钥
- `OPENAI_BASE_URL`: OpenAI API基础URL（可选）
- `PORT`: 服务器端口（默认8000）

## 支持的平台

- Windows (x64, x86)
- macOS (x64, arm64)
- Linux (x64, arm64)
