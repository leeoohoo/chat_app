#!/usr/bin/env python3
"""
简单的MCP Echo服务器
用于测试stdio协议支持
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict

# 配置日志到stderr，避免与stdio通信冲突
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class EchoMcpServer:
    """简单的MCP Echo服务器"""
    
    def __init__(self):
        self.tools = {
            "echo": {
                "name": "echo",
                "description": "回显输入的文本",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要回显的文本"
                        }
                    },
                    "required": ["text"]
                }
            },
            "uppercase": {
                "name": "uppercase",
                "description": "将文本转换为大写",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "要转换的文本"
                        }
                    },
                    "required": ["text"]
                }
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP请求"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            logger.debug(f"收到请求: {method}")
            
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "echo-server",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": list(self.tools.values())
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "echo":
                    text = arguments.get("text", "")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Echo: {text}"
                                }
                            ]
                        }
                    }
                
                elif tool_name == "uppercase":
                    text = arguments.get("text", "")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": text.upper()
                                }
                            ]
                        }
                    }
                
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
        
        except Exception as e:
            logger.error(f"处理请求时出错: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """运行服务器"""
        logger.info("Echo MCP服务器启动")
        
        try:
            while True:
                # 从stdin读取请求
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    logger.debug(f"解析请求: {request}")
                    
                    response = await self.handle_request(request)
                    
                    # 发送响应到stdout
                    response_json = json.dumps(response)
                    print(response_json, flush=True)
                    logger.debug(f"发送响应: {response_json}")
                
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
        
        except KeyboardInterrupt:
            logger.info("收到中断信号，服务器停止")
        except Exception as e:
            logger.error(f"服务器运行错误: {e}")
        finally:
            logger.info("Echo MCP服务器停止")


async def main():
    """主函数"""
    server = EchoMcpServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())