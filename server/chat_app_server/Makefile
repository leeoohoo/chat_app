# Makefile for Chat App Server

.PHONY: help install dev build clean test

# 默认目标
help:
	@echo "可用命令:"
	@echo "  install  - 安装依赖"
	@echo "  dev      - 启动开发服务器"
	@echo "  build    - 构建可执行文件"
	@echo "  clean    - 清理构建文件"
	@echo "  test     - 运行测试"

# 安装依赖
install:
	@echo "安装Python依赖..."
	pip install -r requirements.txt

# 启动开发服务器
dev:
	@echo "启动开发服务器..."
	python scripts/start.py

# 构建可执行文件
build:
	@echo "构建可执行文件..."
	python scripts/build_nuitka.py

# 使用 Nuitka 构建可执行文件
build_nuitka:
	@echo "使用 Nuitka 构建可执行文件..."
	python scripts/build_nuitka.py

# macOS: 仅 arm64 构建
build_macos_arm64:
	@echo "构建 macOS arm64 产物..."
	python scripts/build_macos.py --targets arm64

# macOS: 仅 x64 构建
build_macos_x64:
	@echo "构建 macOS x64 产物..."
	python scripts/build_macos.py --targets x64

# macOS: 双构建（arm64 + x64）
build_macos_both:
	@echo "构建 macOS arm64 + x64 产物..."
	python scripts/build_macos.py --targets both

# Windows: 提示使用批处理脚本
build_windows:
	@echo "请在 Windows 环境运行 scripts\\build_windows.bat 进行打包"

# 清理构建文件
clean:
	@echo "清理构建文件..."
	rm -rf build dist __pycache__ *.pyc *.pyo
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# 运行测试
test:
	@echo "运行API测试..."
	python -m pytest tests/ -v

# 快速启动（安装依赖并启动）
start: install dev

# 完整构建（清理、安装、构建）
release: clean install build