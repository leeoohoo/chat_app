#!/usr/bin/env bash

set -euo pipefail

# 设置 Python 优化环境变量
export PYTHONOPTIMIZE=2          # 启用最高级别优化
export PYTHONDONTWRITEBYTECODE=1 # 不生成 .pyc 文件
export PYTHONUNBUFFERED=1        # 不缓冲输出
export PYTHONHASHSEED=0          # 固定哈希种子

echo "启动 Chat App Server (优化模式)..."

# 优先在打包产物中运行（onedir）
if [[ -x "./chat_app_server" ]]; then
  exec ./chat_app_server
fi

if [[ -d "dist" ]]; then
  # 查找平台后缀目录，例如 chat_app_server_darwin_arm64 或 chat_app_server_linux_x64
  target_dir=$(ls -d dist/chat_app_server_* 2>/dev/null | head -n1 || true)
  if [[ -n "${target_dir}" ]] && [[ -x "${target_dir}/chat_app_server" ]]; then
    exec "${target_dir}/chat_app_server"
  fi
  # 兼容 Nuitka 目录型产物
  nuitka_dir=$(ls -d dist/chat_app_server_nuitka_* 2>/dev/null | head -n1 || true)
  if [[ -n "${nuitka_dir}" ]]; then
    if [[ -x "${nuitka_dir}/chat_app_server" ]]; then
      exec "${nuitka_dir}/chat_app_server"
    fi
    # 有些平台可执行名可能为 main
    if [[ -x "${nuitka_dir}/main" ]]; then
      exec "${nuitka_dir}/main"
    fi
  fi
fi

echo "未找到打包产物，回退到开发模式运行"
exec python -m app.main