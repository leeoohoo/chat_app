# Python聊天应用服务器主模块
# 使用 FastAPI 实现所有 REST API 接口

import time
import asyncio
import logging
import os
import signal
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

def _startup_timer_init():
    """初始化启动计时器并返回日志函数"""
    _startup_time = time.time()
    def log_step(step_name: str):
        now = time.time()
        elapsed = now - _startup_time
        print(f"[{elapsed:.2f}s] {step_name}")
    return log_step

log_step = _startup_timer_init()
log_step("程序开始启动")
log_step("开始导入路由模块")

from app.api import sessions
log_step("导入路由完成: sessions")
from app.api import messages
log_step("导入路由完成: messages")
from app.api import configs
log_step("导入路由完成: configs")
from app.api import mcp_initializers
log_step("导入路由完成: mcp_initializers")
from app.api import chat_api_v2
log_step("导入路由完成: chat_api_v2")
from app.api import agents
log_step("导入路由完成: agents")

log_step("导入数据库模块")
from app.models import db_manager
from app.models.database_factory import get_database
log_step("所有模块导入完成")
log_step("启动后台模块预加载")
from app.utils.module_preloader import start_preload
start_preload()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    logger.info("正在初始化数据库...")
    db = get_database()
    await db.init_database()
    logger.info("数据库初始化完成")
    
    # 跳过启动时的 MCP 配置初始化（改为按需在相关接口调用时进行）
    logger.info("跳过启动时的 MCP 配置初始化，改为按需初始化")
    
    yield
    
    # 关闭时清理资源
    logger.info("正在关闭数据库连接...")
    await db.close()
    logger.info("数据库连接已关闭")

# 创建 FastAPI 应用
app = FastAPI(title="聊天应用服务器", version="1.0.0", lifespan=lifespan)
log_step("FastAPI 应用创建完成")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简单性能监控中间件：记录每次请求耗时
@app.middleware("http")
async def timing_middleware(request, call_next):
    start = asyncio.get_event_loop().time()
    response = await call_next(request)
    duration_ms = (asyncio.get_event_loop().time() - start) * 1000
    try:
        logger.info(f"[perf] {request.method} {request.url.path} -> {duration_ms:.1f} ms")
    except Exception:
        pass
    return response

# 注册路由
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(messages.router, prefix="/api", tags=["messages"])
app.include_router(configs.router, prefix="/api", tags=["configs"])
app.include_router(mcp_initializers.router, prefix="/api/mcp-initializers", tags=["mcp-initializers"])
app.include_router(chat_api_v2.router, prefix="/api", tags=["chat-v2"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
log_step("路由注册完成")


# 数据库依赖
async def get_db():
    return get_database()


# 服务前端静态文件（如果存在）
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # 检查是否是API路由
    if full_path.startswith('api/'):
        raise HTTPException(status_code=404, detail='API endpoint not found')
    
    # 尝试服务静态文件
    dist_path = Path(__file__).parent / "../../dist"
    if dist_path.exists():
        index_file = dist_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    
    raise HTTPException(status_code=404, detail='Page not found')


# 移除自定义信号处理器，让 uvicorn 自己处理
# uvicorn 已经内置了正确的信号处理逻辑

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    # 在打包环境中避免字符串导入，直接传递 app 对象
    # 强制启用 uvloop 与 httptools 以提高性能
    log_step("开始执行主程序")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,
        loop="uvloop",
        http="httptools",
        # 可通过环境变量 WORKERS 配置多进程 worker（默认1）
        workers=int(os.environ.get("WORKERS", "1"))
    )
    log_step("程序启动完成")