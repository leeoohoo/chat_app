"""
简单的配置文件读取工具
"""
import json
import os
from pathlib import Path
from typing import Optional

def get_config_dir() -> str:
    """
    从配置文件读取 config_dir 路径
    
    Returns:
        配置目录路径
    """
    # 获取项目根目录（当前文件的上上级目录）
    project_root = Path(__file__).parent.parent.parent.absolute()
    config_file = project_root / "config.json"
    
    try:
        # 读取配置文件
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config_dir = config.get("config_dir")
            if config_dir:
                return config_dir
    
    except Exception as e:
        print(f"读取配置文件失败: {e}")
    
    # 如果读取失败，返回默认路径
    default_config_dir = str(project_root / "mcp_config")
    print(f"使用默认配置目录: {default_config_dir}")
    return default_config_dir

def get_project_root() -> str:
    """
    获取项目根目录
    
    Returns:
        项目根目录路径
    """
    return str(Path(__file__).parent.parent.parent.absolute())