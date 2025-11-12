import threading
from typing import Dict, Optional

_modules: Dict[str, object] = {}
_loading_complete = threading.Event()

def preload_modules() -> None:
    """在后台线程预加载可能较慢的第三方模块"""
    try:
        import fastmcp  # noqa: F401
        _modules["fastmcp"] = fastmcp

        import mcp  # noqa: F401
        _modules["mcp"] = mcp

        import openai  # noqa: F401
        _modules["openai"] = openai

        import httpx  # noqa: F401
        _modules["httpx"] = httpx
    except Exception:
        # 失败不影响主流程
        pass
    finally:
        _loading_complete.set()

def start_preload() -> None:
    """启动后台预加载线程"""
    try:
        t = threading.Thread(target=preload_modules, daemon=True)
        t.start()
    except Exception:
        pass

def get_module(name: str, timeout: float = 10.0) -> Optional[object]:
    """获取预加载的模块（最多等待指定秒数）"""
    try:
        _loading_complete.wait(timeout=timeout)
    except Exception:
        pass
    return _modules.get(name)