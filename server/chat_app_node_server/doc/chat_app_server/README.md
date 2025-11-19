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

## 跨平台打包

本项目使用 Nuitka 生成目录型产物，支持 macOS 与 Windows 平台按架构打包。

### macOS（在 macOS 机器上执行）
- 仅构建 arm64（Apple Silicon）：`make build_macos_arm64`
- 仅构建 x64（Intel 芯片）：`make build_macos_x64`
- 同时构建 arm64 + x64：`make build_macos_both`

提示：在 Apple Silicon 上构建 x64 需要安装 Rosetta 并确保 Python 为 universal2 或包含 x86_64 切片。

### Windows（在 Windows 机器上执行）
- 命令提示符运行：`scripts\build_windows.bat`

构建成功后，产物位于：`dist/chat_app_server_nuitka_<system>_<arch>`，例如：
- macOS arm64: `dist/chat_app_server_nuitka_darwin_arm64`
- macOS x64: `dist/chat_app_server_nuitka_darwin_x64`
- Windows x64: `dist/chat_app_server_nuitka_windows_x64`

## 使用 PyInstaller 打包

本仓库已提供 PyInstaller 的 `build.spec`，并新增打包脚本：

- 打包命令：
  - `python scripts/build_pyinstaller.py`

- 输出位置：
  - `dist/chat_app_server/`

- 运行示例：
  - macOS/Linux：`dist/chat_app_server/chat_app_server`
  - Windows：`dist/chat_app_server/chat_app_server.exe`

说明：
- 打包脚本会自动安装 PyInstaller（如未安装）。
- 会将 `config.json` 和 `app/mcp_config/` 拷贝到产物目录，确保运行时配置可用。
