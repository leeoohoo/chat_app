# MCP管理器

MCP管理器是一个用于管理MCP（Model Context Protocol）服务器的工具，它可以自动检测系统环境，选择合适的MCP服务器可执行文件，并管理服务器配置。

## 功能特性

- 🔍 **自动系统检测**: 自动检测操作系统和架构，选择合适的MCP服务器文件
- ⚙️ **配置管理**: 管理MCP服务器配置，支持别名、配置检查和初始化
- 🔧 **多服务器支持**: 支持多种MCP服务器类型（expert-stream-server、file-reader-server）
- 📁 **统一配置目录**: 与现有的mcp_tool_execute.py使用相同的配置目录
- 🎯 **简单易用**: 提供简洁的API接口，易于集成到现有项目中

## 目录结构

```
app/mcp_manager/
├── __init__.py              # 包初始化文件
├── mcp_manager.py           # 主管理器类
├── system_detector.py       # 系统检测器
├── config_manager.py        # 配置管理器
├── test_mcp_manager.py      # 测试脚本
├── usage_example.py         # 使用示例
└── README.md               # 说明文档
```

## 快速开始

### 1. 基本使用

```python
from app.mcp_manager import McpManager

# 初始化MCP管理器
mcp_manager = McpManager()

# 获取系统信息
system_info = mcp_manager.get_system_info()
print(f"系统: {system_info['os']} ({system_info['arch']})")

# 检查可用服务器
available_servers = mcp_manager.get_available_servers()
print(f"可用服务器: {list(available_servers.keys())}")

# 为所有可用服务器设置配置
setup_results = mcp_manager.setup_all_available_servers()
print(f"配置设置结果: {setup_results}")
```

### 2. 获取服务器配置

```python
# 获取expert-stream-server的推荐配置
expert_config = mcp_manager.get_recommended_config_for_type("expert-stream-server")
if expert_config:
    print(f"别名: {expert_config['alias']}")
    print(f"可执行文件: {expert_config['executable_path']}")
    print(f"配置目录: {expert_config['config_dir']}")

# 获取启动命令信息
cmd_info = mcp_manager.get_server_command_info(expert_config['alias'])
print(f"启动命令: {cmd_info['command']}")
```

### 3. 与SimpleClient集成

```python
# 获取配置信息用于SimpleClient初始化
config = mcp_manager.get_recommended_config_for_type("expert-stream-server")

# 使用配置信息初始化SimpleClient
from your_simple_client_module import SimpleClient

client = SimpleClient(
    server_script=config['executable_path'],
    alias=config['alias'],
    config_dir=config['config_dir']
)
```

### 4. 自定义别名

```python
# 使用自定义别名初始化服务器配置
success, alias = mcp_manager.initialize_server_config(
    server_type="expert-stream-server",
    alias="my_custom_server"
)

if success:
    print(f"自定义配置创建成功: {alias}")
```

## API参考

### McpManager

主要的MCP管理器类，提供统一的管理接口。

#### 初始化

```python
McpManager(mcp_services_dir=None, config_dir=None)
```

- `mcp_services_dir`: MCP服务器文件目录（可选，默认自动检测）
- `config_dir`: 配置文件目录（可选，默认使用mcp_config）

#### 主要方法

- `get_system_info()`: 获取系统信息
- `get_available_servers()`: 获取可用服务器列表
- `initialize_server_config(server_type, alias=None, force_reinit=False)`: 初始化服务器配置
- `get_server_config(alias)`: 获取指定别名的配置
- `get_recommended_config_for_type(server_type)`: 获取推荐配置
- `get_server_command_info(alias)`: 获取启动命令信息
- `list_all_server_configs()`: 列出所有配置
- `setup_all_available_servers()`: 设置所有可用服务器的配置

### SystemDetector

系统检测器，负责检测系统环境并选择合适的可执行文件。

#### 主要方法

- `get_system_info()`: 获取系统信息
- `get_server_executable_path(server_type)`: 获取服务器可执行文件路径
- `get_available_servers()`: 获取所有可用服务器
- `validate_server_path(server_path)`: 验证服务器路径

### ConfigManager

配置管理器，负责管理MCP服务器配置文件。

#### 主要方法

- `alias_exists(alias)`: 检查别名是否存在
- `get_config(alias)`: 获取配置
- `save_config(alias, config)`: 保存配置
- `initialize_config(alias, server_type, executable_path, additional_config=None)`: 初始化配置
- `generate_unique_alias(server_type, prefix="mcp")`: 生成唯一别名
- `list_all_configs()`: 列出所有配置

## 支持的服务器类型

- `expert-stream-server`: 专家流服务器
- `file-reader-server`: 文件读取服务器

## 支持的平台

- macOS (ARM64, x86_64)
- Windows (x86_64)
- Linux (x86_64, ARM64) - 如果有相应的可执行文件

## 配置文件格式

配置文件以JSON格式存储在`mcp_config`目录中：

```json
{
  "alias": "mcp_expert_stream_server",
  "server_type": "expert-stream-server",
  "executable_path": "/path/to/expert-stream-server",
  "config_dir": "/path/to/mcp_config",
  "platform": "macos-arm64",
  "os": "macos",
  "arch": "arm64",
  "mcp_services_dir": "/path/to/mcp_services",
  "created_at": "/current/working/directory",
  "status": "initialized"
}
```

## 测试

运行测试脚本来验证功能：

```bash
cd /Users/lilei/project/learn/chat_app/server/chat_app_server
python app/mcp_manager/test_mcp_manager.py
```

运行使用示例：

```bash
python app/mcp_manager/usage_example.py
```

## 与现有代码的兼容性

MCP管理器设计时考虑了与现有`mcp_tool_execute.py`的兼容性：

- 使用相同的`config_dir`路径
- 配置格式兼容SimpleClient的要求
- 可以无缝集成到现有项目中

## 日志

MCP管理器使用Python标准日志模块，可以通过配置日志级别来控制输出详细程度：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 注意事项

1. 确保MCP服务器可执行文件具有执行权限
2. 配置目录会自动创建，无需手动创建
3. 别名必须唯一，系统会自动处理冲突
4. 建议定期清理无效配置

## 故障排除

### 常见问题

1. **找不到可执行文件**: 检查`mcp_services`目录结构是否正确
2. **权限错误**: 确保可执行文件有执行权限
3. **配置冲突**: 使用不同的别名或删除冲突的配置

### 调试

启用详细日志来调试问题：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 贡献

欢迎提交问题和改进建议！