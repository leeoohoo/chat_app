#!/usr/bin/env python3
"""
File Reader MCP Server（STDIO 版本，基于 FastMCP v2）
与 HTTP 版本保持工具与资源一致，用于本地 STDIO 传输启动。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

from fastmcp import FastMCP

try:
    # 包内导入（推荐：以模块方式运行）
    from .service import FileReaderService
except ImportError:
    # 直接运行脚本文件时的回退导入
    from file_reader_server_v2.service import FileReaderService


# 默认配置（可通过环境变量覆盖）
CONFIG: Dict[str, Any] = {
    "project_root": os.environ.get("FILE_READER_PROJECT_ROOT", str(Path.cwd())),
    "max_file_size": int(os.environ.get("FILE_READER_MAX_FILE_SIZE_MB", "10")),
    "enable_hidden_files": os.environ.get("FILE_READER_ENABLE_HIDDEN", "false").lower() == "true",
    "search_limit": int(os.environ.get("FILE_READER_SEARCH_LIMIT", "50")),
}


mcp = FastMCP("file-reader-server-v2-stdio")
service = FileReaderService(lambda key, default=None: CONFIG.get(key, default))


@mcp.tool()
async def read_file_lines(file_path: str, start_line: int, end_line: int):
    """📖 读取文件行范围并返回压缩带行号文本。"""
    root = Path(CONFIG.get("project_root", Path.cwd()))
    text = await service.read_file_lines(file_path, start_line, end_line, root)
    return text


@mcp.tool()
async def search_files_by_content(query: str, limit: int = CONFIG["search_limit"], context_lines: int = 20):
    """🔍 简易全局文本检索，返回包含行号的匹配片段。"""
    root = Path(CONFIG.get("project_root", Path.cwd()))
    text = await service.search_files_by_content(query, limit=limit, context_lines=context_lines, root=root)
    return text


@mcp.tool()
async def get_project_structure(max_depth: int = 10, include_hidden: bool = False):
    """🌳 返回项目结构与文件行数统计的文本视图。"""
    root = Path(CONFIG.get("project_root", Path.cwd()))
    text = await service.get_project_structure(max_depth=max_depth, include_hidden=include_hidden, root=root)
    return text


@mcp.resource("config://server", name="File Reader Configuration", description="当前文件读取服务配置")
def config_resource() -> str:
    info = {
        "project_root": CONFIG.get("project_root"),
        "max_file_size": CONFIG.get("max_file_size"),
        "enable_hidden_files": CONFIG.get("enable_hidden_files"),
        "search_limit": CONFIG.get("search_limit"),
        "supported_extensions": sorted(list(FileReaderService.TEXT_EXTENSIONS)),
        "ignored_directories": sorted(list(FileReaderService.DEFAULT_IGNORE_DIRS)),
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


@mcp.resource("stats://project", name="Project Statistics", description="项目文件与代码行数统计")
async def project_stats_resource() -> str:
    root = Path(CONFIG.get("project_root", Path.cwd()))
    stats = await service.get_project_stats(root)
    return json.dumps(stats, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 默认以 STDIO 传输运行
    mcp.run()