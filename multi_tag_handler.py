#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多标签处理工具
专门处理读取范围内存在多个NFC标签的情况
"""

import time
import json
from datetime import datetime
from pn532_controller import PN532Controller

class MultiTagHandler(PN532Controller):
    def __init__(self, port=None, udp_port=8890, total_pages=10):
        """
        初始化多标签处理器
        """
        super().__init__(port, udp_port, total_pages)
        
        # 多标签处理配置
        self.max_tags = 2  # PN532最多同时处理2个标签
        self.tag_priority_strategy = "closest"  # 优先策略: closest, newest, specific
        self.multi_tag_cooldown = 1.0  # 多标签情况下的冷却时间
        
        # 标签历史记录
        self.tag_history = []
        self.last_detected_tags = []
        
        print("多标签处理器已初始化")
        print(f"最大同时检测标签数: {self.max_tags}")
        print(f"优先策略: {self.tag_priority_strategy}")
    
    def detect_multiple_tags(self):
        """
        检测多个标签
        
        Returns:
            list: 检测到的标签列表
        """
        try:
            # 发送多标签检测命令
            cmd = self.build_command([
                0x4A,  # PN532_COMMAND_INLISTPASSIVETARGET
                self.max_tags,  # 最多检测标签数
                0x00   # ISO14443A协议
            ])
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            if not response or len(response) < 1:
                return []
            
            num_tags = response[0]
            if num_tags == 0:
                return []
            
            tags = []
            offset = 1
            
            for i in range(num_tags):
                if offset >= len(response):
                    break
                
                try:
                    tag_number = response[offset]
                    sens_res = (response[offset + 1] << 8) | response[offset + 2]
                    sel_res = response[offset + 3]
                    uid_length = response[offset + 4]
                    
                    if offset + 5 + uid_length > len(response):
                        break
                    
                    uid = response[offset + 5:offset + 5 + uid_length]
                    uid_hex = ''.join([f'{b:02x}' for b in uid])
                    
                    tag_info = {
                        'tag_number': tag_number,
                        'sens_res': sens_res,
                        'sel_res': sel_res,
                        'uid': uid,
                        'uid_hex': uid_hex,
                        'detection_time': time.time(),
                        'signal_strength': self.estimate_signal_strength(sens_res)
                    }
                    
                    tags.append(tag_info)
                    offset += 5 + uid_length
                    
                except Exception as e:
                    print(f"解析第{i+1}个标签失败: {e}")
                    break
            
            return tags
            
        except Exception as e:
            print(f"❌ 多标签检测错误: {e}")
            return []
    
    def estimate_signal_strength(self, sens_res):
        """
        估算信号强度 (简化算法)
        
        Args:
            sens_res (int): SENS_RES值
            
        Returns:
            str: 信号强度等级
        """
        # 这是一个简化的估算，实际需要更复杂的算法
        if sens_res > 0x0040:
            return "strong"
        elif sens_res > 0x0020:
            return "medium" 
        else:
            return "weak"
    
    def select_priority_tag(self, tags):
        """
        从多个标签中选择优先标签
        
        Args:
            tags (list): 检测到的标签列表
            
        Returns:
            dict: 选中的优先标签
        """
        if not tags:
            return None
        
        if len(tags) == 1:
            return tags[0]
        
        print(f"🔍 检测到 {len(tags)} 个标签，应用优先策略: {self.tag_priority_strategy}")
        
        if self.tag_priority_strategy == "closest":
            # 选择信号最强的标签（通常是最近的）
            priority_tag = max(tags, key=lambda t: t['sens_res'])
            print(f"   选择最近标签: {priority_tag['uid_hex']}")
            
        elif self.tag_priority_strategy == "newest":
            # 选择最新检测到的标签
            priority_tag = max(tags, key=lambda t: t['detection_time'])
            print(f"   选择最新标签: {priority_tag['uid_hex']}")
            
        elif self.tag_priority_strategy == "specific":
            # 选择特定优先级的标签（基于映射）
            priority_tag = self.select_by_mapping_priority(tags)
            print(f"   选择映射优先标签: {priority_tag['uid_hex']}")
            
        else:
            # 默认选择第一个
            priority_tag = tags[0]
            print(f"   选择默认标签: {priority_tag['uid_hex']}")
        
        return priority_tag
    
    def select_by_mapping_priority(self, tags):
        """
        基于页面映射优先级选择标签
        
        Args:
            tags (list): 标签列表
            
        Returns:
            dict: 优先标签
        """
        # 查找已知映射的标签
        mapped_tags = []
        unmapped_tags = []
        
        for tag in tags:
            uid_hex = tag['uid_hex']
            if uid_hex in self.reverse_mappings:
                page_number = self.reverse_mappings[uid_hex]
                tag['mapped_page'] = page_number
                mapped_tags.append(tag)
            else:
                unmapped_tags.append(tag)
        
        if mapped_tags:
            # 优先选择页码较小的（假设用户想要较前的页面）
            return min(mapped_tags, key=lambda t: t['mapped_page'])
        else:
            # 没有映射的标签，选择信号最强的
            return max(unmapped_tags, key=lambda t: t['sens_res'])
    
    def process_multiple_tags(self, tags):
        """
        处理多标签情况
        
        Args:
            tags (list): 检测到的标签列表
        """
        try:
            current_time = time.time()
            
            # 显示所有检测到的标签
            print(f"\n🏷️  检测到 {len(tags)} 个标签:")
            for i, tag in enumerate(tags):
                uid_hex = tag['uid_hex']
                signal = tag['signal_strength']
                
                # 检查是否有映射
                if uid_hex in self.reverse_mappings:
                    page_num = self.reverse_mappings[uid_hex]
                    print(f"   {i+1}. {uid_hex} → 第{page_num}页 ({signal})")
                else:
                    print(f"   {i+1}. {uid_hex} → 未映射 ({signal})")
            
            # 选择优先标签
            priority_tag = self.select_priority_tag(tags)
            if not priority_tag:
                return
            
            # 防重复触发检查
            priority_uid = priority_tag['uid_hex']
            if (priority_uid == self.last_tag_uid and 
                current_time - self.last_tag_time < self.multi_tag_cooldown):
                return
            
            self.last_tag_uid = priority_uid
            self.last_tag_time = current_time
            self.last_detected_tags = tags
            
            # 记录到历史
            self.tag_history.append({
                'timestamp': current_time,
                'total_tags': len(tags),
                'selected_tag': priority_uid,
                'all_tags': [t['uid_hex'] for t in tags]
            })
            
            # 保持历史记录在合理范围内
            if len(self.tag_history) > 100:
                self.tag_history = self.tag_history[-50:]
            
            # 处理选中的标签
            if self.learning_mode:
                self.learn_page_mapping(priority_uid)
            else:
                self.process_selected_tag(priority_tag, len(tags))
                
        except Exception as e:
            print(f"❌ 处理多标签错误: {e}")
    
    def process_selected_tag(self, tag, total_count):
        """
        处理选中的标签
        
        Args:
            tag (dict): 选中的标签
            total_count (int): 总标签数
        """
        uid_hex = tag['uid_hex']
        
        # 检查映射
        if uid_hex in self.reverse_mappings:
            page_number = self.reverse_mappings[uid_hex]
            print(f"📖 选择标签 {uid_hex} → 跳转到第 {page_number} 页")
            print(f"   (在 {total_count} 个标签中选择)")
            
            self.send_navigation_command(page_number, {
                'uid': uid_hex,
                'sens_res': tag['sens_res'],
                'sel_res': tag['sel_res'],
                'signal_strength': tag['signal_strength'],
                'total_tags_detected': total_count,
                'selection_method': self.tag_priority_strategy
            })
        else:
            # 尝试读取标签内容
            data = self.read_tag_data(tag)
            if data:
                page_number = self.parse_page_from_data(data)
                if page_number:
                    self.add_page_mapping(page_number, uid_hex)
                    print(f"📖 自动映射 {uid_hex} → 第 {page_number} 页")
                    self.send_navigation_command(page_number, tag)
                else:
                    print(f"❓ 无法解析标签内容: {uid_hex}")
            else:
                print(f"❓ 未知标签: {uid_hex}")
    
    def start_monitoring(self):
        """
        开始多标签监听
        """
        if not self.connect():
            return False
        
        self.load_mappings()
        self.is_running = True
        
        print(f"\n🎯 多标签分页导航系统已启动")
        print(f"📍 支持同时检测 {self.max_tags} 个标签")
        print(f"🎯 优先策略: {self.tag_priority_strategy}")
        print(f"💡 可用命令: 'learn', 'mappings', 'stats', 'strategy'")
        print(f"按 Ctrl+C 停止")
        
        # 启动命令处理线程
        import threading
        command_thread = threading.Thread(target=self.command_interface)
        command_thread.daemon = True
        command_thread.start()
        
        try:
            while self.is_running:
                tags = self.detect_multiple_tags()
                if tags:
                    self.process_multiple_tags(tags)
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print(f"\n⏹️  多标签导航已停止")
        finally:
            self.stop_monitoring()
    
    def command_interface(self):
        """
        增强的命令行界面
        """
        while self.is_running:
            try:
                cmd = input().strip().lower()
                
                if cmd == 'learn':
                    self.start_learning_mode()
                elif cmd == 'mappings':
                    self.show_mappings()
                elif cmd == 'stats':
                    self.show_multi_tag_stats()
                elif cmd == 'strategy':
                    self.change_priority_strategy()
                elif cmd == 'history':
                    self.show_detection_history()
                elif cmd == 'quit' or cmd == 'exit':
                    self.is_running = False
                    break
                elif cmd == 'help':
                    self.show_multi_tag_help()
                    
            except EOFError:
                break
            except Exception as e:
                print(f"命令处理错误: {e}")
    
    def show_multi_tag_stats(self):
        """
        显示多标签统计信息
        """
        print(f"\n=== 多标签统计 ===")
        
        if not self.tag_history:
            print("暂无检测历史")
            return
        
        # 统计多标签检测次数
        multi_tag_detections = [h for h in self.tag_history if h['total_tags'] > 1]
        single_tag_detections = [h for h in self.tag_history if h['total_tags'] == 1]
        
        print(f"总检测次数: {len(self.tag_history)}")
        print(f"单标签检测: {len(single_tag_detections)}次")
        print(f"多标签检测: {len(multi_tag_detections)}次")
        
        if multi_tag_detections:
            avg_tags = sum(h['total_tags'] for h in multi_tag_detections) / len(multi_tag_detections)
            print(f"平均同时标签数: {avg_tags:.1f}")
            
            max_tags = max(h['total_tags'] for h in multi_tag_detections)
            print(f"最多同时标签: {max_tags}个")
        
        print("=" * 20)
    
    def change_priority_strategy(self):
        """
        更改优先策略
        """
        print(f"\n当前策略: {self.tag_priority_strategy}")
        print(f"可选策略:")
        print(f"1. closest - 选择最近的标签")
        print(f"2. newest - 选择最新检测的标签")
        print(f"3. specific - 基于页面映射优先级")
        
        choice = input("选择策略 (1-3): ").strip()
        
        strategies = {'1': 'closest', '2': 'newest', '3': 'specific'}
        if choice in strategies:
            self.tag_priority_strategy = strategies[choice]
            print(f"✅ 已切换到策略: {self.tag_priority_strategy}")
        else:
            print("❌ 无效选择")
    
    def show_detection_history(self):
        """
        显示检测历史
        """
        print(f"\n=== 最近检测历史 ===")
        recent_history = self.tag_history[-10:]  # 显示最近10次
        
        for i, record in enumerate(recent_history, 1):
            timestamp = datetime.fromtimestamp(record['timestamp'])
            selected = record['selected_tag']
            total = record['total_tags']
            
            print(f"{i:2d}. {timestamp.strftime('%H:%M:%S')} - "
                  f"选择 {selected[:8]}... (共{total}个标签)")
    
    def show_multi_tag_help(self):
        """
        显示多标签帮助
        """
        print(f"\n=== 多标签系统帮助 ===")
        print(f"learn      - 开始学习模式")
        print(f"mappings   - 显示页面映射")
        print(f"stats      - 显示多标签统计")
        print(f"strategy   - 更改标签优先策略")
        print(f"history    - 显示检测历史")
        print(f"help       - 显示此帮助")
        print(f"quit/exit  - 退出程序")
        print(f"=" * 25)

def main():
    """主函数"""
    import sys
    
    print("=== 多标签分页导航控制器 ===")
    
    # 解析参数
    total_pages = 10
    udp_port = 8890
    port = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n多标签处理功能:")
            print("• 同时检测多个NFC标签")
            print("• 智能选择优先标签")
            print("• 支持多种优先策略")
            print("• 详细的检测统计")
            print("\n使用方法:")
            print("  python3 multi_tag_handler.py [端口] [页数]")
            return
        else:
            try:
                if len(sys.argv) >= 2:
                    port = sys.argv[1] if not sys.argv[1].isdigit() else None
                    if sys.argv[1].isdigit():
                        udp_port = int(sys.argv[1])
                if len(sys.argv) >= 3:
                    total_pages = int(sys.argv[2])
            except ValueError:
                print("无效参数")
                return
    
    handler = MultiTagHandler(
        port=port,
        udp_port=udp_port,
        total_pages=total_pages
    )
    
    try:
        handler.start_monitoring()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        handler.stop_monitoring()

if __name__ == "__main__":
    main() 