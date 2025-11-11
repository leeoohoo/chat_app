# -*- mode: python ; coding: utf-8 -*-

import os
import sys
# 增加递归深度以避免 PyInstaller 导入递归过深导致的 RecursionError
sys.setrecursionlimit(sys.getrecursionlimit() * 5)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# 收集数据文件
datas = []
datas += copy_metadata('fastmcp')

# 收集隐藏导入
hiddenimports = [
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'fastapi',
    'fastapi.responses',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'pydantic',
    'pydantic.v1',
    'pydantic._internal',
    'pydantic._internal._signature',
    'pydantic_settings',
    'pydantic_settings.main',
    'aiosqlite',
    'openai',
    'openai.types',
    'openai.types.chat',
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'sniffio',
    'h11',
    'h11._util',
    'click',
    'starlette',
    'starlette.applications',
    'starlette.middleware',
    'starlette.responses',
    'starlette.routing',
    'typing_extensions',
    'email_validator',
    'python_multipart',
    # 高性能事件循环与HTTP解析器
    'uvloop',
    'httptools',
]

# 额外收集子模块，避免运行时缺失（pydantic v2 / pydantic_settings / fastmcp）
hiddenimports += [
    'pydantic_core',
    'pydantic_core._pydantic_core'
]
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic._internal')
hiddenimports += collect_submodules('pydantic_settings')
hiddenimports += collect_submodules('fastmcp')
hiddenimports += collect_submodules('pydantic_core')
hiddenimports += collect_submodules('uvloop')
hiddenimports += collect_submodules('httptools')

# 分析主程序
a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 创建PYZ文件
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],  # 在 onedir 模式下，EXE 不直接包含二进制和数据
    [],
    [],
    [],
    name='chat_app_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    exclude_binaries=True,
)

# 生成目录型产物（onedir），避免 onefile 启动时的自解压开销
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='chat_app_server'
)