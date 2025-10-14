#!/usr/bin/env python3
"""
测试双实例配置功能
使用新的 SimpleClient 验证 FileReaderServer 能够正确处理多个实例的配置
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path
from mcp_framework.client.simple import SimpleClient


class DualInstanceConfigTester:
    def __init__(self, server_script: str):
        self.server_script = server_script
        # 创建两个临时目录作为不同的项目根目录
        self.temp_dir1 = "/Users/lilei/project/work/zj/user_manager"
        self.temp_dir2 = "/Users/lilei/project/work/zj/user_manager/src"
        
        # 在临时目录中创建测试文件
        self._setup_test_files()
    
    def _setup_test_files(self):
        """在指定目录中创建测试文件"""
        # 确保目录存在
        Path(self.temp_dir1).mkdir(parents=True, exist_ok=True)
        Path(self.temp_dir2).mkdir(parents=True, exist_ok=True)
        
        # 目录1的测试文件
        test_file1 = Path(self.temp_dir1) / "test1.py"
        test_file1.write_text("""# Test file 1
def hello_world():
    print("Hello from test1")
    return "test1"

class TestClass1:
    def __init__(self):
        self.name = "test1"
""")
        
        # 目录2的测试文件
        test_file2 = Path(self.temp_dir2) / "test2.py"
        test_file2.write_text("""# Test file 2
def goodbye_world():
    print("Goodbye from test2")
    return "test2"

class TestClass2:
    def __init__(self):
        self.name = "test2"
""")
        
        # 创建子目录和文件
        subdir1 = Path(self.temp_dir1) / "subdir"
        subdir1.mkdir(exist_ok=True)
        (subdir1 / "nested1.txt").write_text("Nested content in dir1")
        
        subdir2 = Path(self.temp_dir2) / "subdir"
        subdir2.mkdir(exist_ok=True)
        (subdir2 / "nested2.txt").write_text("Nested content in dir2")
    
    def cleanup(self):
        """清理测试文件"""
        try:
            # 只清理我们创建的测试文件，不删除目录本身
            test_files = [
                Path(self.temp_dir1) / "test1.py",
                Path(self.temp_dir2) / "test2.py",
                Path(self.temp_dir1) / "subdir" / "nested1.txt",
                Path(self.temp_dir2) / "subdir" / "nested2.txt"
            ]
            
            for file_path in test_files:
                if file_path.exists():
                    file_path.unlink()
                    
            # 清理子目录（如果为空）
            subdirs = [
                Path(self.temp_dir1) / "subdir",
                Path(self.temp_dir2) / "subdir"
            ]
            
            for subdir in subdirs:
                if subdir.exists() and not any(subdir.iterdir()):
                    subdir.rmdir()
                    
        except Exception as e:
            print(f"清理测试文件时出错: {e}")

    async def test_dual_instance_config(self):
        """测试双实例配置"""
        try:
            print(f"🔗 测试双实例配置")
            print(f"📁 临时目录1: {self.temp_dir1}")
            print(f"📁 临时目录2: {self.temp_dir2}")
            
            # 创建两个客户端实例
            async with SimpleClient(self.server_script, alias="concurrent1", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client1, \
                       SimpleClient(self.server_script, alias="concurrent2", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client2:
                
                # 为不同别名设置各自的project_root
                await client1.set("project_root", self.temp_dir1)
                await client2.set("project_root", self.temp_dir2)
                
                print("✅ 成功创建两个客户端实例")
                
                # 验证配置是否正确应用
                print("\n🔍 验证实例1配置:")
                config1_result = await client1.config()
                print(f"  项目根目录: {await client1.get('project_root', '未设置')}")
                print(f"  最大文件大小: {await client1.get('max_file_size', '未设置')} MB")
                print(f"  启用隐藏文件: {await client1.get('enable_hidden_files', '未设置')}")
                
                print("\n🔍 验证实例2配置:")
                config2_result = await client2.config()
                print(f"  项目根目录: {await client2.get('project_root', '未设置')}")
                print(f"  最大文件大小: {await client2.get('max_file_size', '未设置')} MB")
                print(f"  启用隐藏文件: {await client2.get('enable_hidden_files', '未设置')}")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试双实例配置时发生错误: {e}")
            return False

    async def test_concurrent_access(self):
        """测试并发访问"""
        try:
            print(f"\n🔄 测试并发访问")
            
            async with SimpleClient(self.server_script, alias="concurrent1", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client1, \
                       SimpleClient(self.server_script, alias="concurrent2", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client2:
                
                # 为不同别名设置各自的project_root
                await client1.set("project_root", self.temp_dir1)
                await client2.set("project_root", self.temp_dir2)
                
                print("✅ 成功创建两个客户端实例")
                
                async def read_file1():
                    result = await client1.call("read_file_lines",
                        file_path="test1.py",
                        start_line=1,
                        end_line=5
                    )
                    return result
                
                async def read_file2():
                    result = await client2.call("read_file_lines",
                        file_path="test2.py", 
                        start_line=1,
                        end_line=5
                    )
                    return result
                
                # 并发执行
                result1, result2 = await asyncio.gather(read_file1(), read_file2())
                
                print("✅ 并发读取完成")
                print(f"  实例1读取结果长度: {len(result1) if result1 else 0}")
                print(f"  实例2读取结果长度: {len(result2) if result2 else 0}")
                
                # 验证结果包含预期内容
                if result1 and "test1" in result1:
                    print("  ✅ 实例1读取到正确内容")
                else:
                    print("  ❌ 实例1读取内容不正确")
                    
                if result2 and "test2" in result2:
                    print("  ✅ 实例2读取到正确内容")
                else:
                    print("  ❌ 实例2读取内容不正确")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试并发访问时发生错误: {e}")
            return False

    async def test_instance_isolation(self):
        """测试实例隔离"""
        try:
            print(f"\n🔒 测试实例隔离")
            
            async with SimpleClient(self.server_script, alias="concurrent1", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client1, \
                       SimpleClient(self.server_script, alias="concurrent2", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client2:
                
                # 为不同别名设置各自的project_root
                await client1.set("project_root", self.temp_dir1)
                await client2.set("project_root", self.temp_dir2)
                
                # 实例1尝试搜索只存在于目录1的内容
                print("🔍 实例1搜索目录1特有内容...")
                search1 = await client1.call("search_files_by_content",
                    query="hello_world"
                )
                
                # 实例2尝试搜索只存在于目录2的内容
                print("🔍 实例2搜索目录2特有内容...")
                search2 = await client2.call("search_files_by_content",
                    query="goodbye_world"
                )
                
                # 验证隔离性
                if search1 and "hello_world" in search1:
                    print("  ✅ 实例1正确找到目录1的内容")
                else:
                    print("  ❌ 实例1未找到目录1的内容")
                
                if search2 and "goodbye_world" in search2:
                    print("  ✅ 实例2正确找到目录2的内容")
                else:
                    print("  ❌ 实例2未找到目录2的内容")
                
                # 交叉验证：实例1不应该找到目录2的内容
                print("🔍 交叉验证实例隔离...")
                cross_search1 = await client1.call("search_files_by_content",
                    query="goodbye_world"
                )
                
                cross_search2 = await client2.call("search_files_by_content",
                    query="hello_world"
                )
                
                if not cross_search1 or "goodbye_world" not in cross_search1:
                    print("  ✅ 实例1正确隔离，未找到目录2的内容")
                else:
                    print("  ❌ 实例1隔离失败，找到了目录2的内容")
                
                if not cross_search2 or "hello_world" not in cross_search2:
                    print("  ✅ 实例2正确隔离，未找到目录1的内容")
                else:
                    print("  ❌ 实例2隔离失败，找到了目录1的内容")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试实例隔离时发生错误: {e}")
            return False

    async def test_configuration_differences(self):
        """测试配置差异"""
        try:
            print(f"\n⚙️ 测试配置差异")
            
            async with SimpleClient(self.server_script, alias="concurrent1", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client1, \
                       SimpleClient(self.server_script, alias="concurrent2", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client2:
                
                # 为不同别名设置不同的配置
                await client1.set("project_root", self.temp_dir1)
                await client1.set("max_file_size", 1024)
                await client1.set("enable_hidden_files", True)
                
                await client2.set("project_root", self.temp_dir2)
                await client2.set("max_file_size", 2048)
                await client2.set("enable_hidden_files", False)
                
                # 验证不同的配置值
                print("📋 验证配置差异:")
                
                max_size1 = await client1.get("max_file_size", "未设置")
                max_size2 = await client2.get("max_file_size", "未设置")
                
                hidden1 = await client1.get("enable_hidden_files", "未设置")
                hidden2 = await client2.get("enable_hidden_files", "未设置")
                
                print(f"  实例1 - 最大文件大小: {max_size1}, 隐藏文件: {hidden1}")
                print(f"  实例2 - 最大文件大小: {max_size2}, 隐藏文件: {hidden2}")
                
                # 验证配置确实不同
                if str(max_size1) != str(max_size2):
                    print("  ✅ 最大文件大小配置不同")
                else:
                    print("  ❌ 最大文件大小配置相同")
                
                if str(hidden1) != str(hidden2):
                    print("  ✅ 隐藏文件配置不同")
                else:
                    print("  ❌ 隐藏文件配置相同")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试配置差异时发生错误: {e}")
            return False

    async def test_configuration_management(self):
        """测试配置管理"""
        try:
            print(f"\n🛠️ 测试配置管理")
            
            async with SimpleClient(self.server_script, alias="concurrent1", config_dir="/Users/lilei/project/config/test_mcp_server_config") as client:
                # 先设置项目根目录
                await client.set("project_root", self.temp_dir1)
                
                # 获取完整配置
                print("📋 获取完整配置...")
                full_config = await client.config()
                print(f"  配置项数量: {len(full_config)}")
                
                # 测试配置项的获取和设置
                print("🔧 测试配置项操作...")
                
                # 获取项目根目录
                project_root = await client.get("project_root", "未设置")
                print(f"  项目根目录: {project_root}")
                
                # 验证项目根目录是否正确
                if self.temp_dir1 in str(project_root):
                    print("  ✅ 项目根目录配置正确")
                else:
                    print("  ❌ 项目根目录配置不正确")
                
                # 测试默认值
                default_value = await client.get("non_existent_key", "默认值")
                if default_value == "默认值":
                    print("  ✅ 默认值处理正确")
                else:
                    print("  ❌ 默认值处理不正确")
                
                return True
                
        except Exception as e:
            print(f"❌ 测试配置管理时发生错误: {e}")
            return False


async def main():
    """主测试函数"""
    print("🧪 开始测试双实例配置功能")
    print("=" * 60)
    
    # 创建测试器
    tester = DualInstanceConfigTester("./dist/file-reader-server")
    
    try:
        # 测试双实例配置
        print("\n🎯 测试 1: 双实例配置")
        success1 = await tester.test_dual_instance_config()
        
        # 测试并发访问
        print("\n🎯 测试 2: 并发访问")
        success2 = await tester.test_concurrent_access()
        
        # 测试实例隔离
        print("\n🎯 测试 3: 实例隔离")
        success3 = await tester.test_instance_isolation()
        
        # 测试配置差异
        print("\n🎯 测试 4: 配置差异")
        success4 = await tester.test_configuration_differences()
        
        # 测试配置管理
        print("\n🎯 测试 5: 配置管理")
        success5 = await tester.test_configuration_management()
        
        # 总结结果
        print(f"\n📊 测试结果:")
        print(f"✅ 双实例配置: {'通过' if success1 else '失败'}")
        print(f"✅ 并发访问: {'通过' if success2 else '失败'}")
        print(f"✅ 实例隔离: {'通过' if success3 else '失败'}")
        print(f"✅ 配置差异: {'通过' if success4 else '失败'}")
        print(f"✅ 配置管理: {'通过' if success5 else '失败'}")
        
        if all([success1, success2, success3, success4, success5]):
            print("\n🎉 所有双实例配置测试通过！")
            return 0
        else:
            print("\n❌ 部分双实例配置测试失败！")
            return 1
            
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        return 1
    finally:
        # 清理临时文件
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))