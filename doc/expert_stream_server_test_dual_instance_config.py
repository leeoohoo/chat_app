#!/usr/bin/env python3
"""
测试双实例配置管理
使用新的 SimpleClient 验证不同配置的 ExpertStreamServer 实例能够正确工作
"""

import asyncio
import sys
import os
from mcp_framework.client.simple import SimpleClient


class DualInstanceTester:
    def __init__(self, server_script: str):
        self.server_script = server_script
    
    async def test_instance_with_alias(self, alias: str):
        """测试指定别名的实例"""
        print(f"\n🧪 测试实例 '{alias}'...")
        
        try:
            async with SimpleClient(self.server_script, alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
                print(f"✅ 成功连接到实例 '{alias}'")
                
                # 获取工具列表
                tools = await client.tools()
                print(f"   可用工具数量: {len(tools)}")
                
                # 验证 query_expert_stream 工具存在
                has_expert_tool = await client.has_tool("query_expert_stream")
                if not has_expert_tool:
                    print(f"❌ 实例 '{alias}' 缺少 query_expert_stream 工具")
                    return False
                
                print(f"✅ 实例 '{alias}' 包含 query_expert_stream 工具")
                
                # 测试专家查询
                print(f"   测试专家查询...")
                
                try:
                    result = await client.call("query_expert_stream",
                        question=f"这是来自实例 {alias} 的测试查询，请简单回复确认收到。"
                    )
                    print(f"   ✅ 专家查询成功")
                    response_preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                    print(f"   响应预览: {response_preview}")
                except Exception as e:
                    print(f"   ❌ 专家查询失败: {e}")
                    return False
                
                return True
                
        except Exception as e:
            print(f"❌ 测试实例 '{alias}' 时发生错误: {e}")
            return False

    async def test_concurrent_instances(self):
        """测试并发访问不同实例"""
        print(f"\n🧪 测试并发访问不同实例...")
        
        async def test_instance_concurrent(alias: str):
            """并发测试单个实例"""
            try:
                async with SimpleClient(self.server_script, alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
                    # 发送测试查询
                    result = await client.call("query_expert_stream",
                        question=f"并发测试 - 实例 {alias}，请回复确认。时间戳: {asyncio.get_event_loop().time()}"
                    )
                    
                    return True, alias, result
            except Exception as e:
                return False, alias, str(e)
        
        try:
            # 并发测试两个实例
            tasks = [
                test_instance_concurrent("test_no_config"),
                test_instance_concurrent("test_with_config")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            for result in results:
                if isinstance(result, Exception):
                    print(f"   ❌ 并发测试异常: {result}")
                else:
                    success, alias, content = result
                    if success:
                        print(f"   ✅ 实例 '{alias}' 并发测试成功")
                        success_count += 1
                    else:
                        print(f"   ❌ 实例 '{alias}' 并发测试失败: {content}")
            
            return success_count == len(tasks)
            
        except Exception as e:
            print(f"❌ 并发测试失败: {e}")
            return False

    async def test_instance_isolation(self):
        """测试实例隔离性"""
        print(f"\n🧪 测试实例隔离性...")
        
        try:
            # 在第一个实例中设置配置
            async with SimpleClient(self.server_script, alias="test_no_config", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client1:
                await client1.set("test_isolation_1", "实例1的配置值")
                print("   ✅ 实例1设置配置成功")
            
            # 在第二个实例中设置不同的配置
            async with SimpleClient(self.server_script, alias="test_with_config", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client2:
                await client2.set("test_isolation_2", "实例2的配置值")
                print("   ✅ 实例2设置配置成功")
            
            # 验证每个实例都能访问自己的配置
            async with SimpleClient(self.server_script, alias="test_no_config", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client1:
                value1 = await client1.get("test_isolation_1", "未设置")
                if value1 == "实例1的配置值":
                    print("   ✅ 实例1能访问自己的配置")
                else:
                    print(f"   ❌ 实例1配置验证失败: {value1}")
                    return False
            
            async with SimpleClient(self.server_script, alias="test_with_config", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client2:
                value2 = await client2.get("test_isolation_2", "未设置")
                if value2 == "实例2的配置值":
                    print("   ✅ 实例2能访问自己的配置")
                else:
                    print(f"   ❌ 实例2配置验证失败: {value2}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ 实例隔离测试失败: {e}")
            return False

    async def test_configuration_differences(self):
        """测试不同配置的差异"""
        print(f"\n🧪 测试配置差异...")
        
        try:
            configs = {}
            
            # 获取两个实例的工具信息
            for alias in ["test_no_config", "test_with_config"]:
                async with SimpleClient(self.server_script, alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
                    tools = await client.tools()
                    tool_info = await client.tool_info("query_expert_stream") if await client.has_tool("query_expert_stream") else None
                    
                    configs[alias] = {
                        "tool_count": len(tools),
                        "has_expert_tool": tool_info is not None,
                        "tool_description": tool_info.description if tool_info else None
                    }
                    
                    print(f"   实例 '{alias}': {configs[alias]['tool_count']} 个工具")
            
            # 比较配置
            config1 = configs["test_no_config"]
            config2 = configs["test_with_config"]
            
            print(f"   配置比较:")
            print(f"     test_no_config: {config1['tool_count']} 工具, query_expert_stream: {config1['has_expert_tool']}")
            print(f"     test_with_config: {config2['tool_count']} 工具, query_expert_stream: {config2['has_expert_tool']}")
            
            # 验证两个实例都有基本功能
            if config1['has_expert_tool'] and config2['has_expert_tool']:
                print("   ✅ 两个实例都支持 query_expert_stream 工具")
                return True
            else:
                print("   ❌ 某些实例缺少必要工具")
                return False
                
        except Exception as e:
            print(f"❌ 配置差异测试失败: {e}")
            return False

    async def test_config_management(self):
        """测试配置管理功能 - 使用 SimpleClient"""
        print(f"\n🧪 测试配置管理功能（SimpleClient）...")
        
        try:
            # 为两个实例设置不同的配置 - 包含所有可用的配置参数
            configs_to_test = {
                "test_no_config1": {
                    "server_name": "ExpertStreamServer",
                    "log_level": "DEBUG",
                    "max_connections": 50,
                    "timeout": 60,
                    # 核心配置参数
                    "api_key": "sk-4jkOOy4t0qnY2t0rCQbEddyZaaMpYscsGZQ32Fa34GnIND8p",
                    "model_name": "kimi-k2-0905-preview",
                    "base_url": "https://api.openai.com/v1",
                    "system_prompt": "你是一个专业的AI助手，能够提供准确、详细和有用的回答。",
                    # MCP服务器配置（测试模式下为空）
                    "mcp_servers": "[]",
                    # stdio MCP服务器配置
                    "stdio_mcp_servers": "",
                    # 数据库配置
                    "mongodb_url": "",
                    # 历史记录配置
                    "history_limit": "10",
                    "enable_history": False,
                    # 角色和工具配置
                    "role": "development_assistant",
                    "tool_description": "🤖 **Development Assistant** - Professional Development Task Executor",
                    "parameter_description": "🎯 **Task Request Parameter**: Send task request to development assistant",
                    # 总结配置
                    "summary_interval": 5,
                    "max_rounds": 25,
                    "summary_instruction": "You are a professional conversation analysis and requirement prediction expert.",
                    "summary_request": "Please intelligently analyze and generate a precise data retention report.",
                    "summary_length_threshold": 30000,
                    # 自定义设置
                    "custom_setting": "expert_server1_value"
                },
                "test_with_config": {
                    "server_name": "ExpertStreamServer", 
                    "log_level": "WARNING",
                    "max_connections": 20,
                    "timeout": 45,
                    # 核心配置参数
                    "api_key": "sk-test-key-for-testing-purposes-only-0987654321",
                    "model_name": "gpt-4",
                    "base_url": "https://api.openai.com/v1",
                    "system_prompt": "你是一个专业的AI助手，能够通过工具帮用查询当前目录下的内容。",
                    # MCP服务器配置（测试模式下为空）
                    "mcp_servers": "[]",
                    # stdio MCP服务器配置
                    "stdio_mcp_servers": "file-writer:../file_write_server/file_write_server.py--test_no_config",
                    # 数据库配置
                    "mongodb_url": "mongodb://localhost:27017/chat_history",
                    # 历史记录配置
                    "history_limit": "20",
                    "enable_history": True,
                    # 角色和工具配置
                    "role": "code_reviewer",
                    "tool_description": "🔧 **Code Review Assistant** - Advanced Code Analysis Tool",
                    "parameter_description": "📝 **Code Analysis Parameter**: Submit code for professional review",
                    # 总结配置
                    "summary_interval": 3,
                    "max_rounds": 15,
                    "summary_instruction": "You are an expert code analyzer. Focus on critical code patterns and potential issues.",
                    "summary_request": "Generate a comprehensive code analysis summary with actionable insights.",
                    "summary_length_threshold": 20000,
                    # 自定义设置
                    "custom_setting": "expert_server2_value"
                }
            }
            
            success_count = 0
            
            for alias, config_data in configs_to_test.items():
                print(f"\n   测试实例 '{alias}' 的配置管理...")
                
                try:
                    # 使用 SimpleClient 进行配置管理
                    async with SimpleClient(self.server_script, alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
                        print(f"   ✅ 成功连接到 SimpleClient '{alias}'")
                        
                        # 获取当前配置
                        current_config = await client.config()
                        print(f"   📋 当前配置: {len(current_config)} 项")
                        
                        # 批量更新配置
                        print(f"   🔧 批量更新配置...")
                        update_success = await client.update(**config_data)
                        if update_success:
                            print(f"   ✅ 配置批量更新成功")
                        else:
                            print(f"   ⚠️  配置批量更新返回 False")
                        
                        # 逐个设置关键配置项（确保设置成功）
                        key_configs = [
                            ("custom_setting", config_data["custom_setting"]),
                            ("model_name", config_data["model_name"]),
                            ("log_level", config_data["log_level"])
                        ]
                        
                        for key, value in key_configs:
                            set_success = await client.set(key, value)
                            if set_success:
                                print(f"   ✅ 设置 {key} = {value}")
                            else:
                                print(f"   ⚠️  设置 {key} 失败")
                        
                        # 验证配置更新
                        updated_config = await client.config()
                        print(f"   🔍 验证配置: {len(updated_config)} 项")
                        
                        # 检查关键配置项
                        expected_setting = config_data["custom_setting"]
                        actual_setting = await client.get("custom_setting", "未设置")
                        
                        if actual_setting == expected_setting:
                            print(f"   ✅ 配置验证成功: custom_setting = {actual_setting}")
                            success_count += 1
                        else:
                            print(f"   ❌ 配置验证失败: 期望 {expected_setting}, 实际 {actual_setting}")
                        
                        # 显示其他配置项
                        model_name = await client.get("model_name", "未设置")
                        log_level = await client.get("log_level", "未设置")
                        print(f"   📊 其他配置: model_name={model_name}, log_level={log_level}")
                            
                except Exception as e:
                    print(f"   ❌ 实例 '{alias}' 配置管理失败: {e}")
            
            return success_count == len(configs_to_test)
            
        except Exception as e:
            print(f"❌ 配置管理测试失败: {e}")
            return False

    async def test_config_with_simple_client(self):
        """测试 SimpleClient 的配置功能"""
        print(f"\n🧪 测试 SimpleClient 配置功能...")
        
        try:
            success_count = 0
            
            for alias in ["test_no_config", "test_with_config"]:
                print(f"\n   测试实例 '{alias}' 的 SimpleClient 配置...")
                
                try:
                    async with SimpleClient(self.server_script, alias=alias, config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
                        # 获取配置
                        config = await client.config()
                        print(f"   📋 获取配置成功: {len(config)} 项")
                        
                        # 设置单个配置项
                        test_key = f"test_key_{alias}"
                        test_value = f"test_value_{alias}"
                        await client.set(test_key, test_value)
                        print(f"   ✅ 设置配置项成功: {test_key} = {test_value}")
                        
                        # 批量更新配置 - 包含所有主要配置参数
                        batch_config = {
                            "batch_test_1": f"batch_value_1_{alias}",
                            "batch_test_2": f"batch_value_2_{alias}",
                            "enable_test_mode": True,
                            # 核心配置参数测试
                            "model_name": f"test-model-{alias}",
                            "base_url": f"https://test-api-{alias}.com/v1",
                            "system_prompt": f"测试系统提示词 for {alias}",
                            # MCP服务器配置测试
                            "mcp_servers": f"test-server:http://localhost:800{len(alias)}/mcp",
                            # stdio MCP服务器配置测试
                            "stdio_mcp_servers": f"test-stdio-{alias}:../file_write_server/file_write_server.py--test-{alias}" if alias == "test_with_config" else "",
                            # 历史记录配置测试
                            "history_limit": "15" if alias == "test_no_config" else "25",
                            "enable_history": alias == "test_with_config",
                            # 角色和工具配置测试
                            "role": f"test_role_{alias}",
                            "tool_description": f"🧪 **Test Tool for {alias}** - Testing Configuration",
                            "parameter_description": f"📋 **Test Parameter for {alias}**: Configuration testing parameter",
                            # 总结配置测试
                            "summary_interval": 3 if alias == "test_no_config" else 7,
                            "max_rounds": 20 if alias == "test_no_config" else 30,
                            "summary_instruction": f"Test summary instruction for {alias}",
                            "summary_request": f"Test summary request for {alias}",
                            "summary_length_threshold": 25000 if alias == "test_no_config" else 35000
                        }
                        await client.update(**batch_config)
                        print(f"   ✅ 批量更新配置成功: {len(batch_config)} 项")
                        
                        # 验证配置
                        updated_config = await client.config()
                        if test_key in updated_config and updated_config[test_key] == test_value:
                            print(f"   ✅ 配置验证成功")
                            success_count += 1
                        else:
                            print(f"   ❌ 配置验证失败")
                            
                except Exception as e:
                    print(f"   ❌ 实例 '{alias}' SimpleClient 配置测试失败: {e}")
            
            return success_count == 2
            
        except Exception as e:
            print(f"❌ SimpleClient 配置测试失败: {e}")
            return False


async def main():
    """主测试函数"""
    # 设置测试环境变量
    import os
    os.environ["TESTING_MODE"] = "true"
    
    print("🚀 ExpertStreamServer 双实例配置测试")
    print("=" * 60)
    
    # 创建测试器
    tester = DualInstanceTester("./dist/expert-stream-server")
    
    try:
        # 测试第一个实例
        print("\n🎯 测试 1: 无配置实例 (test_no_config)")
        success1 = await tester.test_instance_with_alias("test_no_config")
        
        # 测试第二个实例
        print("\n🎯 测试 2: 有配置实例 (test_with_config)")
        success2 = await tester.test_instance_with_alias("test_with_config")
        
        # 测试并发访问
        print("\n🎯 测试 3: 并发访问测试")
        success3 = await tester.test_concurrent_instances()
        
        # 测试实例隔离
        print("\n🎯 测试 4: 实例隔离测试")
        success4 = await tester.test_instance_isolation()
        
        # 测试配置差异
        print("\n🎯 测试 5: 配置差异测试")
        success5 = await tester.test_configuration_differences()
        
        # 测试配置管理
        print("\n🎯 测试 6: 配置管理测试")
        success6 = await tester.test_config_management()
        
        # 测试 SimpleClient 配置
        print("\n🎯 测试 7: SimpleClient 配置测试")
        success7 = await tester.test_config_with_simple_client()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 无配置实例测试: {'通过' if success1 else '失败'}")
        print(f"✅ 有配置实例测试: {'通过' if success2 else '失败'}")
        print(f"✅ 并发访问测试: {'通过' if success3 else '失败'}")
        print(f"✅ 实例隔离测试: {'通过' if success4 else '失败'}")
        print(f"✅ 配置差异测试: {'通过' if success5 else '失败'}")
        print(f"✅ 配置管理测试: {'通过' if success6 else '失败'}")
        print(f"✅ SimpleClient配置测试: {'通过' if success7 else '失败'}")
        
        if all([success1, success2, success3, success4, success5, success6, success7]):
            print("\n🎉 所有双实例配置测试通过！")
            result = 0
        else:
            print("\n❌ 部分双实例配置测试失败")
            result = 1
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        result = 1
    
    return result


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))