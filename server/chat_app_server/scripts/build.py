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
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True, text=True)
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
        # 使用PyInstaller构建
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--onefile',
            '--specpath', '.',
            'build.spec'
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 构建完成")
        
        # 获取生成的可执行文件路径
        dist_dir = Path('dist')
        if system == 'windows':
            exe_name = 'chat_app_server.exe'
        else:
            exe_name = 'chat_app_server'
        
        exe_path = dist_dir / exe_name
        
        if exe_path.exists():
            # 重命名为包含平台信息的文件名
            new_name = f'chat_app_server_{system}_{arch}'
            if system == 'windows':
                new_name += '.exe'
            
            new_path = dist_dir / new_name
            shutil.move(str(exe_path), str(new_path))
            
            print(f"✓ 可执行文件已生成: {new_path}")
            print(f"文件大小: {new_path.stat().st_size / 1024 / 1024:.1f} MB")
            
            return True
        else:
            print("✗ 未找到生成的可执行文件")
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
    required_files = ['main.py', 'requirements.txt', 'build.spec']
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