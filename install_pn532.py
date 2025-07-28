#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PN532安装和测试脚本
自动安装依赖并测试PN532模块连接
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔧 {description}")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 成功")
            if result.stdout:
                print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 失败")
            if result.stderr:
                print(f"错误: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def install_requirements():
    """安装Python依赖"""
    print("📦 安装Python依赖...")
    
    # 基础依赖
    dependencies = [
        'pyserial>=3.5',
        'pyserial-asyncio',
    ]
    
    for dep in dependencies:
        if not run_command([sys.executable, '-m', 'pip', 'install', dep], 
                          f"安装 {dep}"):
            return False
    
    return True

def check_serial_ports():
    """检查可用串口"""
    print("\n🔍 检查可用串口...")
    
    try:
        import serial.tools.list_ports
        
        ports = serial.tools.list_ports.comports()
        if not ports:
            print("❌ 未找到串口设备")
            return False
        
        print(f"✅ 找到 {len(ports)} 个串口:")
        for port in ports:
            print(f"  {port.device}: {port.description}")
            if port.hwid:
                print(f"    硬件ID: {port.hwid}")
        
        return True
        
    except ImportError:
        print("❌ pyserial库未安装")
        return False
    except Exception as e:
        print(f"❌ 检查串口失败: {e}")
        return False

def test_pn532_basic():
    """基础PN532测试"""
    print("\n🧪 基础PN532连接测试...")
    
    try:
        from pn532_controller import PN532Controller
        
        controller = PN532Controller()
        print("✅ PN532控制器模块加载成功")
        
        # 尝试自动检测
        port = controller.find_pn532_port()
        if port:
            print(f"✅ 检测到可能的PN532模块: {port}")
            
            # 尝试连接
            if controller.connect():
                print("✅ PN532模块连接成功!")
                
                # 测试标签检测
                print("📡 测试标签检测 (5秒超时)...")
                import time
                
                start_time = time.time()
                while time.time() - start_time < 5:
                    tag_info = controller.detect_tag()
                    if tag_info:
                        print(f"✅ 检测到标签: {tag_info['uid_hex']}")
                        break
                    time.sleep(0.1)
                else:
                    print("ℹ️  未检测到标签 (可以稍后放置标签测试)")
                
                controller.stop_monitoring()
                return True
            else:
                print("❌ PN532模块连接失败")
                return False
        else:
            print("❌ 未找到PN532模块")
            return False
            
    except ImportError as e:
        print(f"❌ 导入PN532控制器失败: {e}")
        return False
    except Exception as e:
        print(f"❌ PN532测试失败: {e}")
        return False

def create_startup_scripts():
    """创建启动脚本"""
    print("\n📝 创建启动脚本...")
    
    # PN532启动脚本
    pn532_script = """#!/bin/bash
# PN532分页导航启动脚本

cd "$(dirname "$0")"

echo "=== PN532分页导航系统 ==="
echo "正在启动..."

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "❌ 找不到虚拟环境"
    exit 1
fi

# 启动PN532控制器
python3 pn532_controller.py

echo "PN532控制器已停止"
"""
    
    try:
        with open('start_pn532.sh', 'w', encoding='utf-8') as f:
            f.write(pn532_script)
        
        # 设置执行权限
        os.chmod('start_pn532.sh', 0o755)
        print("✅ 创建 start_pn532.sh")
        
        # Windows批处理文件
        windows_script = """@echo off
REM PN532分页导航启动脚本

cd /d "%~dp0"

echo === PN532分页导航系统 ===
echo 正在启动...

REM 激活虚拟环境
if exist "venv\\Scripts\\activate.bat" (
    call venv\\Scripts\\activate.bat
    echo ✅ 虚拟环境已激活
) else (
    echo ❌ 找不到虚拟环境
    pause
    exit /b 1
)

REM 启动PN532控制器
python pn532_controller.py

echo PN532控制器已停止
pause
"""
        
        with open('start_pn532.bat', 'w', encoding='utf-8') as f:
            f.write(windows_script)
        
        print("✅ 创建 start_pn532.bat")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建启动脚本失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 PN532安装和配置工具")
    print("=" * 40)
    
    # 检查Python版本
    if sys.version_info < (3, 6):
        print("❌ 需要Python 3.6或更高版本")
        return
    
    print(f"✅ Python版本: {sys.version}")
    
    # 安装依赖
    if not install_requirements():
        print("\n❌ 依赖安装失败")
        return
    
    # 检查串口
    if not check_serial_ports():
        print("\n⚠️  串口检查失败，请确保PN532模块已连接")
    
    # 测试PN532
    if not test_pn532_basic():
        print("\n⚠️  PN532测试失败，请检查连接")
    else:
        print("\n🎉 PN532模块工作正常!")
    
    # 创建启动脚本
    if create_startup_scripts():
        print("\n✅ 启动脚本创建成功")
    
    # 显示使用指南
    print("\n" + "=" * 40)
    print("📋 使用指南:")
    print("1. 确保PN532模块已通过USB连接到电脑")
    print("2. 运行分页导航控制器:")
    print("   python3 pn532_controller.py")
    print("   或者:")
    print("   ./start_pn532.sh (Linux/macOS)")
    print("   start_pn532.bat (Windows)")
    print("\n3. 写入标签:")
    print("   python3 pn532_tag_writer.py --batch 10")
    print("\n4. 启动统一接收器:")
    print("   python3 unified_receiver.py")
    print("\n💡 提示:")
    print("- 使用 'learn' 命令进入学习模式")
    print("- 使用 'mappings' 查看页面映射")
    print("- 将页面左下角靠近PN532模块即可跳转")

if __name__ == "__main__":
    main() 