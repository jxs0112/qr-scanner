#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PN532 NFC模块控制器
专门用于PN532模块的NFC标签读写和分页导航
支持USB转串口连接方式
"""

import time
import serial
import serial.tools.list_ports
import threading
import socket
import json
from datetime import datetime

# PN532 命令常量
PN532_PREAMBLE = 0x00
PN532_STARTCODE1 = 0x00
PN532_STARTCODE2 = 0xFF
PN532_POSTAMBLE = 0x00

# PN532 命令
PN532_COMMAND_GETFIRMWAREVERSION = 0x02
PN532_COMMAND_SAMCONFIGURATION = 0x14
PN532_COMMAND_INLISTPASSIVETARGET = 0x4A
PN532_COMMAND_INDATAEXCHANGE = 0x40

# MIFARE 命令
MIFARE_CMD_READ = 0x30
MIFARE_CMD_WRITE = 0xA0

class PN532Controller:
    def __init__(self, port=None, baudrate=115200, udp_port=8890, total_pages=10):
        """
        初始化PN532控制器
        
        Args:
            port (str): 串口名称，如果为None则自动检测
            baudrate (int): 波特率
            udp_port (int): UDP发送端口
            total_pages (int): 总页数
        """
        self.port = port
        self.baudrate = baudrate
        self.udp_port = udp_port
        self.total_pages = total_pages
        self.serial_conn = None
        self.is_running = False
        
        # UDP套接字
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 页面映射
        self.page_mappings = {}
        self.reverse_mappings = {}
        
        # 防重复触发
        self.last_tag_uid = None
        self.last_tag_time = 0
        self.tag_cooldown = 0.5
        
        # 学习模式
        self.learning_mode = False
        self.current_learning_page = 1
        
        print(f"PN532控制器已初始化")
        print(f"目标端口: {udp_port}")
        print(f"总页数: {total_pages}")
    
    def find_pn532_port(self):
        """
        自动检测PN532模块端口
        
        Returns:
            str: 串口名称，如果未找到返回None
        """
        print("🔍 正在搜索PN532模块...")
        
        # 常见的USB转串口芯片
        usb_serial_chips = [
            'CH340', 'CH341', 'FT232', 'CP210', 'PL2303'
        ]
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            port_name = port.device
            description = port.description.upper()
            
            print(f"  检测到串口: {port_name} - {port.description}")
            
            # 检查是否为USB转串口设备
            for chip in usb_serial_chips:
                if chip in description:
                    print(f"  ✅ 可能的PN532端口: {port_name}")
                    # 尝试连接测试
                    if self.test_pn532_connection(port_name):
                        print(f"  🎉 确认PN532模块: {port_name}")
                        return port_name
        
        print("  ❌ 未找到PN532模块")
        return None
    
    def test_pn532_connection(self, port_name):
        """
        测试PN532连接
        
        Args:
            port_name (str): 串口名称
            
        Returns:
            bool: 连接成功返回True
        """
        try:
            with serial.Serial(port_name, self.baudrate, timeout=2) as test_conn:
                time.sleep(0.5)  # 等待初始化
                
                # 发送获取固件版本命令
                cmd = self.build_command([PN532_COMMAND_GETFIRMWAREVERSION])
                test_conn.write(cmd)
                
                # 读取响应
                response = test_conn.read(20)
                if len(response) >= 6:
                    return True
                    
        except Exception as e:
            pass
        
        return False
    
    def build_command(self, data):
        """
        构建PN532命令包
        
        Args:
            data (list): 命令数据
            
        Returns:
            bytes: 完整的命令包
        """
        # 计算长度和校验和
        length = len(data) + 1  # +1 for direction
        checksum = (~length + 1) & 0xFF
        
        # 构建命令包
        cmd = [
            PN532_PREAMBLE,
            PN532_STARTCODE1,
            PN532_STARTCODE2,
            length,
            checksum,
            0xD4,  # Direction (host to PN532)
        ]
        cmd.extend(data)
        
        # 计算数据校验和
        data_checksum = 0xD4
        for byte in data:
            data_checksum += byte
        data_checksum = (~data_checksum + 1) & 0xFF
        
        cmd.append(data_checksum)
        cmd.append(PN532_POSTAMBLE)
        
        return bytes(cmd)
    
    def connect(self):
        """
        连接PN532模块
        
        Returns:
            bool: 连接成功返回True
        """
        if self.port is None:
            self.port = self.find_pn532_port()
            if self.port is None:
                print("❌ 无法找到PN532模块")
                return False
        
        try:
            self.serial_conn = serial.Serial(
                self.port, 
                self.baudrate, 
                timeout=1
            )
            time.sleep(1)  # 等待初始化
            
            print(f"✅ 已连接PN532模块: {self.port}")
            
            # 初始化PN532
            if self.initialize_pn532():
                print("✅ PN532初始化成功")
                return True
            else:
                print("❌ PN532初始化失败")
                return False
                
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def initialize_pn532(self):
        """
        初始化PN532模块
        
        Returns:
            bool: 初始化成功返回True
        """
        try:
            # 获取固件版本
            cmd = self.build_command([PN532_COMMAND_GETFIRMWAREVERSION])
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            if response and len(response) >= 4:
                ic = response[0]
                ver = response[1]
                rev = response[2]
                support = response[3]
                print(f"📋 固件版本: IC={ic}, Ver={ver}, Rev={rev}, Support={support}")
            
            # 配置SAM
            cmd = self.build_command([
                PN532_COMMAND_SAMCONFIGURATION,
                0x01,  # Normal mode
                0x14,  # Timeout 50ms * 20 = 1 second
                0x01   # Use IRQ pin
            ])
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            return response is not None
            
        except Exception as e:
            print(f"❌ 初始化错误: {e}")
            return False
    
    def read_response(self):
        """
        读取PN532响应
        
        Returns:
            list: 响应数据，如果失败返回None
        """
        try:
            # 读取前导码和开始码
            header = self.serial_conn.read(6)
            if len(header) < 6:
                return None
            
            if header[0:3] != bytes([0x00, 0x00, 0xFF]):
                return None
            
            length = header[3]
            if length == 0:  # Extended frame
                return None
            
            # 读取数据
            data = self.serial_conn.read(length + 2)  # +2 for checksum and postamble
            if len(data) < length + 2:
                return None
            
            # 验证校验和
            checksum = sum(data[:-2]) & 0xFF
            if checksum != (256 - data[-2]) & 0xFF:
                return None
            
            # 返回实际数据 (跳过方向字节)
            return list(data[1:-2])
            
        except Exception as e:
            print(f"❌ 读取响应错误: {e}")
            return None
    
    def detect_tag(self):
        """
        检测NFC标签
        
        Returns:
            dict: 标签信息，如果没有检测到返回None
        """
        try:
            # 发送被动目标检测命令
            cmd = self.build_command([
                PN532_COMMAND_INLISTPASSIVETARGET,
                0x01,  # Max 1 card
                0x00   # 106 kbps type A (ISO14443 Type A)
            ])
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            if response and len(response) >= 7:
                num_tags = response[0]
                if num_tags > 0:
                    tag_number = response[1]
                    sens_res = (response[2] << 8) | response[3]
                    sel_res = response[4]
                    uid_length = response[5]
                    uid = response[6:6+uid_length]
                    
                    tag_info = {
                        'tag_number': tag_number,
                        'sens_res': sens_res,
                        'sel_res': sel_res,
                        'uid': uid,
                        'uid_hex': ''.join([f'{b:02x}' for b in uid])
                    }
                    
                    return tag_info
            
            return None
            
        except Exception as e:
            print(f"❌ 检测标签错误: {e}")
            return None
    
    def read_tag_data(self, tag_info, block=4):
        """
        读取标签数据
        
        Args:
            tag_info (dict): 标签信息
            block (int): 要读取的块号
            
        Returns:
            bytes: 块数据，如果失败返回None
        """
        try:
            # 发送数据交换命令
            cmd = self.build_command([
                PN532_COMMAND_INDATAEXCHANGE,
                tag_info['tag_number'],  # Target number
                MIFARE_CMD_READ,         # MIFARE read command
                block                    # Block number
            ])
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            if response and len(response) >= 17:  # 16 bytes data + status
                status = response[0]
                if status == 0x00:  # Success
                    return bytes(response[1:17])
            
            return None
            
        except Exception as e:
            print(f"❌ 读取标签数据错误: {e}")
            return None
    
    def parse_page_from_data(self, data):
        """
        从标签数据解析页码
        
        Args:
            data (bytes): 标签数据
            
        Returns:
            int: 页码，如果无法解析返回None
        """
        try:
            if data:
                # 尝试解析文本数据
                text = data.decode('utf-8', errors='ignore').strip()
                
                # 直接数字
                if text.isdigit():
                    page_num = int(text)
                    if 1 <= page_num <= self.total_pages:
                        return page_num
                
                # "第X页"格式
                if text.startswith('第') and text.endswith('页'):
                    num_str = text[1:-1]
                    if num_str.isdigit():
                        page_num = int(num_str)
                        if 1 <= page_num <= self.total_pages:
                            return page_num
        except:
            pass
        
        return None
    
    def process_tag(self, tag_info):
        """
        处理检测到的NFC标签
        
        Args:
            tag_info (dict): 标签信息
        """
        try:
            uid_hex = tag_info['uid_hex']
            current_time = time.time()
            
            # 防重复触发
            if (uid_hex == self.last_tag_uid and 
                current_time - self.last_tag_time < self.tag_cooldown):
                return
            
            self.last_tag_uid = uid_hex
            self.last_tag_time = current_time
            
            print(f"🏷️  检测到标签: {uid_hex}")
            
            # 学习模式
            if self.learning_mode:
                self.learn_page_mapping(uid_hex)
                return
            
            # 正常模式
            if uid_hex in self.reverse_mappings:
                page_number = self.reverse_mappings[uid_hex]
                self.send_navigation_command(page_number, tag_info)
            else:
                # 尝试读取标签内容
                data = self.read_tag_data(tag_info)
                if data:
                    page_number = self.parse_page_from_data(data)
                    if page_number:
                        # 自动学习
                        self.add_page_mapping(page_number, uid_hex)
                        self.send_navigation_command(page_number, tag_info)
                    else:
                        print(f"❓ 未知标签内容: {data[:16].hex()}")
                else:
                    print(f"❓ 未知标签，建议添加映射: {uid_hex}")
            
        except Exception as e:
            print(f"❌ 处理标签错误: {e}")
    
    def send_navigation_command(self, page_number, tag_info):
        """发送导航命令"""
        try:
            packet_data = {
                'timestamp': datetime.now().isoformat(),
                'command': 'goto_page',
                'page_number': page_number,
                'total_pages': self.total_pages,
                'source': 'pn532_navigation',
                'tag_data': {
                    'uid': tag_info['uid_hex'],
                    'sens_res': tag_info['sens_res'],
                    'sel_res': tag_info['sel_res']
                }
            }
            
            json_data = json.dumps(packet_data, ensure_ascii=False)
            encoded_data = json_data.encode('utf-8')
            
            self.socket.sendto(encoded_data, ('127.0.0.1', self.udp_port))
            print(f"📖 跳转到第 {page_number} 页")
            
        except Exception as e:
            print(f"❌ 发送命令失败: {e}")
    
    def add_page_mapping(self, page_number, uid_hex):
        """添加页面映射"""
        if 1 <= page_number <= self.total_pages:
            self.page_mappings[page_number] = uid_hex
            self.reverse_mappings[uid_hex] = page_number
            print(f"✓ 已添加映射: 第{page_number}页 -> {uid_hex}")
    
    def start_learning_mode(self):
        """开始学习模式"""
        self.learning_mode = True
        self.current_learning_page = 1
        print(f"\n📚 学习模式已启动")
        print(f"请按顺序将每页的标签靠近PN532模块:")
        print(f"当前等待: 第{self.current_learning_page}页")
    
    def learn_page_mapping(self, uid_hex):
        """学习页面映射"""
        if self.current_learning_page <= self.total_pages:
            self.add_page_mapping(self.current_learning_page, uid_hex)
            self.current_learning_page += 1
            
            if self.current_learning_page <= self.total_pages:
                print(f"下一页: 第{self.current_learning_page}页")
            else:
                print(f"🎉 学习完成！已配置{self.total_pages}页")
                self.learning_mode = False
    
    def start_monitoring(self):
        """开始NFC监听"""
        if not self.connect():
            return False
        
        self.is_running = True
        print(f"\n🎯 PN532分页导航系统已启动")
        print(f"📍 请将页面左下角的标签靠近PN532模块")
        print(f"💡 输入 'learn' 开始学习模式")
        print(f"按 Ctrl+C 停止")
        
        # 启动命令处理线程
        command_thread = threading.Thread(target=self.command_interface)
        command_thread.daemon = True
        command_thread.start()
        
        try:
            while self.is_running:
                tag_info = self.detect_tag()
                if tag_info:
                    self.process_tag(tag_info)
                
                time.sleep(0.1)  # 避免过度占用CPU
                
        except KeyboardInterrupt:
            print(f"\n⏹️  PN532导航已停止")
        finally:
            self.stop_monitoring()
    
    def command_interface(self):
        """命令行界面"""
        while self.is_running:
            try:
                cmd = input().strip().lower()
                
                if cmd == 'learn':
                    self.start_learning_mode()
                elif cmd == 'mappings':
                    self.show_mappings()
                elif cmd == 'quit' or cmd == 'exit':
                    self.is_running = False
                    break
                    
            except EOFError:
                break
            except Exception as e:
                print(f"命令处理错误: {e}")
    
    def show_mappings(self):
        """显示映射"""
        print(f"\n=== PN532页面映射 ===")
        for page in sorted(self.page_mappings.keys()):
            uid = self.page_mappings[page]
            print(f"  第{page:2d}页: {uid}")
        print("=" * 25)
    
    def stop_monitoring(self):
        """停止监听"""
        self.is_running = False
        if self.serial_conn:
            self.serial_conn.close()
        self.socket.close()
        print("PN532控制器已停止")

def main():
    """主函数"""
    import sys
    
    print("=== PN532分页导航控制器 ===")
    
    # 解析参数
    total_pages = 10
    udp_port = 8890
    port = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 pn532_controller.py [串口] [页数] [UDP端口]")
            print("\n参数:")
            print("  串口: 串口名称 (默认: 自动检测)")
            print("  页数: 总页数 (默认: 10)")
            print("  UDP端口: UDP端口 (默认: 8890)")
            print("\n示例:")
            print("  python3 pn532_controller.py")
            print("  python3 pn532_controller.py /dev/ttyUSB0")
            print("  python3 pn532_controller.py COM3 10 8890")
            return
        else:
            try:
                if len(sys.argv) >= 2:
                    port = sys.argv[1]
                if len(sys.argv) >= 3:
                    total_pages = int(sys.argv[2])
                if len(sys.argv) >= 4:
                    udp_port = int(sys.argv[3])
            except ValueError:
                print("无效参数")
                return
    
    controller = PN532Controller(
        port=port,
        total_pages=total_pages,
        udp_port=udp_port
    )
    
    try:
        controller.start_monitoring()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        controller.stop_monitoring()

if __name__ == "__main__":
    main() 