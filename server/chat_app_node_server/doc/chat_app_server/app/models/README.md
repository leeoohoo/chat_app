# 数据库兼容性功能

本项目现在支持 SQLite 和 MongoDB 两种数据库，可以通过配置文件进行切换，而不需要修改任何业务代码。

## 功能特性

- ✅ **双数据库支持**: 同时支持 SQLite 和 MongoDB
- ✅ **配置驱动**: 通过配置文件选择数据库类型
- ✅ **无缝切换**: 不影响现有方法调用
- ✅ **统一接口**: 所有数据库操作使用相同的API
- ✅ **向后兼容**: 保留原有的 DatabaseManager 类

## 配置方式

### 1. SQLite 配置（默认）

在 `config.json` 中设置：

```json
{
  "database": {
    "type": "sqlite",
    "sqlite": {
      "database_path": "data/chat_app.db"
    }
  }
}
```

### 2. MongoDB 配置

在 `config.json` 中设置：

```json
{
  "database": {
    "type": "mongodb",
    "mongodb": {
      "host": "localhost",
      "port": 27017,
      "database": "chat_app",
      "username": "your_username",
      "password": "your_password",
      "connection_options": {
        "maxPoolSize": 20,
        "minPoolSize": 5,
        "maxIdleTimeMS": 60000,
        "serverSelectionTimeoutMS": 10000,
        "socketTimeoutMS": 60000,
        "connectTimeoutMS": 20000,
        "retryWrites": true,
        "w": "majority"
      }
    }
  }
}
```

## 使用方法

### 1. 在模型类中使用

所有现有的模型类（如 `MCPConfigCreate`、`MessageCreate`、`SessionCreate` 等）已经自动使用新的数据库抽象层，无需修改任何代码：

```python
# 这些方法调用保持不变
config_id = MCPConfigCreate.create("test", "description", {"key": "value"})
configs = MCPConfigCreate.get_all()
config = MCPConfigCreate.get_by_id(config_id)
```

### 2. 直接使用数据库适配器

如果需要直接操作数据库：

```python
from app.models import get_database

# 获取当前配置的数据库适配器
db = get_database()

# 执行查询（自动适配不同数据库）
cursor = db.execute_query("SELECT * FROM sessions")
results = cursor.fetchall()
```

### 3. 动态切换数据库

```python
from app.models.database_factory import switch_to_mongodb, switch_to_sqlite

# 切换到 MongoDB
adapter = switch_to_mongodb(
    host="localhost",
    port=27017,
    database="chat_app",
    username="user",
    password="pass"
)

# 切换到 SQLite
adapter = switch_to_sqlite("data/new_database.db")
```

## 架构说明

### 核心组件

1. **DatabaseConfig**: 数据库配置模型
2. **AbstractDatabaseAdapter**: 抽象数据库接口
3. **SQLiteAdapter**: SQLite 数据库适配器
4. **MongoDBAdapter**: MongoDB 数据库适配器
5. **DatabaseFactory**: 数据库工厂类

### 文件结构

```
app/models/
├── __init__.py                 # 模块初始化和导出
├── database_config.py          # 数据库配置模型
├── database_interface.py       # 抽象数据库接口
├── sqlite_adapter.py          # SQLite 适配器
├── mongodb_adapter.py         # MongoDB 适配器
├── database_factory.py        # 数据库工厂
├── config.py                  # 配置相关模型
├── message.py                 # 消息模型
├── session.py                 # 会话模型
└── README.md                  # 本文档
```

## 安装依赖

### SQLite（默认包含）
无需额外安装，Python 内置支持。

### MongoDB
```bash
pip install pymongo motor
```

## 数据迁移

### 从 SQLite 迁移到 MongoDB

1. 导出 SQLite 数据：
```python
from app.models import get_database, switch_to_sqlite, switch_to_mongodb

# 使用 SQLite
sqlite_db = switch_to_sqlite("data/chat_app.db")
sessions = sqlite_db.fetch_all("SELECT * FROM sessions")

# 切换到 MongoDB
mongo_db = switch_to_mongodb()

# 迁移数据
for session in sessions:
    mongo_db.execute_query(
        "INSERT INTO sessions (id, title, description, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session['id'], session['title'], session['description'], session['metadata'], session['created_at'], session['updated_at'])
    )
```

### 从 MongoDB 迁移到 SQLite

类似的过程，只是方向相反。

## 性能考虑

### SQLite
- ✅ 轻量级，无需额外服务
- ✅ 适合单机部署
- ❌ 不支持并发写入
- ❌ 不适合大规模数据

### MongoDB
- ✅ 支持高并发
- ✅ 适合大规模数据
- ✅ 支持分布式部署
- ❌ 需要额外的服务器资源
- ❌ 配置相对复杂

## 故障排除

### 常见问题

1. **MongoDB 连接失败**
   - 检查 MongoDB 服务是否启动
   - 验证连接参数（主机、端口、用户名、密码）
   - 检查网络连接

2. **SQLite 文件权限问题**
   - 确保数据目录存在且可写
   - 检查文件权限设置

3. **配置文件格式错误**
   - 验证 JSON 格式是否正确
   - 检查必需字段是否存在

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展支持

如需支持其他数据库（如 PostgreSQL、MySQL），只需：

1. 创建新的适配器类继承 `AbstractDatabaseAdapter`
2. 在 `DatabaseConfig` 中添加新的配置类型
3. 在 `DatabaseFactory` 中添加创建逻辑

## 注意事项

1. **数据一致性**: 切换数据库时需要确保数据完整性
2. **事务支持**: MongoDB 的事务支持与 SQLite 有所不同
3. **查询语法**: 虽然提供了统一接口，但复杂查询可能需要特殊处理
4. **索引管理**: MongoDB 需要手动创建索引以优化性能

## 版本兼容性

- Python 3.7+
- SQLite 3.x
- MongoDB 4.0+
- pymongo 4.0+
- motor 3.0+ (异步支持)