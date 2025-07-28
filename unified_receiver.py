#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一命令接收器
同时接收二维码扫描器和NFC控制器的命令，统一处理翻页等操作
"""

import socket
import json
import threading
import time
from datetime import datetime

class UnifiedReceiver:
    def __init__(self, qr_port=8888, nfc_port=8889, page_nav_port=8890):
        """
        初始化统一接收器
        
        Args:
            qr_port (int): 二维码扫描器UDP端口
            nfc_port (int): NFC控制器UDP端口
            page_nav_port (int): 分页导航控制器UDP端口
        """
        self.qr_port = qr_port
        self.nfc_port = nfc_port
        self.page_nav_port = page_nav_port
        self.is_running = False
        
        # 创建套接字
        self.qr_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.nfc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.page_nav_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 绑定端口
        try:
            self.qr_socket.bind(('127.0.0.1', qr_port))
            print(f"✅ 二维码接收器绑定到端口 {qr_port}")
        except Exception as e:
            print(f"❌ 二维码端口绑定失败: {e}")
        
        try:
            self.nfc_socket.bind(('127.0.0.1', nfc_port))
            print(f"✅ NFC接收器绑定到端口 {nfc_port}")
        except Exception as e:
            print(f"❌ NFC端口绑定失败: {e}")
        
        try:
            self.page_nav_socket.bind(('127.0.0.1', page_nav_port))
            print(f"✅ 分页导航接收器绑定到端口 {page_nav_port}")
        except Exception as e:
            print(f"❌ 分页导航端口绑定失败: {e}")
        
        # 统计信息
        self.stats = {
            'qr_messages': 0,
            'nfc_messages': 0,
            'page_nav_messages': 0,
            'total_commands': 0,
            'start_time': time.time()
        }
        
        # 命令历史
        self.command_history = []
        self.max_history = 100
        
        print(f"统一接收器已初始化")
        print(f"监听端口: QR={qr_port}, NFC={nfc_port}, 分页导航={page_nav_port}")
    
    def process_qr_message(self, data, addr):
        """
        处理二维码消息
        
        Args:
            data (bytes): 接收到的数据
            addr (tuple): 发送方地址
        """
        try:
            message = json.loads(data.decode('utf-8'))
            self.stats['qr_messages'] += 1
            
            print(f"📱 QR码: {message.get('qr_content', 'Unknown')}")
            print(f"   时间: {message.get('timestamp', 'Unknown')}")
            print(f"   来源: {addr}")
            
            # 解析二维码内容为命令
            qr_content = message.get('qr_content', '')
            command = self.parse_qr_command(qr_content)
            
            if command:
                self.execute_command(command, 'qr_scanner', message)
            else:
                print(f"   📄 内容: {qr_content}")
            
        except json.JSONDecodeError:
            print(f"❌ 无效的QR JSON数据: {data}")
        except Exception as e:
            print(f"❌ 处理QR消息失败: {e}")
    
    def process_nfc_message(self, data, addr):
        """
        处理NFC消息
        
        Args:
            data (bytes): 接收到的数据
            addr (tuple): 发送方地址
        """
        try:
            message = json.loads(data.decode('utf-8'))
            self.stats['nfc_messages'] += 1
            
            command = message.get('command', 'unknown')
            tag_data = message.get('tag_data', {})
            
            print(f"🏷️  NFC: {command}")
            print(f"   时间: {message.get('timestamp', 'Unknown')}")
            print(f"   标签: {tag_data.get('tag_id', 'Unknown')}")
            print(f"   来源: {addr}")
            
            self.execute_command(command, 'nfc_controller', message)
            
        except json.JSONDecodeError:
            print(f"❌ 无效的NFC JSON数据: {data}")
        except Exception as e:
            print(f"❌ 处理NFC消息失败: {e}")
    
    def process_page_nav_message(self, data, addr):
        """
        处理分页导航消息
        
        Args:
            data (bytes): 接收到的数据
            addr (tuple): 发送方地址
        """
        try:
            message = json.loads(data.decode('utf-8'))
            self.stats['page_nav_messages'] += 1
            
            command = message.get('command', 'unknown')
            page_number = message.get('page_number', 0)
            total_pages = message.get('total_pages', 0)
            
            print(f"📑 分页导航: {command}")
            print(f"   页面: {page_number}/{total_pages}")
            print(f"   时间: {message.get('timestamp', 'Unknown')}")
            print(f"   来源: {addr}")
            
            if command == 'goto_page':
                self.execute_page_navigation(page_number, total_pages, message)
            else:
                self.execute_command(command, 'page_navigation', message)
            
        except json.JSONDecodeError:
            print(f"❌ 无效的分页导航JSON数据: {data}")
        except Exception as e:
            print(f"❌ 处理分页导航消息失败: {e}")
    
    def parse_qr_command(self, qr_content):
        """
        解析二维码内容为命令
        
        Args:
            qr_content (str): 二维码内容
            
        Returns:
            str: 命令类型，如果不是命令则返回None
        """
        content = qr_content.lower().strip()
        
        # 翻页命令
        if content in ['next', 'next_page', '下一页', '下页', '>']:
            return 'next_page'
        elif content in ['prev', 'prev_page', 'previous', '上一页', '上页', '<']:
            return 'prev_page'
        elif content in ['first', 'first_page', '首页', '第一页', '1']:
            return 'first_page'
        elif content in ['last', 'last_page', '末页', '最后一页', 'end']:
            return 'last_page'
        
        # 其他命令
        elif content in ['bookmark', '书签', 'mark']:
            return 'bookmark'
        elif content in ['menu', '菜单', 'index']:
            return 'menu'
        elif content in ['exit', '退出', 'quit', 'close']:
            return 'exit'
        elif content in ['debug', '调试', 'debug_toggle']:
            return 'debug_toggle'
        
        # URL形式的命令
        elif 'page=next' in content:
            return 'next_page'
        elif 'page=prev' in content:
            return 'prev_page'
        elif 'action=' in content:
            # 提取action参数
            try:
                action = content.split('action=')[1].split('&')[0]
                return action
            except:
                pass
        
        return None
    
    def execute_command(self, command, source, original_message):
        """
        执行命令
        
        Args:
            command (str): 命令类型
            source (str): 命令来源
            original_message (dict): 原始消息
        """
        self.stats['total_commands'] += 1
        
        # 记录命令历史
        command_record = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'source': source,
            'message': original_message
        }
        self.command_history.append(command_record)
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
        
        # 命令映射
        command_descriptions = {
            'next_page': '📖 翻到下一页',
            'prev_page': '📖 翻到上一页', 
            'first_page': '📖 跳转到首页',
            'last_page': '📖 跳转到末页',
            'bookmark': '🔖 添加书签',
            'menu': '📋 打开菜单',
            'exit': '🚪 退出程序',
            'debug_toggle': '🔧 切换调试模式'
        }
        
        description = command_descriptions.get(command, f'执行命令: {command}')
        print(f"⚡ {description} (来源: {source})")
        
        # 这里可以添加实际的命令执行逻辑
        # 例如：调用其他程序的API、发送键盘事件等
        self.simulate_page_action(command)
    
    def execute_page_navigation(self, page_number, total_pages, original_message):
        """
        执行页面导航
        
        Args:
            page_number (int): 目标页码
            total_pages (int): 总页数
            original_message (dict): 原始消息
        """
        self.stats['total_commands'] += 1
        
        # 记录命令历史
        command_record = {
            'timestamp': datetime.now().isoformat(),
            'command': 'goto_page',
            'page_number': page_number,
            'total_pages': total_pages,
            'source': 'page_navigation',
            'message': original_message
        }
        self.command_history.append(command_record)
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
        
        print(f"⚡ 📖 跳转到第 {page_number} 页 (共{total_pages}页)")
        
        # 这里可以添加实际的页面跳转逻辑
        self.simulate_page_navigation(page_number, total_pages)
    
    def simulate_page_action(self, command):
        """
        模拟翻页操作（示例实现）
        
        Args:
            command (str): 命令类型
        """
        # 这里可以集成到实际的阅读器应用
        # 例如：使用键盘模拟、调用API等
        
        if command == 'next_page':
            print("   → 模拟按下右箭头键或Page Down")
            # 示例：使用pynput模拟键盘
            # from pynput.keyboard import Key, Controller
            # keyboard = Controller()
            # keyboard.press(Key.right)
            # keyboard.release(Key.right)
            
        elif command == 'prev_page':
            print("   ← 模拟按下左箭头键或Page Up")
            
        elif command == 'first_page':
            print("   🏠 模拟按下Home键")
            
        elif command == 'last_page':
            print("   🏁 模拟按下End键")
            
        elif command == 'bookmark':
            print("   🔖 添加当前页面为书签")
            
        elif command == 'menu':
            print("   📋 打开应用菜单")
            
        elif command == 'exit':
            print("   🚪 退出应用")
            
        elif command == 'debug_toggle':
            print("   🔧 切换调试模式")
    
    def simulate_page_navigation(self, page_number, total_pages):
        """
        模拟页面导航操作
        
        Args:
            page_number (int): 目标页码
            total_pages (int): 总页数
        """
        # 这里可以集成到实际的阅读器应用
        print(f"   🎯 导航到第 {page_number} 页")
        
        # 示例：使用键盘快捷键 Ctrl+G 打开"跳转到页面"对话框
        # from pynput.keyboard import Key, Controller
        # keyboard = Controller()
        # keyboard.press(Key.ctrl)
        # keyboard.press('g')
        # keyboard.release('g')
        # keyboard.release(Key.ctrl)
        
        # 然后输入页码
        # for digit in str(page_number):
        #     keyboard.press(digit)
        #     keyboard.release(digit)
        # keyboard.press(Key.enter)
        # keyboard.release(Key.enter)
    
    def listen_qr(self):
        """
        监听二维码消息（线程函数）
        """
        self.qr_socket.settimeout(1.0)  # 设置超时避免阻塞
        
        while self.is_running:
            try:
                data, addr = self.qr_socket.recvfrom(1024)
                self.process_qr_message(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"QR监听错误: {e}")
    
    def listen_nfc(self):
        """
        监听NFC消息（线程函数）
        """
        self.nfc_socket.settimeout(1.0)  # 设置超时避免阻塞
        
        while self.is_running:
            try:
                data, addr = self.nfc_socket.recvfrom(1024)
                self.process_nfc_message(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"NFC监听错误: {e}")
    
    def listen_page_nav(self):
        """
        监听分页导航消息（线程函数）
        """
        self.page_nav_socket.settimeout(1.0)
        
        while self.is_running:
            try:
                data, addr = self.page_nav_socket.recvfrom(1024)
                self.process_page_nav_message(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"分页导航监听错误: {e}")
    
    def show_stats(self):
        """
        显示统计信息
        """
        runtime = time.time() - self.stats['start_time']
        print(f"\n=== 统计信息 ===")
        print(f"运行时间: {runtime:.1f} 秒")
        print(f"QR消息: {self.stats['qr_messages']}")
        print(f"NFC消息: {self.stats['nfc_messages']}")
        print(f"分页导航: {self.stats['page_nav_messages']}")
        print(f"总命令: {self.stats['total_commands']}")
        print(f"================\n")
    
    def show_history(self, count=10):
        """
        显示命令历史
        
        Args:
            count (int): 显示的历史条数
        """
        print(f"\n=== 最近 {count} 条命令历史 ===")
        recent_history = self.command_history[-count:]
        
        for record in recent_history:
            timestamp = record['timestamp']
            command = record['command']
            source = record['source']
            print(f"{timestamp} | {command:12} | {source}")
        print("=========================\n")
    
    def start(self):
        """
        开始监听
        """
        self.is_running = True
        
        # 启动监听线程
        self.qr_thread = threading.Thread(target=self.listen_qr)
        self.nfc_thread = threading.Thread(target=self.listen_nfc)
        self.page_nav_thread = threading.Thread(target=self.listen_page_nav)
        
        self.qr_thread.daemon = True
        self.nfc_thread.daemon = True
        self.page_nav_thread.daemon = True
        
        self.qr_thread.start()
        self.nfc_thread.start()
        self.page_nav_thread.start()
        
        print("🎯 统一接收器已启动")
        print("等待二维码、NFC和分页导航命令...")
        print("按 Ctrl+C 停止接收")
        
        try:
            while self.is_running:
                time.sleep(1)
                
                # 每30秒显示一次统计信息
                if int(time.time()) % 30 == 0:
                    self.show_stats()
                    
        except KeyboardInterrupt:
            print("\n⏹️  接收器已停止")
        finally:
            self.stop()
    
    def stop(self):
        """
        停止监听
        """
        self.is_running = False
        
        # 关闭套接字
        try:
            self.qr_socket.close()
            self.nfc_socket.close()
            self.page_nav_socket.close()
        except:
            pass
        
        print("统一接收器已停止")
    
    def cleanup(self):
        """
        清理资源
        """
        self.stop()
        print("统一接收器资源已清理")

def main():
    """
    主函数
    """
    import sys
    
    print("=== 统一命令接收器 ===")
    print("同时接收二维码和NFC翻页命令")
    
    # 检查命令行参数
    qr_port = 8888
    nfc_port = 8889
    page_nav_port = 8890
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 unified_receiver.py [QR端口] [NFC端口] [分页导航端口]")
            print("\n参数:")
            print("  QR端口: 二维码扫描器UDP端口 (默认: 8888)")
            print("  NFC端口: NFC控制器UDP端口 (默认: 8889)")
            print("  分页导航端口: 分页导航控制器UDP端口 (默认: 8890)")
            print("\n示例:")
            print("  python3 unified_receiver.py              # 使用默认端口")
            print("  python3 unified_receiver.py 8888 8889 8890    # 指定端口")
            print("\n支持的命令:")
            print("  翻页: next_page, prev_page, first_page, last_page")
            print("  其他: bookmark, menu, exit, debug_toggle")
            print("\n二维码命令格式:")
            print("  - 直接文本: '下一页', '上一页', '首页', '末页'")
            print("  - 英文: 'next', 'prev', 'first', 'last'")
            print("  - URL参数: 'http://localhost/?page=next'")
            return
        else:
            try:
                if len(sys.argv) >= 2:
                    qr_port = int(sys.argv[1])
                if len(sys.argv) >= 3:
                    nfc_port = int(sys.argv[2])
                if len(sys.argv) >= 4:
                    page_nav_port = int(sys.argv[3])
            except ValueError:
                print("无效的端口号")
                return
    
    # 创建接收器
    receiver = UnifiedReceiver(qr_port, nfc_port, page_nav_port)
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        receiver.cleanup()

if __name__ == "__main__":
    main() 