#!/usr/bin/env python3
"""
macOS 平台打包脚本（调用现有 Nuitka 构建脚本）

支持：
- 仅构建 arm64（Apple Silicon / M 系列）
- 仅构建 x64（Intel 芯片）
- 在支持的机器上一次构建两个架构（arm64 + x64）

说明：
- 实际打包由 scripts/build_nuitka.py 完成，本脚本只负责按指定架构调用。
- 在 Apple Silicon 上构建 x64 需要 Rosetta 2，并且 Python 解释器需为 universal2 或具备对应架构切片。

用法：
  python scripts/build_macos.py --targets arm64
  python scripts/build_macos.py --targets x64
  python scripts/build_macos.py --targets both
"""

import argparse
import os
import sys
import platform
import subprocess
from pathlib import Path


def is_darwin() -> bool:
    return platform.system().lower() == "darwin"


def run(cmd: list[str]) -> int:
    print("执行命令:")
    print(" ", " ".join(map(str, cmd)))
    completed = subprocess.run(cmd)
    return completed.returncode


def ensure_rosetta_hint() -> None:
    """在 Apple Silicon 上如果需要 x64 构建，给出 Rosetta 安装提示。"""
    print("提示：若命令失败且为 Apple Silicon，请安装 Rosetta 并确保 Python 支持 x86_64 切片：")
    print("  sudo softwareupdate --install-rosetta --agree-to-license")


def build_for_arch(target_arch: str) -> bool:
    """按指定架构调用 Nuitka 构建脚本。"""
    project_root = Path(__file__).parent.parent
    nuitka_script = project_root / "scripts" / "build_nuitka.py"

    if not is_darwin():
        print("✗ 非 macOS 平台，无法执行本脚本。")
        return False

    if target_arch == "arm64":
        cmd = ["arch", "-arm64", sys.executable, str(nuitka_script)]
        rc = run(cmd)
        if rc == 0:
            print("✓ arm64 构建完成。产物位于 dist/chat_app_server_nuitka_darwin_arm64")
            return True
        print("✗ arm64 构建失败。")
        return False

    if target_arch in ("x64", "x86_64"):
        # 在 Apple Silicon 上，需要 Rosetta 支持
        cmd = ["arch", "-x86_64", sys.executable, str(nuitka_script)]
        rc = run(cmd)
        if rc == 0:
            print("✓ x64 构建完成。产物位于 dist/chat_app_server_nuitka_darwin_x64")
            return True
        print("✗ x64 构建失败。")
        ensure_rosetta_hint()
        return False

    print(f"✗ 未知架构: {target_arch}")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="macOS 多架构打包入口")
    parser.add_argument(
        "--targets",
        choices=["arm64", "x64", "both"],
        default=None,
        help="选择要构建的目标架构"
    )
    return parser.parse_args()


def main() -> int:
    if not is_darwin():
        print("✗ 当前系统不是 macOS。")
        return 1

    args = parse_args()
    machine = platform.machine().lower()
    # 推断默认目标
    default_target = "x64"
    if machine in ("arm64", "aarch64"):
        default_target = "both"

    target_choice = args.targets or default_target
    print(f"目标选择: {target_choice}")

    if target_choice == "arm64":
        return 0 if build_for_arch("arm64") else 1
    if target_choice == "x64":
        return 0 if build_for_arch("x64") else 1
    if target_choice == "both":
        ok_arm = build_for_arch("arm64")
        ok_x64 = build_for_arch("x64")
        return 0 if (ok_arm and ok_x64) else 1

    print("✗ 无效的目标选择。")
    return 1


if __name__ == "__main__":
    sys.exit(main())