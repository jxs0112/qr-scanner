#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分页导航控制器
专门用于多页文档的直接页面跳转，通过NFC标签实现精确的页面导航
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

class PageNavigationController:
    def __init__(self, udp_host='127.0.0.1', udp_port=8890, total_pages=10, device_path=None):
        """
        初始化分页导航控制器
        
        Args:
            udp_host (str): UDP目标主机地址
            udp_port (int): UDP目标端口
            total_pages (int): 总页数
            device_path (str): NFC设备路径
        """
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.total_pages = total_pages
        self.device_path = device_path
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # NFC设备和状态
        self.clf = None
        self.is_running = False
        self.last_tag_id = None
        self.last_tag_time = 0
        self.tag_cooldown = 0.5  # 页面跳转响应更快
        
        # 页面标签映射
        self.page_mappings = {}
        self.reverse_mappings = {}  # 标签ID -> 页码
        
        # 自动学习模式
        self.learning_mode = False
        self.current_learning_page = 1
        
        # 统计信息
        self.navigation_stats = {
            'total_navigations': 0,
            'page_usage': [0] * (total_pages + 1),  # 索引0不用，1-10对应页面
            'last_page': 0,
            'session_start': time.time()
        }
        
        print(f"分页导航控制器已初始化")
        print(f"UDP目标: {udp_host}:{udp_port}")
        print(f"总页数: {total_pages}")
        print(f"NFC库可用: {'是' if NFC_AVAILABLE else '否'}")
    
    def initialize_nfc(self):
        """初始化NFC设备"""
        if not NFC_AVAILABLE:
            print("❌ NFC库不可用")
            return False
        
        try:
            self.clf = nfc.ContactlessFrontend(self.device_path)
            if self.clf:
                print(f"✅ NFC设备已连接: {self.clf}")
                print(f"📍 请将NFC读卡器放在左下角台子背后")
                return True
            else:
                print("❌ 无法连接NFC设备")
                return False
        except Exception as e:
            print(f"❌ NFC设备初始化失败: {e}")
            return False
    
    def send_navigation_command(self, page_number, tag_data=None):
        """
        发送页面导航命令
        
        Args:
            page_number (int): 目标页码
            tag_data (dict): 标签数据
        """
        try:
            packet_data = {
                'timestamp': datetime.now().isoformat(),
                'command': 'goto_page',
                'page_number': page_number,
                'total_pages': self.total_pages,
                'source': 'page_navigation',
                'tag_data': tag_data
            }
            
            json_data = json.dumps(packet_data, ensure_ascii=False)
            encoded_data = json_data.encode('utf-8')
            
            self.socket.sendto(encoded_data, (self.udp_host, self.udp_port))
            
            # 更新统计
            self.navigation_stats['total_navigations'] += 1
            if 1 <= page_number <= self.total_pages:
                self.navigation_stats['page_usage'][page_number] += 1
            self.navigation_stats['last_page'] = page_number
            
            print(f"📖 跳转到第 {page_number} 页")
            
        except Exception as e:
            print(f"✗ 导航命令发送失败: {e}")
    
    def process_nfc_tag(self, tag):
        """
        处理NFC标签
        
        Args:
            tag: NFC标签对象
        """
        try:
            tag_id = tag.identifier.hex() if tag.identifier else "unknown"
            tag_type = str(tag.type)
            current_time = time.time()
            
            # 防止重复触发
            if (tag_id == self.last_tag_id and 
                current_time - self.last_tag_time < self.tag_cooldown):
                return
            
            self.last_tag_id = tag_id
            self.last_tag_time = current_time
            
            print(f"🏷️  检测到标签: {tag_id}")
            
            # 学习模式：建立标签与页面的映射
            if self.learning_mode:
                self.learn_page_mapping(tag_id)
                return
            
            # 正常模式：根据映射跳转页面
            if tag_id in self.reverse_mappings:
                page_number = self.reverse_mappings[tag_id]
                self.send_navigation_command(page_number, {
                    'tag_id': tag_id,
                    'tag_type': tag_type,
                    'recognition_method': 'learned_mapping'
                })
            else:
                # 尝试解析标签内容
                page_number = self.parse_page_from_tag(tag)
                if page_number:
                    # 自动学习新的映射
                    self.add_page_mapping(page_number, tag_id)
                    self.send_navigation_command(page_number, {
                        'tag_id': tag_id,
                        'tag_type': tag_type,
                        'recognition_method': 'content_parsing'
                    })
                else:
                    print(f"❓ 未知标签，请配置映射或使用学习模式")
                    # 可以提示用户当前检测到的标签ID
                    print(f"   标签ID: {tag_id}")
                    print(f"   使用命令添加映射: add_mapping {tag_id} [页码]")
                    
        except Exception as e:
            print(f"❌ 处理NFC标签失败: {e}")
    
    def parse_page_from_tag(self, tag):
        """
        从标签内容解析页码
        
        Args:
            tag: NFC标签对象
            
        Returns:
            int: 页码，如果无法解析则返回None
        """
        try:
            if tag.ndef and tag.ndef.records:
                for record in tag.ndef.records:
                    # 文本记录
                    if record.type == 'urn:nfc:wkt:T':
                        try:
                            text = record.text.strip()
                            
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
                            
                            # "Page X"格式
                            if text.lower().startswith('page '):
                                num_str = text[5:].strip()
                                if num_str.isdigit():
                                    page_num = int(num_str)
                                    if 1 <= page_num <= self.total_pages:
                                        return page_num
                            
                        except:
                            continue
                    
                    # URI记录
                    elif record.type == 'urn:nfc:wkt:U':
                        try:
                            uri = record.uri.lower()
                            if 'page=' in uri:
                                page_str = uri.split('page=')[1].split('&')[0]
                                if page_str.isdigit():
                                    page_num = int(page_str)
                                    if 1 <= page_num <= self.total_pages:
                                        return page_num
                        except:
                            continue
        except:
            pass
        
        return None
    
    def add_page_mapping(self, page_number, tag_id):
        """
        添加页面映射
        
        Args:
            page_number (int): 页码
            tag_id (str): 标签ID
        """
        if 1 <= page_number <= self.total_pages:
            self.page_mappings[page_number] = tag_id
            self.reverse_mappings[tag_id] = page_number
            print(f"✓ 已添加映射: 第{page_number}页 -> {tag_id}")
            self.save_mappings()
        else:
            print(f"❌ 无效页码: {page_number} (有效范围: 1-{self.total_pages})")
    
    def remove_page_mapping(self, page_number):
        """移除页面映射"""
        if page_number in self.page_mappings:
            tag_id = self.page_mappings[page_number]
            del self.page_mappings[page_number]
            del self.reverse_mappings[tag_id]
            print(f"✓ 已移除映射: 第{page_number}页")
            self.save_mappings()
    
    def start_learning_mode(self):
        """开始学习模式"""
        self.learning_mode = True
        self.current_learning_page = 1
        print(f"\n📚 学习模式已启动")
        print(f"请按顺序将每页的标签靠近读卡器:")
        print(f"当前等待: 第{self.current_learning_page}页")
        print(f"完成后输入 'stop_learning' 结束学习")
    
    def learn_page_mapping(self, tag_id):
        """学习页面映射"""
        if self.current_learning_page <= self.total_pages:
            self.add_page_mapping(self.current_learning_page, tag_id)
            self.current_learning_page += 1
            
            if self.current_learning_page <= self.total_pages:
                print(f"下一页: 第{self.current_learning_page}页")
            else:
                print(f"🎉 学习完成！已配置{self.total_pages}页")
                self.stop_learning_mode()
    
    def stop_learning_mode(self):
        """停止学习模式"""
        self.learning_mode = False
        print(f"📚 学习模式已结束")
        self.show_mappings()
    
    def show_mappings(self):
        """显示所有页面映射"""
        print(f"\n=== 页面映射 (共{len(self.page_mappings)}页) ===")
        if self.page_mappings:
            for page in sorted(self.page_mappings.keys()):
                tag_id = self.page_mappings[page]
                usage = self.navigation_stats['page_usage'][page]
                print(f"  第{page:2d}页: {tag_id} (使用次数: {usage})")
        else:
            print("  无页面映射")
        print("=" * 35)
    
    def show_statistics(self):
        """显示使用统计"""
        runtime = time.time() - self.navigation_stats['session_start']
        print(f"\n=== 导航统计 ===")
        print(f"会话时长: {runtime/60:.1f} 分钟")
        print(f"总导航次数: {self.navigation_stats['total_navigations']}")
        print(f"当前页面: 第{self.navigation_stats['last_page']}页")
        print(f"最常用页面:")
        
        # 按使用次数排序
        page_usage = [(i, count) for i, count in enumerate(self.navigation_stats['page_usage'][1:], 1) if count > 0]
        page_usage.sort(key=lambda x: x[1], reverse=True)
        
        for page, count in page_usage[:5]:  # 显示前5个最常用的
            print(f"  第{page}页: {count}次")
        print("===============")
    
    def save_mappings(self):
        """保存映射到文件"""
        try:
            mapping_data = {
                'page_mappings': self.page_mappings,
                'total_pages': self.total_pages,
                'created_time': datetime.now().isoformat()
            }
            
            with open('page_mappings.json', 'w', encoding='utf-8') as f:
                json.dump(mapping_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存映射失败: {e}")
    
    def load_mappings(self):
        """从文件加载映射"""
        try:
            with open('page_mappings.json', 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)
                
            self.page_mappings = mapping_data.get('page_mappings', {})
            # 转换字符串键为整数
            self.page_mappings = {int(k): v for k, v in self.page_mappings.items()}
            
            # 重建反向映射
            self.reverse_mappings = {v: k for k, v in self.page_mappings.items()}
            
            saved_total = mapping_data.get('total_pages', self.total_pages)
            if saved_total != self.total_pages:
                print(f"⚠️  警告: 保存的页数({saved_total})与当前设置({self.total_pages})不匹配")
            
            print(f"✓ 已加载{len(self.page_mappings)}个页面映射")
            
        except FileNotFoundError:
            print("📝 未找到映射文件，将创建新的映射")
        except Exception as e:
            print(f"加载映射失败: {e}")
    
    def start_monitoring(self):
        """开始NFC监听"""
        if not self.initialize_nfc():
            return False
        
        # 加载已保存的映射
        self.load_mappings()
        
        self.is_running = True
        print(f"\n🎯 分页导航系统已启动")
        print(f"📖 支持{self.total_pages}页直接跳转")
        print(f"📍 将页面左下角的标签靠近读卡器即可跳转")
        print(f"💡 输入 'help' 查看可用命令")
        print(f"按 Ctrl+C 停止")
        
        # 启动命令处理线程
        command_thread = threading.Thread(target=self.command_interface)
        command_thread.daemon = True
        command_thread.start()
        
        try:
            while self.is_running:
                # NFC监听
                tag = self.clf.connect(rdwr={
                    'on-connect': self.process_nfc_tag
                })
                
                if not tag:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print(f"\n⏹️  分页导航已停止")
        except Exception as e:
            print(f"❌ NFC监听错误: {e}")
        finally:
            self.stop_monitoring()
    
    def command_interface(self):
        """命令行界面"""
        while self.is_running:
            try:
                cmd = input().strip().lower()
                
                if cmd == 'help':
                    self.show_help()
                elif cmd == 'mappings' or cmd == 'list':
                    self.show_mappings()
                elif cmd == 'stats':
                    self.show_statistics()
                elif cmd == 'learn':
                    self.start_learning_mode()
                elif cmd == 'stop_learning':
                    self.stop_learning_mode()
                elif cmd.startswith('add_mapping '):
                    parts = cmd.split()
                    if len(parts) == 3:
                        try:
                            tag_id = parts[1]
                            page_num = int(parts[2])
                            self.add_page_mapping(page_num, tag_id)
                        except ValueError:
                            print("❌ 页码必须是数字")
                elif cmd.startswith('remove_mapping '):
                    try:
                        page_num = int(cmd.split()[1])
                        self.remove_page_mapping(page_num)
                    except (ValueError, IndexError):
                        print("❌ 请提供有效页码")
                elif cmd == 'quit' or cmd == 'exit':
                    self.is_running = False
                    break
                elif cmd:
                    print("❓ 未知命令，输入 'help' 查看帮助")
                    
            except EOFError:
                break
            except Exception as e:
                print(f"命令处理错误: {e}")
    
    def show_help(self):
        """显示帮助信息"""
        print(f"\n=== 可用命令 ===")
        print(f"help          - 显示此帮助")
        print(f"mappings      - 显示页面映射")
        print(f"stats         - 显示使用统计")
        print(f"learn         - 开始学习模式")
        print(f"stop_learning - 停止学习模式")
        print(f"add_mapping <标签ID> <页码> - 手动添加映射")
        print(f"remove_mapping <页码> - 移除映射")
        print(f"quit/exit     - 退出程序")
        print(f"===============")
    
    def stop_monitoring(self):
        """停止监听"""
        self.is_running = False
        if self.clf:
            try:
                self.clf.close()
            except:
                pass
            self.clf = None
        print("分页导航已停止")
    
    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        self.socket.close()
        self.save_mappings()
        print("分页导航资源已清理")

def main():
    """主函数"""
    import sys
    
    print("=== 分页导航控制器 ===")
    print("支持10页文档的直接页面跳转")
    
    if not NFC_AVAILABLE:
        print("\n❌ 错误: 缺少NFC库")
        print("请安装: pip install nfcpy")
        return
    
    # 解析参数
    total_pages = 10
    udp_port = 8890
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 page_navigation_controller.py [页数] [端口]")
            print("\n参数:")
            print("  页数: 总页数 (默认: 10)")
            print("  端口: UDP端口 (默认: 8890)")
            print("\n设置步骤:")
            print("  1. 将NFC读卡器放在左下角台子背后")
            print("  2. 在每页左下角贴一个NFC标签")
            print("  3. 运行程序并使用学习模式配置映射")
            print("  4. 使用时将页面左下角靠近读卡器")
            return
        else:
            try:
                if len(sys.argv) >= 2:
                    total_pages = int(sys.argv[1])
                if len(sys.argv) >= 3:
                    udp_port = int(sys.argv[2])
            except ValueError:
                print("无效参数")
                return
    
    controller = PageNavigationController(
        total_pages=total_pages,
        udp_port=udp_port
    )
    
    try:
        controller.start_monitoring()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        controller.cleanup()

if __name__ == "__main__":
    main() 