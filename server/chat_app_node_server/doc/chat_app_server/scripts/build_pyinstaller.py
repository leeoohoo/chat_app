#!/usr/bin/env python3
"""
PyInstaller 打包脚本

功能：
- 自动安装 PyInstaller（如未安装）
- 清理旧的 build/dist 目录
- 使用现有的 build.spec 进行打包
- 将运行所需的资源拷贝到产物目录（config.json、mcp_config）

生成产物：dist/chat_app_server/

使用：
    python scripts/build_pyinstaller.py

可选环境变量：
- PIP_INDEX_URL：自定义 Python 包源（如需）
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
SPEC_FILE = PROJECT_ROOT / "build.spec"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
APP_DIST_DIR = DIST_DIR / "chat_app_server"


def run(cmd: list[str], cwd: Path | None = None):
    print(f"[run] {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except Exception:
        print("PyInstaller 未安装，正在安装...")
        pip_cmd = [sys.executable, "-m", "pip", "install", "pyinstaller"]
        # 支持自定义源
        index_url = os.environ.get("PIP_INDEX_URL")
        if index_url:
            pip_cmd += ["-i", index_url]
        run(pip_cmd)


def clean_previous():
    for path in [DIST_DIR, BUILD_DIR]:
        if path.exists():
            print(f"清理目录: {path}")
            shutil.rmtree(path)


def copy_runtime_resources():
    # 拷贝 config.json 到产物根目录
    cfg_src = PROJECT_ROOT / "config.json"
    if cfg_src.exists():
        dst = APP_DIST_DIR / "config.json"
        print(f"复制配置: {cfg_src} -> {dst}")
        shutil.copy2(cfg_src, dst)
    else:
        print("提示：未找到 config.json，运行时将使用默认 mcp_config 目录")

    # 拷贝 mcp_config 目录到产物根目录
    mcp_src = PROJECT_ROOT / "app" / "mcp_config"
    mcp_dst = APP_DIST_DIR / "mcp_config"
    if mcp_src.exists():
        if mcp_dst.exists():
            shutil.rmtree(mcp_dst)
        print(f"复制目录: {mcp_src} -> {mcp_dst}")
        shutil.copytree(mcp_src, mcp_dst)
    else:
        print("提示：未找到 app/mcp_config 目录")


def build_with_spec():
    if not SPEC_FILE.exists():
        raise FileNotFoundError(f"未找到 spec 文件: {SPEC_FILE}")
    run([sys.executable, "-m", "PyInstaller", "--clean", "-y", str(SPEC_FILE)], cwd=PROJECT_ROOT)


def main():
    print("项目根目录:", PROJECT_ROOT)
    ensure_pyinstaller()
    clean_previous()
    build_with_spec()
    copy_runtime_resources()

    exe_path = APP_DIST_DIR / ("chat_app_server.exe" if os.name == "nt" else "chat_app_server")
    print("\n打包完成!")
    print("产物目录:", APP_DIST_DIR)
    print("可执行文件:", exe_path)
    print("\n运行示例:")
    if os.name == "nt":
        print(str(exe_path))
    else:
        print(f"{exe_path}")
        print("或")
        print(f"PORT=3001 {exe_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print("命令执行失败:", e)
        sys.exit(e.returncode)
    except Exception as e:
        print("打包失败:", e)
        sys.exit(1)