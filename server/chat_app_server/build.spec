# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform

# 设置合理的递归深度
sys.setrecursionlimit(5000)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# 收集数据文件和元数据
datas = []
metadata_packages = [
    'fastmcp', 'pydantic', 'pydantic_core', 'fastapi',
    'uvicorn', 'openai', 'httpx', 'mcp', 'anyio', 'sniffio'
]

for package in metadata_packages:
    try:
        datas += copy_metadata(package)
    except Exception as e:
        print(f"Warning: Failed to collect metadata for {package}: {e}")

# 基础隐藏导入
hiddenimports = [
    # === ANYIO 相关（重点） ===
    'anyio',
    'anyio._core',
    'anyio._backends',
    'anyio._backends._asyncio',
    'anyio._backends._trio',
    'anyio.abc',
    'anyio.lowlevel',
    'anyio.streams',
    'anyio.streams.buffered',
    'anyio.streams.file',
    'anyio.streams.memory',
    'anyio.streams.stapled',
    'anyio.streams.text',
    'anyio.streams.tls',
    'anyio.from_thread',
    'anyio.to_thread',
    'anyio.to_process',
    'anyio.pytest_plugin',
    'sniffio',
    
    # === 核心 Web 框架 ===
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    
    # === FastAPI ===
    'fastapi',
    'fastapi.responses',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.routing',
    'fastapi.dependencies',
    'fastapi.security',
    
    # === Pydantic ===
    'pydantic',
    'pydantic.v1',
    'pydantic._internal',
    'pydantic._internal._signature',
    'pydantic._internal._config',
    'pydantic._internal._decorators',
    'pydantic._internal._fields',
    'pydantic._internal._generate_schema',
    'pydantic._internal._model_construction',
    'pydantic._internal._typing_extra',
    'pydantic._internal._utils',
    'pydantic._internal._validators',
    'pydantic_settings',
    'pydantic_settings.main',
    'pydantic_core',
    'pydantic_core._pydantic_core',
    
    # === MCP 相关 ===
    'mcp',
    'mcp.server',
    'mcp.types',
    'fastmcp',
    'fastmcp.server',
    'fastmcp.utilities',
    
    # === 其他核心模块 ===
    'aiosqlite',
    'sqlite3',
    'openai',
    'openai.types',
    'openai.types.chat',
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
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
    
    # === 标准库模块 ===
    'json',
    'logging',
    'asyncio',
    'concurrent.futures',
    'multiprocessing',
    'threading',
    'queue',
    'collections',
    'functools',
    'itertools',
    'datetime',
    'uuid',
    'hashlib',
    'base64',
    'urllib',
    'urllib.parse',
    'urllib.request',
]

# 强制收集关键模块的所有子模块
critical_modules = ['anyio', 'sniffio', 'fastmcp', 'mcp', 'pydantic', 'pydantic_core']

for module in critical_modules:
    try:
        submodules = collect_submodules(module)
        hiddenimports += submodules
        print(f"Collected {len(submodules)} submodules for {module}")
    except Exception as e:
        print(f"Warning: Failed to collect submodules for {module}: {e}")

# 去重
hiddenimports = list(set(hiddenimports))
print(f"Total hiddenimports: {len(hiddenimports)}")

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
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
    ],
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
    [],
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

# 生成目录型产物
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