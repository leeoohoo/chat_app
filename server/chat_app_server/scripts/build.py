#!/usr/bin/env python3
"""
构建脚本 - 用于打包Python聊天应用服务器
支持Windows、macOS、Linux跨平台打包
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def get_platform_info():
    """获取平台信息"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if arch in ['x86_64', 'amd64']:
        arch = 'x64'
    elif arch in ['aarch64', 'arm64']:
        arch = 'arm64'
    elif arch in ['i386', 'i686']:
        arch = 'x86'
    
    return system, arch

def install_dependencies():
    """安装依赖"""
    print("正在安装依赖...")
    try:
        # 增加网络超时与降级选项，提高安装稳定性
        base_cmd = [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--default-timeout', '120']
        try:
            subprocess.run(base_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            # 失败后尝试不使用缓存再次安装，并使用旧解析器以绕过冲突
            fallback_cmd = base_cmd + ['--no-cache-dir', '--use-deprecated=legacy-resolver']
            subprocess.run(fallback_cmd, check=True, capture_output=True, text=True)
        print("✓ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def build_executable():
    """构建可执行文件"""
    print("正在构建可执行文件...")
    
    system, arch = get_platform_info()
    
    try:
        # 清理可能存在的上次输出目录（onedir 目标目录）
        dist_root = Path('dist')
        target_dir = dist_root / ('chat_app_server.exe' if system == 'windows' else 'chat_app_server')
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)
        
        # 使用 PyInstaller 构建（指定 .spec 文件时不再传递 makespec 相关参数）
        cmd = [sys.executable, '-m', 'PyInstaller', 'build.spec']
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 构建完成")
        
        # 获取生成的可执行文件路径
        dist_dir = Path('dist')
        if system == 'windows':
            exe_name = 'chat_app_server.exe'
        else:
            exe_name = 'chat_app_server'

        # 支持 onedir：目录中包含可执行文件及依赖
        exe_file_path = dist_dir / exe_name
        exe_dir_path = dist_dir / exe_name

        if exe_file_path.exists() and exe_file_path.is_file():
            # onefile 情况（保留兼容）
            new_name = f'chat_app_server_{system}_{arch}'
            if system == 'windows':
                new_name += '.exe'
            new_path = dist_dir / new_name
            shutil.move(str(exe_file_path), str(new_path))
            print(f"✓ 可执行文件已生成: {new_path}")
            print(f"文件大小: {new_path.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        elif exe_dir_path.exists() and exe_dir_path.is_dir():
            # onedir 情况：将目录重命名为带平台后缀
            new_dir_name = f'chat_app_server_{system}_{arch}'
            new_dir_path = dist_dir / new_dir_name
            if new_dir_path.exists():
                shutil.rmtree(new_dir_path)
            shutil.move(str(exe_dir_path), str(new_dir_path))
            # 统计主可执行文件大小
            main_binary = 'chat_app_server.exe' if system == 'windows' else 'chat_app_server'
            main_binary_path = new_dir_path / main_binary
            if main_binary_path.exists():
                print(f"✓ 可执行目录已生成: {new_dir_path}")
                print(f"主程序大小: {main_binary_path.stat().st_size / 1024 / 1024:.1f} MB")
            else:
                print(f"✓ 可执行目录已生成: {new_dir_path}")
            return True
        else:
            print("✗ 未找到生成的产物 (既非文件也非目录)")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"✗ 构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def clean_build_files():
    """清理构建文件"""
    print("正在清理构建文件...")
    
    dirs_to_clean = ['build', '__pycache__']
    files_to_clean = ['*.pyc', '*.pyo']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ 已删除 {dir_name}")
    
    # 清理Python缓存文件
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs[:]:
            if dir_name == '__pycache__':
                shutil.rmtree(os.path.join(root, dir_name))
                dirs.remove(dir_name)

def create_readme():
    """创建使用说明"""
    readme_content = """# 聊天应用服务器

## 使用方法

1. 直接运行可执行文件：
   ```
   ./chat_app_server  # Linux/macOS
   chat_app_server.exe  # Windows
   ```

2. 服务器将在 http://localhost:8000 启动

3. API文档可在 http://localhost:8000/docs 查看

## 配置

服务器会自动创建 SQLite 数据库文件 `chat_app.db`

## 环境变量

- `OPENAI_API_KEY`: OpenAI API密钥
- `OPENAI_BASE_URL`: OpenAI API基础URL（可选）
- `PORT`: 服务器端口（默认8000）

## 支持的平台

- Windows (x64, x86)
- macOS (x64, arm64)
- Linux (x64, arm64)
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✓ 已创建 README.md")

def main():
    """主函数"""
    print("=" * 50)
    print("聊天应用服务器构建工具")
    print("=" * 50)
    
    system, arch = get_platform_info()
    print(f"当前平台: {system} {arch}")
    print()
    
    # 检查必要文件
    required_files = ['app/main.py', 'requirements.txt', 'build.spec']
    for file in required_files:
        if not os.path.exists(file):
            print(f"✗ 缺少必要文件: {file}")
            return False
    
    # 安装依赖
    if not install_dependencies():
        return False
    
    print()
    
    # 构建可执行文件
    if not build_executable():
        return False
    
    print()
    
    # 清理构建文件
    clean_build_files()
    
    print()
    
    # 创建说明文档
    create_readme()
    
    print()
    print("=" * 50)
    print("构建完成！")
    print("可执行文件位于 dist/ 目录中")
    print("=" * 50)
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)