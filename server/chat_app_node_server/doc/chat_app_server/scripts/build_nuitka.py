#!/usr/bin/env python3
"""
使用 Nuitka 构建可执行文件（onefile）
适用于 macOS/Linux/Windows，默认输出到 dist_nuitka/

依赖：
  - nuitka (pip install nuitka)
  - 编译器（macOS 推荐安装 Xcode Command Line Tools）
  - 可选：ordered-set, zstandard（nuitka 会自动拉取，若失败可手动安装）
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")


def get_platform_info():
    system = platform.system().lower()
    arch = platform.machine().lower()
    if arch in ["x86_64", "amd64"]:
        arch = "x64"
    elif arch in ["aarch64", "arm64"]:
        arch = "arm64"
    elif arch in ["i386", "i686"]:
        arch = "x86"
    return system, arch


def ensure_nuitka_installed() -> bool:
    try:
        __import__("nuitka")
        return True
    except Exception:
        print("未检测到 nuitka，尝试安装...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "nuitka", "ordered-set", "zstandard"],
                check=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"安装 nuitka 失败: {e}")
            print("请手动执行: pip install nuitka ordered-set zstandard")
            return False


def build_with_nuitka() -> bool:
    system, arch = get_platform_info()
    project_root = Path(__file__).parent.parent
    main_file = project_root / "app" / "main.py"
    output_dir = project_root / "dist_nuitka"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 目标文件名（不含后缀）
    output_name = "chat_app_server"
    print("开始使用 Nuitka 构建...")

    # 目录型产物（standalone onedir），避免 onefile 的解压开销
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        str(main_file),
        "--standalone",  # 独立运行，携带依赖（输出到 <name>.dist/）
        f"--output-dir={output_dir}",
        f"--output-filename={output_name}",
        "--enable-plugin=anti-bloat",
        "--include-package=app",
    ]

    # 为常用依赖显式包含包，避免动态导入遗漏
    include_pkgs = [
        "uvicorn",
        "fastapi",
        "starlette",
        "anyio",
        "sniffio",
        "pydantic",
        "pydantic_core",
        "httpx",
        "h11",
        "openai",
        "mcp",
        "fastmcp",
        "typing_extensions",
    ]
    for pkg in include_pkgs:
        cmd += [f"--include-package={pkg}"]

    # 包含必要的数据文件（如配置）
    data_files = [
        (project_root / "config.json", "config.json"),
        (project_root / "config.mongodb.example.json", "config.mongodb.example.json"),
    ]
    for src, dst in data_files:
        if src.exists():
            cmd += [f"--include-data-files={src}={dst}"]

    # 优化编译参数
    cmd += ["--jobs=4"]
    cmd += ["--python-flag=-OO"]  # 移除断言与 docstring，减小体积
    # CI 环境避免交互式下载提示
    cmd += ["--assume-yes-for-downloads"]

    # macOS 使用 clang
    if system == "darwin":
        cmd += ["--clang", "--lto=yes"]
    elif system == "windows":
        # Windows 优先使用 MinGW64，避免 MSVC 配置复杂
        cmd += ["--mingw64", "--lto=yes"]
    else:
        cmd += ["--lto=yes"]

    print("执行命令:")
    print(" ", " ".join(map(str, cmd)))

    try:
        subprocess.run(cmd, check=True)
        # 结果路径（standalone 目录）
        produced_dir = output_dir / f"{main_file.stem}.dist"
        # 目录内的可执行文件名为 output_name（或 output_name.exe）
        produced_bin = produced_dir / (f"{output_name}.exe" if system == "windows" else output_name)

        if produced_dir.exists():
            print("✓ 构建成功:", produced_dir)
            if produced_bin.exists():
                size_mb = produced_bin.stat().st_size / 1024 / 1024
                print(f"主二进制大小: {size_mb:.1f} MB")
            # 将整目录移动到 dist/，保持风格统一
            final_dir = project_root / "dist" / f"chat_app_server_nuitka_{system}_{arch}"
            try:
                import shutil
                if final_dir.exists():
                    shutil.rmtree(final_dir)
                shutil.move(str(produced_dir), str(final_dir))
                print("✓ 产物已移动到:", final_dir)
            except Exception as move_err:
                print("移动产物目录失败:", move_err)
                print("注意: 产物位于:", produced_dir)
            return True
        else:
            print("✗ 未找到生成的目录产物")
            return False
    except subprocess.CalledProcessError as e:
        print("✗ Nuitka 构建失败")
        print(e)
        return False


def main():
    if not ensure_nuitka_installed():
        return False
    return build_with_nuitka()


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)