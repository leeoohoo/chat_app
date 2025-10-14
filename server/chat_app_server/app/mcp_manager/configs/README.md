# MCP服务器分离式配置初始化系统

这个系统为不同类型的MCP服务器提供了独立的配置初始化和管理功能。每个服务器类型都有自己专门的配置文件和初始化逻辑。

## 🏗️ 架构概览

```
mcp_manager/configs/
├── __init__.py                    # 包初始化，导出主要类
├── config_factory.py             # 配置工厂，统一管理入口
├── expert_stream_config.py       # Expert Stream Server专用配置
├── file_reader_config.py         # File Reader Server专用配置
└── README.md                      # 本文档
```

## 🚀 快速开始

### 1. 基本使用

```python
from app.mcp_manager.configs import ConfigInitializerFactory

# 初始化配置工厂
factory = ConfigInitializerFactory("/path/to/config/directory")

# 查看支持的服务器类型
supported_servers = factory.get_supported_servers()
print(f"支持的服务器: {list(supported_servers.keys())}")

# 初始化Expert Stream Server配置
success = factory.initialize_config(
    server_type="expert-stream-server",
    alias="my_expert_server",
    executable_path="/path/to/expert-stream-server",
    config_template="development",
    custom_config={
        "api_key": "your_api_key_here",
        "model_name": "gpt-4"
    }
)

# 初始化File Reader Server配置
success = factory.initialize_config(
    server_type="file-reader-server", 
    alias="my_file_reader",
    executable_path="/path/to/file-reader-server",
    config_template="development",
    project_root="/path/to/your/project"
)
```

### 2. 通过McpManager使用

```python
from app.mcp_manager.mcp_manager import McpManager

# 初始化管理器
manager = McpManager(config_dir="/path/to/config/directory")

# 查看可用的配置模板
expert_templates = manager.get_available_config_templates("expert-stream-server")
file_reader_templates = manager.get_available_config_templates("file-reader-server")

# 使用模板初始化配置
manager.initialize_server_with_template(
    server_type="expert-stream-server",
    alias="expert_dev",
    executable_path="/path/to/expert-stream-server",
    config_template="development",
    api_key="your_api_key",
    model_name="gpt-4"
)

# 更新配置
manager.update_server_config("expert_dev", {
    "log_level": "DEBUG",
    "system_prompt": "You are a helpful coding assistant."
})

# 获取配置摘要
summary = manager.get_config_summary_by_factory("expert_dev")
print(f"配置摘要: {summary}")
```

## 📋 Expert Stream Server配置

### 支持的配置模板

1. **default** - 基础配置
2. **development** - 开发环境配置
3. **production** - 生产环境配置  
4. **code_review** - 代码审查专用配置

### 配置参数

```python
{
    "api_key": "OpenAI API密钥",
    "model_name": "使用的模型名称 (如: gpt-4, gpt-3.5-turbo)",
    "system_prompt": "系统提示词",
    "max_tokens": "最大token数",
    "temperature": "温度参数",
    "log_level": "日志级别",
    "enable_history": "是否启用历史记录",
    "history_limit": "历史记录限制",
    "enable_summary": "是否启用摘要功能",
    "summary_threshold": "摘要触发阈值"
}
```

### 使用示例

```python
from app.mcp_manager.configs.expert_stream_config import ExpertStreamConfigInitializer

initializer = ExpertStreamConfigInitializer("/config/directory")

# 使用开发模板
initializer.initialize_config(
    alias="expert_dev",
    executable_path="/path/to/expert-stream-server",
    config_template="development",
    custom_config={
        "api_key": "sk-your-api-key",
        "model_name": "gpt-4",
        "system_prompt": "You are a helpful coding assistant.",
        "log_level": "DEBUG"
    }
)

# 验证配置
if initializer.validate_config("expert_dev"):
    print("✅ 配置验证通过")

# 更新配置
initializer.update_config("expert_dev", {
    "temperature": 0.7,
    "max_tokens": 4000
})
```

## 📁 File Reader Server配置

### 支持的配置模板

1. **default** - 基础配置
2. **development** - 开发环境配置
3. **production** - 生产环境配置
4. **research** - 研究项目配置

### 配置参数

```python
{
    "project_root": "项目根目录路径",
    "max_file_size": "最大文件大小(MB)",
    "enable_hidden_files": "是否启用隐藏文件",
    "file_extensions": "支持的文件扩展名列表",
    "exclude_patterns": "排除的文件模式",
    "log_level": "日志级别",
    "cache_enabled": "是否启用缓存",
    "cache_size": "缓存大小"
}
```

### 使用示例

```python
from app.mcp_manager.configs.file_reader_config import FileReaderConfigInitializer

initializer = FileReaderConfigInitializer("/config/directory")

# 使用开发模板
initializer.initialize_config(
    alias="file_reader_dev",
    executable_path="/path/to/file-reader-server",
    config_template="development",
    project_root="/path/to/your/project",
    custom_config={
        "max_file_size": 20,
        "enable_hidden_files": True,
        "log_level": "DEBUG"
    }
)

# 设置项目根目录
initializer.set_project_root("file_reader_dev", "/new/project/path")

# 获取当前项目根目录
current_root = initializer.get_project_root("file_reader_dev")
print(f"当前项目根目录: {current_root}")
```

## 🔧 配置工厂高级功能

### 批量操作

```python
from app.mcp_manager.configs import ConfigInitializerFactory

factory = ConfigInitializerFactory("/config/directory")

# 列出所有配置
all_configs = factory.list_configs()
for server_type, configs in all_configs.items():
    print(f"{server_type}: {len(configs)} 个配置")

# 复制配置
factory.copy_config("source_alias", "target_alias")

# 删除配置
factory.delete_config("alias_to_delete")

# 清理无效配置
cleanup_result = factory.cleanup_configs()
print(f"清理结果: {cleanup_result}")
```

### 配置验证

```python
# 验证单个配置
is_valid = factory.validate_config("my_alias")

# 获取配置摘要
summary = factory.get_config_summary("my_alias")
if summary:
    print(f"服务器类型: {summary['server_type']}")
    print(f"版本: {summary['version']}")
    print(f"创建时间: {summary['created_at']}")
```

### 工厂状态监控

```python
# 获取工厂状态
status = factory.get_factory_status()
print(f"支持的服务器类型: {status['supported_servers']}")
print(f"总配置数: {status['total_configs']}")
print(f"按类型分组: {status['configs_by_type']}")
```

## 🧪 测试

运行测试脚本来验证所有功能：

```bash
cd /path/to/chat_app_server
python app/mcp_manager/test_separate_configs.py
```

测试包括：
- ✅ 配置工厂基本功能
- ✅ Expert Stream Server配置初始化
- ✅ File Reader Server配置初始化  
- ✅ McpManager集成测试

## 🔍 故障排除

### 常见问题

1. **配置初始化失败**
   - 检查可执行文件路径是否正确
   - 确认配置目录有写入权限
   - 验证配置模板名称是否正确

2. **配置验证失败**
   - 检查必需的配置参数是否存在
   - 验证配置文件格式是否正确
   - 确认配置值的类型和范围

3. **项目根目录设置失败**
   - 确认目录路径存在且可访问
   - 检查目录权限
   - 验证路径格式是否正确

### 调试技巧

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 查看配置文件内容
import json
with open("/config/directory/alias.json", "r") as f:
    config = json.load(f)
    print(json.dumps(config, indent=2, ensure_ascii=False))
```

## 🚀 扩展新的服务器类型

要添加新的MCP服务器类型支持：

1. 在`configs/`目录下创建新的配置文件（如`new_server_config.py`）
2. 实现配置初始化器类，继承基础接口
3. 在`config_factory.py`中注册新的服务器类型
4. 在`__init__.py`中导出新的初始化器类
5. 添加相应的测试用例

示例结构：
```python
class NewServerConfigInitializer:
    def __init__(self, config_dir: str):
        # 初始化逻辑
        
    def get_config_templates(self) -> Dict[str, Dict]:
        # 返回配置模板
        
    def initialize_config(self, alias: str, executable_path: str, 
                         config_template: str = "default", **kwargs) -> bool:
        # 配置初始化逻辑
        
    # 其他必需方法...
```

## 📝 最佳实践

1. **配置命名**: 使用描述性的别名，如`expert_dev_main`、`file_reader_prod_api`
2. **模板选择**: 根据使用场景选择合适的配置模板
3. **安全性**: 不要在配置文件中硬编码敏感信息，使用环境变量
4. **备份**: 定期备份重要的配置文件
5. **版本控制**: 配置文件包含版本信息，便于管理和升级

---

这个分离式配置系统提供了灵活、可扩展的MCP服务器配置管理方案，支持多种服务器类型和配置模板，让您可以轻松管理复杂的MCP服务器环境。