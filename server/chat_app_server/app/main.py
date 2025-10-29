# Python聊天应用服务器主模块
# 使用 FastAPI 实现所有 REST API 接口

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

from app.api import sessions, messages, configs, mcp_initializers, chat_api_v2
from app.models import db
from app.mcp_manager.configs import startup_initialize_mcp

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
    await db.init_database()
    logger.info("数据库初始化完成")
    
    # 启动时初始化MCP配置
    logger.info("正在初始化MCP配置...")
    try:
        mcp_results = await startup_initialize_mcp()
        success_count = sum(1 for success in mcp_results.values() if success)
        total_count = len(mcp_results)
        logger.info(f"MCP配置初始化完成: {success_count}/{total_count} 成功")
        
        # 记录详细结果
        for server_type, success in mcp_results.items():
            status = "✅ 成功" if success else "❌ 失败"
            logger.info(f"  - {server_type}: {status}")
            
    except Exception as e:
        logger.error(f"MCP配置初始化失败: {e}")
    
    yield
    
    # 关闭时清理资源
    logger.info("正在关闭数据库连接...")
    await db.close()
    logger.info("数据库连接已关闭")

# 创建 FastAPI 应用
app = FastAPI(title="聊天应用服务器", version="1.0.0", lifespan=lifespan)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(messages.router, prefix="/api", tags=["messages"])
app.include_router(configs.router, prefix="/api", tags=["configs"])
app.include_router(mcp_initializers.router, prefix="/api/mcp-initializers", tags=["mcp-initializers"])
app.include_router(chat_api_v2.router, prefix="/api", tags=["chat-v2"])


# 数据库依赖
async def get_db():
    return db


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


# 优雅关闭处理
def signal_handler(signum, frame):
    logger.info(f'🔄 收到信号 {signum}，正在关闭服务器...')
    asyncio.create_task(shutdown_event())


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )