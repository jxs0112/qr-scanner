#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PN532标签写入工具
专门用于PN532模块的NFC标签写入
"""

import time
import struct
from pn532_controller import PN532Controller

class PN532TagWriter(PN532Controller):
    def __init__(self, port=None, baudrate=115200):
        """
        初始化PN532标签写入工具
        
        Args:
            port (str): 串口名称
            baudrate (int): 波特率
        """
        # 不需要UDP功能，所以设置为0
        super().__init__(port, baudrate, udp_port=0, total_pages=10)
        print("PN532标签写入工具已初始化")
    
    def write_tag_data(self, tag_info, block, data):
        """
        写入标签数据
        
        Args:
            tag_info (dict): 标签信息
            block (int): 要写入的块号
            data (bytes): 要写入的数据 (16字节)
            
        Returns:
            bool: 写入成功返回True
        """
        try:
            if len(data) != 16:
                print(f"❌ 数据长度必须为16字节，当前为{len(data)}字节")
                return False
            
            # 发送数据交换命令
            cmd_data = [
                0x40,  # PN532_COMMAND_INDATAEXCHANGE
                tag_info['tag_number'],  # Target number
                0xA0,  # MIFARE write command
                block  # Block number
            ]
            cmd_data.extend(list(data))
            
            cmd = self.build_command(cmd_data)
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            if response and len(response) >= 1:
                status = response[0]
                if status == 0x00:  # Success
                    return True
                else:
                    print(f"❌ 写入失败，状态码: 0x{status:02x}")
            
            return False
            
        except Exception as e:
            print(f"❌ 写入标签数据错误: {e}")
            return False
    
    def write_page_tag(self, page_number, total_pages=10):
        """
        写入页面标签
        
        Args:
            page_number (int): 页码
            total_pages (int): 总页数
            
        Returns:
            bool: 写入成功返回True
        """
        print(f"\n📝 准备写入第 {page_number} 页标签")
        print(f"请将标签 #{page_number} 靠近PN532模块...")
        
        # 等待检测标签
        tag_info = None
        timeout = 30  # 30秒超时
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            tag_info = self.detect_tag()
            if tag_info:
                break
            time.sleep(0.1)
        
        if not tag_info:
            print(f"❌ 超时：未检测到标签")
            return False
        
        uid_hex = tag_info['uid_hex']
        print(f"✅ 检测到标签: {uid_hex}")
        
        try:
            # 准备要写入的数据
            text_content = f"第{page_number}页"
            
            # 将文本转换为16字节数据块
            text_bytes = text_content.encode('utf-8')
            
            # 构造数据块 (16字节)
            data_block = bytearray(16)
            
            # 前4字节：页码信息
            data_block[0] = page_number  # 页码
            data_block[1] = total_pages  # 总页数
            data_block[2] = len(text_bytes)  # 文本长度
            data_block[3] = 0x00  # 保留字节
            
            # 后12字节：文本内容
            text_len = min(len(text_bytes), 12)
            data_block[4:4+text_len] = text_bytes[:text_len]
            
            # 写入到块4 (NTAG213的用户数据区)
            if self.write_tag_data(tag_info, 4, bytes(data_block)):
                print(f"✅ 第 {page_number} 页标签写入成功!")
                print(f"   标签ID: {uid_hex}")
                print(f"   内容: {text_content}")
                print(f"   数据: {data_block.hex()}")
                return True
            else:
                print(f"❌ 第 {page_number} 页标签写入失败")
                return False
                
        except Exception as e:
            print(f"❌ 写入过程错误: {e}")
            return False
    
    def read_and_display_tag(self):
        """
        读取并显示标签信息
        """
        print(f"\n🔍 PN532标签读取测试")
        print(f"请将标签靠近PN532模块...")
        
        # 等待检测标签
        tag_info = None
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            tag_info = self.detect_tag()
            if tag_info:
                break
            time.sleep(0.1)
        
        if not tag_info:
            print(f"❌ 超时：未检测到标签")
            return
        
        try:
            uid_hex = tag_info['uid_hex']
            print(f"\n📱 检测到标签:")
            print(f"   标签ID: {uid_hex}")
            print(f"   SENS_RES: 0x{tag_info['sens_res']:04x}")
            print(f"   SEL_RES: 0x{tag_info['sel_res']:02x}")
            
            # 读取用户数据区 (块4)
            data = self.read_tag_data(tag_info, 4)
            if data:
                print(f"\n📄 块4数据:")
                print(f"   原始数据: {data.hex()}")
                
                # 解析数据
                if len(data) >= 4:
                    page_num = data[0]
                    total_pages = data[1]
                    text_len = data[2]
                    
                    if page_num > 0 and page_num <= 100:
                        print(f"   页码: {page_num}")
                        print(f"   总页数: {total_pages}")
                        
                        if text_len > 0 and text_len <= 12:
                            text_data = data[4:4+text_len]
                            try:
                                text = text_data.decode('utf-8')
                                print(f"   文本内容: {text}")
                            except:
                                print(f"   文本数据: {text_data.hex()}")
                
                # 尝试解析整个数据为文本
                try:
                    full_text = data.decode('utf-8', errors='ignore').strip('\x00')
                    if full_text:
                        print(f"   完整文本: {full_text}")
                except:
                    pass
            else:
                print(f"   无法读取用户数据")
            
        except Exception as e:
            print(f"❌ 读取标签错误: {e}")
    
    def batch_write_tags(self, total_pages=10):
        """
        批量写入标签
        
        Args:
            total_pages (int): 总页数
        """
        print(f"🏷️  PN532标签批量写入工具")
        print(f"准备为 {total_pages} 页文档配置标签")
        print(f"=" * 40)
        
        print(f"\n📋 写入计划:")
        for i in range(1, total_pages + 1):
            print(f"  标签 #{i}: 第{i}页")
        
        input("\n按 Enter 键开始写入...")
        
        success_count = 0
        failed_pages = []
        
        for page in range(1, total_pages + 1):
            print(f"\n⏳ 进度: {page}/{total_pages}")
            
            if self.write_page_tag(page, total_pages):
                success_count += 1
                input(f"✅ 第 {page} 页完成，请放置下一个标签后按 Enter...")
            else:
                failed_pages.append(page)
                retry = input(f"❌ 第 {page} 页失败，是否重试? (y/n): ").lower()
                if retry == 'y':
                    if self.write_page_tag(page, total_pages):
                        success_count += 1
                        failed_pages.remove(page)
                        input(f"✅ 第 {page} 页重试成功，请放置下一个标签后按 Enter...")
                    else:
                        input(f"❌ 第 {page} 页重试仍失败，按 Enter 继续...")
        
        # 显示结果
        print(f"\n🎉 批量写入完成!")
        print(f"成功: {success_count}/{total_pages} 个标签")
        
        if failed_pages:
            print(f"❌ 失败的页面: {failed_pages}")
            print(f"建议稍后重新写入这些标签")
        else:
            print(f"✅ 所有标签写入成功!")
        
        return success_count, failed_pages

def main():
    """
    主函数
    """
    import sys
    
    print("=== PN532标签写入工具 ===")
    print("专用于PN532模块的NFC标签写入")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 pn532_tag_writer.py [选项] [参数]")
            print("\n选项:")
            print("  --batch [页数]     批量写入标签")
            print("  --single [页码]    写入单个标签")
            print("  --read            读取标签信息")
            print("  --help            显示此帮助")
            print("\n参数:")
            print("  页数: 总页数 (默认: 10)")
            print("  页码: 要写入的页码")
            print("\n示例:")
            print("  python3 pn532_tag_writer.py --batch 10")
            print("  python3 pn532_tag_writer.py --single 5")
            print("  python3 pn532_tag_writer.py --read")
            return
        
        elif sys.argv[1] == '--read':
            writer = PN532TagWriter()
            if writer.connect():
                writer.read_and_display_tag()
            return
        
        elif sys.argv[1] == '--batch':
            total_pages = 10
            if len(sys.argv) > 2:
                try:
                    total_pages = int(sys.argv[2])
                except ValueError:
                    print("❌ 无效的页数")
                    return
            
            writer = PN532TagWriter()
            if writer.connect():
                writer.batch_write_tags(total_pages)
            return
        
        elif sys.argv[1] == '--single':
            if len(sys.argv) < 3:
                print("❌ 请指定页码")
                return
            
            try:
                page_number = int(sys.argv[2])
                writer = PN532TagWriter()
                if writer.connect():
                    writer.write_page_tag(page_number)
            except ValueError:
                print("❌ 无效的页码")
            return
    
    # 交互模式
    print("\n请选择操作:")
    print("1. 批量写入标签")
    print("2. 写入单个标签")
    print("3. 读取标签信息")
    print("4. 退出")
    
    try:
        choice = input("\n请选择 (1-4): ").strip()
        
        writer = PN532TagWriter()
        if not writer.connect():
            print("❌ 无法连接PN532模块")
            return
        
        if choice == '1':
            total_pages = input("总页数 (默认10): ").strip()
            total_pages = int(total_pages) if total_pages else 10
            writer.batch_write_tags(total_pages)
        
        elif choice == '2':
            page_number = int(input("页码: ").strip())
            writer.write_page_tag(page_number)
        
        elif choice == '3':
            writer.read_and_display_tag()
        
        elif choice == '4':
            print("退出")
        
        else:
            print("❌ 无效选择")
    
    except (ValueError, KeyboardInterrupt):
        print("\n程序中断")
    except Exception as e:
        print(f"❌ 程序错误: {e}")

if __name__ == "__main__":
    main() 