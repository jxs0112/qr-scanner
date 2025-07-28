#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFC翻页控制器
使用NFC传感器实现翻页功能，支持多种NFC标签和手机NFC
"""

import time
import threading
import socket
import json
from datetime import datetime

try:
    import nfc
    from nfc.clf import RemoteTarget
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    print("警告: python-nfc库未安装，NFC功能不可用")
    print("安装命令: pip install nfcpy")

class NFCPageController:
    def __init__(self, udp_host='127.0.0.1', udp_port=8889, device_path=None):
        """
        初始化NFC翻页控制器
        
        Args:
            udp_host (str): UDP目标主机地址
            udp_port (int): UDP目标端口
            device_path (str): NFC设备路径，None表示自动检测
        """
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.device_path = device_path
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # NFC设备和状态
        self.clf = None
        self.is_running = False
        self.last_tag_id = None
        self.last_tag_time = 0
        self.tag_cooldown = 1.0  # 防止重复触发的冷却时间
        
        # 预定义的NFC标签功能
        self.nfc_commands = {
            'next_page': '下一页',
            'prev_page': '上一页',
            'first_page': '首页',
            'last_page': '末页',
            'bookmark': '书签',
            'menu': '菜单',
            'exit': '退出',
            'debug_toggle': '调试切换'
        }
        
        # 标签ID到命令的映射（可配置）
        self.tag_mappings = {}
        
        print(f"NFC翻页控制器初始化")
        print(f"UDP目标: {udp_host}:{udp_port}")
        print(f"NFC库可用: {'是' if NFC_AVAILABLE else '否'}")
    
    def initialize_nfc(self):
        """
        初始化NFC设备
        """
        if not NFC_AVAILABLE:
            print("❌ NFC库不可用，无法初始化NFC设备")
            return False
        
        try:
            # 尝试连接NFC设备
            self.clf = nfc.ContactlessFrontend(self.device_path)
            if self.clf:
                print(f"✅ NFC设备已连接: {self.clf}")
                return True
            else:
                print("❌ 无法连接NFC设备")
                return False
        except Exception as e:
            print(f"❌ NFC设备初始化失败: {e}")
            return False
    
    def send_page_command(self, command, tag_data=None):
        """
        发送翻页命令
        
        Args:
            command (str): 命令类型
            tag_data (dict): 标签数据
        """
        try:
            packet_data = {
                'timestamp': datetime.now().isoformat(),
                'command': command,
                'source': 'nfc_controller',
                'tag_data': tag_data
            }
            
            json_data = json.dumps(packet_data, ensure_ascii=False)
            encoded_data = json_data.encode('utf-8')
            
            self.socket.sendto(encoded_data, (self.udp_host, self.udp_port))
            print(f"✓ NFC命令已发送: {command}")
            
        except Exception as e:
            print(f"✗ NFC命令发送失败: {e}")
    
    def process_nfc_tag(self, tag):
        """
        处理NFC标签
        
        Args:
            tag: NFC标签对象
        """
        try:
            # 获取标签信息
            tag_id = tag.identifier.hex() if tag.identifier else "unknown"
            tag_type = str(tag.type)
            
            current_time = time.time()
            
            # 防止重复触发
            if (tag_id == self.last_tag_id and 
                current_time - self.last_tag_time < self.tag_cooldown):
                return
            
            self.last_tag_id = tag_id
            self.last_tag_time = current_time
            
            print(f"📱 检测到NFC标签: {tag_id} (类型: {tag_type})")
            
            # 检查是否有预设映射
            if tag_id in self.tag_mappings:
                command = self.tag_mappings[tag_id]
                print(f"🏷️  使用预设命令: {command}")
                self.send_page_command(command, {
                    'tag_id': tag_id,
                    'tag_type': tag_type
                })
                return
            
            # 尝试读取标签内容
            tag_data = self.read_tag_content(tag)
            
            # 根据标签内容判断命令
            command = self.parse_tag_command(tag_data, tag_id)
            
            if command:
                self.send_page_command(command, {
                    'tag_id': tag_id,
                    'tag_type': tag_type,
                    'content': tag_data
                })
            else:
                # 默认行为：下一页
                self.send_page_command('next_page', {
                    'tag_id': tag_id,
                    'tag_type': tag_type,
                    'content': tag_data
                })
                
        except Exception as e:
            print(f"❌ 处理NFC标签失败: {e}")
    
    def read_tag_content(self, tag):
        """
        读取NFC标签内容
        
        Args:
            tag: NFC标签对象
            
        Returns:
            dict: 标签内容
        """
        content = {}
        
        try:
            # 尝试读取NDEF记录
            if tag.ndef and tag.ndef.records:
                content['ndef_records'] = []
                for record in tag.ndef.records:
                    record_data = {
                        'type': record.type,
                        'name': record.name,
                        'data': record.data
                    }
                    
                    # 如果是文本记录，尝试解码
                    if record.type == 'urn:nfc:wkt:T':
                        try:
                            text = record.text
                            record_data['text'] = text
                            content['text'] = text
                        except:
                            pass
                    
                    # 如果是URI记录
                    elif record.type == 'urn:nfc:wkt:U':
                        try:
                            uri = record.uri
                            record_data['uri'] = uri
                            content['uri'] = uri
                        except:
                            pass
                    
                    content['ndef_records'].append(record_data)
            
        except Exception as e:
            print(f"读取标签内容时出错: {e}")
        
        return content
    
    def parse_tag_command(self, tag_data, tag_id):
        """
        根据标签内容解析命令
        
        Args:
            tag_data (dict): 标签数据
            tag_id (str): 标签ID
            
        Returns:
            str: 命令类型
        """
        # 检查文本内容
        if 'text' in tag_data:
            text = tag_data['text'].lower()
            if 'next' in text or '下一页' in text or '下页' in text:
                return 'next_page'
            elif 'prev' in text or '上一页' in text or '上页' in text:
                return 'prev_page'
            elif 'first' in text or '首页' in text:
                return 'first_page'
            elif 'last' in text or '末页' in text or '最后' in text:
                return 'last_page'
            elif 'bookmark' in text or '书签' in text:
                return 'bookmark'
            elif 'menu' in text or '菜单' in text:
                return 'menu'
            elif 'exit' in text or '退出' in text:
                return 'exit'
            elif 'debug' in text or '调试' in text:
                return 'debug_toggle'
        
        # 检查URI内容
        if 'uri' in tag_data:
            uri = tag_data['uri'].lower()
            if 'page=next' in uri:
                return 'next_page'
            elif 'page=prev' in uri:
                return 'prev_page'
            # 可以添加更多URI解析规则
        
        # 根据标签ID的模式匹配
        if tag_id:
            # 奇数ID = 下一页，偶数ID = 上一页（示例规则）
            try:
                id_int = int(tag_id[-2:], 16)  # 取最后两位十六进制
                return 'next_page' if id_int % 2 == 1 else 'prev_page'
            except:
                pass
        
        return None
    
    def add_tag_mapping(self, tag_id, command):
        """
        添加标签ID到命令的映射
        
        Args:
            tag_id (str): 标签ID
            command (str): 命令类型
        """
        self.tag_mappings[tag_id] = command
        print(f"✓ 已添加标签映射: {tag_id} -> {command}")
    
    def remove_tag_mapping(self, tag_id):
        """
        移除标签映射
        
        Args:
            tag_id (str): 标签ID
        """
        if tag_id in self.tag_mappings:
            del self.tag_mappings[tag_id]
            print(f"✓ 已移除标签映射: {tag_id}")
    
    def list_tag_mappings(self):
        """
        列出所有标签映射
        """
        print("\n=== NFC标签映射 ===")
        if self.tag_mappings:
            for tag_id, command in self.tag_mappings.items():
                command_desc = self.nfc_commands.get(command, command)
                print(f"  {tag_id} -> {command} ({command_desc})")
        else:
            print("  无预设映射")
        print("==================\n")
    
    def start_nfc_monitoring(self):
        """
        开始NFC监听（阻塞模式）
        """
        if not self.initialize_nfc():
            return False
        
        self.is_running = True
        print("🎯 开始NFC监听...")
        print("请将NFC标签或支持NFC的设备靠近传感器")
        print("按 Ctrl+C 停止监听")
        
        try:
            while self.is_running:
                # 等待标签接近
                tag = self.clf.connect(rdwr={
                    'on-connect': self.process_nfc_tag
                })
                
                if not tag:
                    time.sleep(0.1)  # 短暂等待避免CPU占用过高
                    
        except KeyboardInterrupt:
            print("\n⏹️  NFC监听已停止")
        except Exception as e:
            print(f"❌ NFC监听错误: {e}")
        finally:
            self.stop_nfc_monitoring()
    
    def start_nfc_monitoring_async(self):
        """
        异步开始NFC监听
        """
        self.nfc_thread = threading.Thread(target=self.start_nfc_monitoring)
        self.nfc_thread.daemon = True
        self.nfc_thread.start()
        return True
    
    def stop_nfc_monitoring(self):
        """
        停止NFC监听
        """
        self.is_running = False
        if self.clf:
            try:
                self.clf.close()
            except:
                pass
            self.clf = None
        print("NFC监听已停止")
    
    def cleanup(self):
        """
        清理资源
        """
        self.stop_nfc_monitoring()
        self.socket.close()
        print("NFC控制器资源已清理")

def main():
    """
    主函数 - NFC翻页控制器独立运行
    """
    import sys
    
    print("=== NFC翻页控制器 ===")
    print("使用NFC传感器实现翻页功能")
    
    if not NFC_AVAILABLE:
        print("\n❌ 错误: 缺少NFC库")
        print("请安装: pip install nfcpy")
        print("或者: pip install pyscard")
        return
    
    # 检查命令行参数
    udp_port = 8889  # 默认端口（与二维码扫描器不同）
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 nfc_page_controller.py [UDP端口]")
            print("\n参数:")
            print("  UDP端口: 可选，默认为 8889")
            print("\n示例:")
            print("  python3 nfc_page_controller.py          # 使用默认端口")
            print("  python3 nfc_page_controller.py 9000     # 使用端口9000")
            print("\nNFC标签配置:")
            print("  - 将文本写入标签: '下一页', '上一页', '首页', '末页'等")
            print("  - 或写入URI: 'http://localhost/?page=next'")
            print("  - 空白标签默认为'下一页'功能")
            return
        else:
            try:
                udp_port = int(sys.argv[1])
            except ValueError:
                print(f"无效的端口号: {sys.argv[1]}")
                return
    
    # 创建NFC控制器
    controller = NFCPageController(udp_port=udp_port)
    
    # 添加一些示例映射（可选）
    print("\n📋 可用命令:")
    for cmd, desc in controller.nfc_commands.items():
        print(f"  {cmd}: {desc}")
    
    try:
        # 开始NFC监听
        controller.start_nfc_monitoring()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        controller.cleanup()

if __name__ == "__main__":
    main() 