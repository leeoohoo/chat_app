#!/usr/bin/env python3
"""
启动脚本 - 用于开发和测试
"""

import os
import sys
import uvicorn
from pathlib import Path

def setup_environment():
    """设置环境变量"""
    # 添加项目根目录到Python路径
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 设置默认端口
    if 'PORT' not in os.environ:
        os.environ['PORT'] = '8000'
    
    # 检查数据库目录
    db_path = Path('chat_app.db')
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"数据库路径: {db_path.absolute()}")
    print(f"服务器端口: {os.environ.get('PORT', '8000')}")

def main():
    """主函数"""
    print("=" * 50)
    print("聊天应用服务器 - 开发模式")
    print("=" * 50)
    
    # 设置环境
    setup_environment()
    
    # 检查必要文件
    if not Path('/Users/lilei/project/learn/chat_app/server/chat_app_server/app/main.py').exists():
        print("✗ 未找到 app/main.py 文件")
        return False
    
    port = int(os.environ.get('PORT', 8000))
    
    print(f"\n启动服务器...")
    print(f"地址: http://localhost:{port}")
    print(f"API文档: http://localhost:{port}/docs")
    print(f"按 Ctrl+C 停止服务器\n")
    
    try:
        # 启动服务器
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
            reload=True,  # 开发模式启用热重载
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)