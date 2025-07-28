#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PN532天线测试工具
用于测试不同天线配置的读取距离和性能
"""

import time
import threading
from pn532_controller import PN532Controller

class AntennaTester(PN532Controller):
    def __init__(self, port=None):
        """
        初始化天线测试器
        
        Args:
            port (str): 串口名称
        """
        super().__init__(port, udp_port=0, total_pages=1)
        self.test_results = []
        self.is_testing = False
        
    def test_read_distance(self, test_duration=30):
        """
        测试读取距离
        
        Args:
            test_duration (int): 测试持续时间(秒)
        """
        print(f"\n📡 天线读取距离测试")
        print(f"测试时长: {test_duration}秒")
        print(f"=" * 40)
        
        print(f"\n📋 测试步骤:")
        print(f"1. 将标签放在距离天线2cm处")
        print(f"2. 每5秒逐渐增加1cm距离")
        print(f"3. 观察最远检测距离")
        print(f"4. 记录稳定读取的最大距离")
        
        input("按 Enter 开始测试...")
        
        self.is_testing = True
        detection_count = 0
        last_detection_time = 0
        max_stable_distance = 0
        current_distance = 2  # 从2cm开始
        
        start_time = time.time()
        last_distance_change = start_time
        
        print(f"\n🔍 开始测试 (当前距离: {current_distance}cm)")
        print(f"将标签放在天线上方 {current_distance}cm 处...")
        
        try:
            while time.time() - start_time < test_duration and self.is_testing:
                current_time = time.time()
                
                # 每5秒提示增加距离
                if current_time - last_distance_change >= 5 and current_distance <= 20:
                    current_distance += 1
                    last_distance_change = current_time
                    print(f"\n📏 请将标签移至 {current_distance}cm 距离")
                
                # 检测标签
                tag_info = self.detect_tag()
                if tag_info:
                    detection_count += 1
                    last_detection_time = current_time
                    
                    print(f"✅ {current_distance}cm: 检测到标签 {tag_info['uid_hex']}")
                    
                    # 记录稳定检测的距离
                    if current_distance > max_stable_distance:
                        max_stable_distance = current_distance
                    
                    # 记录测试结果
                    self.test_results.append({
                        'distance': current_distance,
                        'timestamp': current_time,
                        'uid': tag_info['uid_hex'],
                        'sens_res': tag_info['sens_res'],
                        'signal_quality': 'good' if current_time - last_detection_time < 1 else 'weak'
                    })
                
                time.sleep(0.2)  # 200ms检测间隔
                
        except KeyboardInterrupt:
            print(f"\n⏹️  测试被用户中断")
        
        self.is_testing = False
        
        # 显示测试结果
        print(f"\n📊 测试结果:")
        print(f"检测次数: {detection_count}")
        print(f"最大稳定距离: {max_stable_distance}cm")
        print(f"测试时长: {time.time() - start_time:.1f}秒")
        
        if self.test_results:
            print(f"\n📈 距离统计:")
            distance_stats = {}
            for result in self.test_results:
                dist = result['distance']
                if dist not in distance_stats:
                    distance_stats[dist] = 0
                distance_stats[dist] += 1
            
            for dist in sorted(distance_stats.keys()):
                count = distance_stats[dist]
                print(f"  {dist:2d}cm: {count:3d}次检测")
        
        return max_stable_distance
    
    def test_antenna_performance(self, test_positions=8):
        """
        测试天线不同位置的性能
        
        Args:
            test_positions (int): 测试位置数量
        """
        print(f"\n🎯 天线覆盖范围测试")
        print(f"测试 {test_positions} 个不同位置")
        print(f"=" * 40)
        
        positions = [
            "中心位置",
            "上方",
            "下方", 
            "左侧",
            "右侧",
            "左上角",
            "右上角",
            "左下角",
            "右下角"
        ]
        
        results = {}
        
        for i, position in enumerate(positions[:test_positions]):
            print(f"\n📍 位置 {i+1}/{test_positions}: {position}")
            input(f"请将标签放在天线{position}，然后按 Enter...")
            
            # 测试此位置
            detection_count = 0
            test_duration = 5  # 每个位置测试5秒
            start_time = time.time()
            
            print(f"🔍 测试中...")
            while time.time() - start_time < test_duration:
                tag_info = self.detect_tag()
                if tag_info:
                    detection_count += 1
                time.sleep(0.1)
            
            success_rate = (detection_count / (test_duration * 10)) * 100
            results[position] = {
                'detections': detection_count,
                'success_rate': success_rate
            }
            
            if success_rate > 80:
                print(f"✅ {position}: {success_rate:.1f}% (优秀)")
            elif success_rate > 50:
                print(f"🟡 {position}: {success_rate:.1f}% (良好)")
            else:
                print(f"❌ {position}: {success_rate:.1f}% (较差)")
        
        # 显示综合结果
        print(f"\n📊 天线覆盖范围报告:")
        print(f"位置\t\t检测率\t评价")
        print(f"-" * 35)
        
        for position, data in results.items():
            rate = data['success_rate']
            if rate > 80:
                rating = "优秀"
            elif rate > 50:
                rating = "良好"
            else:
                rating = "较差"
            
            print(f"{position:8}\t{rate:5.1f}%\t{rating}")
        
        return results
    
    def test_interference(self):
        """
        测试环境干扰
        """
        print(f"\n📶 环境干扰测试")
        print(f"=" * 30)
        
        scenarios = [
            "正常环境",
            "靠近金属物体",
            "靠近电子设备",
            "靠近WiFi路由器"
        ]
        
        for scenario in scenarios:
            print(f"\n🔬 场景: {scenario}")
            input(f"请调整环境至'{scenario}'，然后按 Enter...")
            
            # 测试10秒
            detection_count = 0
            error_count = 0
            test_duration = 10
            start_time = time.time()
            
            print(f"🔍 测试中...")
            while time.time() - start_time < test_duration:
                try:
                    tag_info = self.detect_tag()
                    if tag_info:
                        detection_count += 1
                except Exception:
                    error_count += 1
                
                time.sleep(0.2)
            
            success_rate = (detection_count / (test_duration * 5)) * 100
            
            print(f"📊 {scenario} 结果:")
            print(f"  检测成功: {detection_count}次")
            print(f"  通信错误: {error_count}次")
            print(f"  成功率: {success_rate:.1f}%")
            
            if success_rate > 80:
                print(f"  ✅ 环境良好")
            elif success_rate > 50:
                print(f"  🟡 轻微干扰")
            else:
                print(f"  ❌ 严重干扰")
    
    def optimize_antenna_position(self):
        """
        天线位置优化建议
        """
        print(f"\n🎯 天线优化建议")
        print(f"=" * 30)
        
        print(f"📐 理想放置位置:")
        print(f"• 距离页面放置区域中心下方3-5cm")
        print(f"• 避免金属物体遮挡")
        print(f"• 远离强电磁干扰源")
        print(f"• 天线平面与页面平行")
        
        print(f"\n🔧 性能优化技巧:")
        print(f"• 使用更大尺寸天线 (8-12cm直径)")
        print(f"• 适当调整天线到主板的连接线长度")
        print(f"• 在天线下方放置金属接地板(可选)")
        print(f"• 定期清洁天线表面")
        
        print(f"\n⚡ 距离增强方法:")
        print(f"• 选择高品质NFC标签")
        print(f"• 确保标签天线完整无损")
        print(f"• 标签与读卡器天线保持平行")
        print(f"• 避免标签重叠放置")

def main():
    """主函数"""
    import sys
    
    print("=== PN532天线测试工具 ===")
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("\n使用方法:")
        print("  python3 antenna_tester.py [选项]")
        print("\n功能:")
        print("  1. 读取距离测试")
        print("  2. 覆盖范围测试") 
        print("  3. 环境干扰测试")
        print("  4. 优化建议")
        return
    
    tester = AntennaTester()
    
    if not tester.connect():
        print("❌ 无法连接PN532模块")
        return
    
    try:
        while True:
            print(f"\n📋 请选择测试项目:")
            print(f"1. 读取距离测试")
            print(f"2. 覆盖范围测试")
            print(f"3. 环境干扰测试") 
            print(f"4. 优化建议")
            print(f"5. 退出")
            
            choice = input(f"\n请选择 (1-5): ").strip()
            
            if choice == '1':
                duration = input("测试时长(秒，默认30): ").strip()
                duration = int(duration) if duration else 30
                tester.test_read_distance(duration)
                
            elif choice == '2':
                positions = input("测试位置数(默认8): ").strip()
                positions = int(positions) if positions else 8
                tester.test_antenna_performance(positions)
                
            elif choice == '3':
                tester.test_interference()
                
            elif choice == '4':
                tester.optimize_antenna_position()
                
            elif choice == '5':
                print("退出测试")
                break
                
            else:
                print("❌ 无效选择")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  测试已停止")
    finally:
        tester.stop_monitoring()

if __name__ == "__main__":
    main() 