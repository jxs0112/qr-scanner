#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFC协议兼容性测试工具
测试不同NFC协议和标签类型的兼容性
"""

import time
from pn532_controller import PN532Controller

class ProtocolTester(PN532Controller):
    def __init__(self, port=None):
        """
        初始化协议测试器
        """
        super().__init__(port, udp_port=0, total_pages=1)
        
        # 支持的协议类型
        self.protocols = {
            0x00: "ISO14443A (Type A)",
            0x01: "ISO14443B (Type B)",
            0x02: "FeliCa 212kbps",
            0x03: "FeliCa 424kbps"
        }
        
        # 常见标签类型
        self.tag_types = {
            'NTAG213': {'protocol': 0x00, 'capacity': '180 bytes', 'price': '¥2-5'},
            'NTAG215': {'protocol': 0x00, 'capacity': '540 bytes', 'price': '¥3-8'},
            'NTAG216': {'protocol': 0x00, 'capacity': '930 bytes', 'price': '¥5-12'},
            'MIFARE Classic 1K': {'protocol': 0x00, 'capacity': '1024 bytes', 'price': '¥3-8'},
            'MIFARE Ultralight': {'protocol': 0x00, 'capacity': '64 bytes', 'price': '¥2-6'},
        }
    
    def detect_tag_with_protocol(self, protocol_type):
        """
        使用指定协议检测标签
        
        Args:
            protocol_type (int): 协议类型
            
        Returns:
            dict: 标签信息或None
        """
        try:
            cmd = self.build_command([
                0x4A,  # PN532_COMMAND_INLISTPASSIVETARGET
                0x01,  # Max 1 card
                protocol_type  # Protocol type
            ])
            self.serial_conn.write(cmd)
            
            response = self.read_response()
            if response and len(response) >= 7:
                num_tags = response[0]
                if num_tags > 0:
                    tag_number = response[1]
                    
                    if protocol_type == 0x00:  # ISO14443A
                        sens_res = (response[2] << 8) | response[3]
                        sel_res = response[4]
                        uid_length = response[5]
                        uid = response[6:6+uid_length]
                        
                        return {
                            'protocol': protocol_type,
                            'protocol_name': self.protocols[protocol_type],
                            'tag_number': tag_number,
                            'sens_res': sens_res,
                            'sel_res': sel_res,
                            'uid': uid,
                            'uid_hex': ''.join([f'{b:02x}' for b in uid])
                        }
                    
                    elif protocol_type == 0x01:  # ISO14443B
                        # ISO14443B has different response format
                        return {
                            'protocol': protocol_type,
                            'protocol_name': self.protocols[protocol_type],
                            'tag_number': tag_number,
                            'raw_data': response[2:]
                        }
                    
                    else:  # FeliCa
                        return {
                            'protocol': protocol_type,
                            'protocol_name': self.protocols[protocol_type],
                            'tag_number': tag_number,
                            'raw_data': response[2:]
                        }
            
            return None
            
        except Exception as e:
            print(f"协议 {self.protocols.get(protocol_type, 'Unknown')} 检测错误: {e}")
            return None
    
    def test_all_protocols(self):
        """
        测试所有支持的协议
        """
        print(f"\n📡 NFC协议兼容性测试")
        print(f"=" * 40)
        
        print(f"请放置一个NFC标签靠近读卡器...")
        input("按 Enter 开始测试...")
        
        results = {}
        
        for protocol_id, protocol_name in self.protocols.items():
            print(f"\n🔍 测试协议: {protocol_name}")
            
            tag_info = self.detect_tag_with_protocol(protocol_id)
            if tag_info:
                print(f"✅ 检测成功!")
                print(f"   标签UID: {tag_info.get('uid_hex', 'N/A')}")
                if 'sens_res' in tag_info:
                    print(f"   SENS_RES: 0x{tag_info['sens_res']:04x}")
                    print(f"   SEL_RES: 0x{tag_info['sel_res']:02x}")
                
                results[protocol_id] = tag_info
            else:
                print(f"❌ 未检测到")
                results[protocol_id] = None
        
        return results
    
    def identify_tag_type(self, tag_info):
        """
        识别标签类型
        
        Args:
            tag_info (dict): 标签信息
            
        Returns:
            str: 标签类型名称
        """
        if not tag_info or tag_info['protocol'] != 0x00:
            return "Unknown"
        
        sens_res = tag_info.get('sens_res', 0)
        sel_res = tag_info.get('sel_res', 0)
        
        # 根据SENS_RES和SEL_RES识别标签类型
        if sens_res == 0x0004:
            if sel_res == 0x00:
                return "MIFARE Ultralight"
            elif sel_res == 0x08:
                return "MIFARE Classic 1K"
            elif sel_res == 0x18:
                return "MIFARE Classic 4K"
        
        elif sens_res == 0x0044:
            if sel_res == 0x00:
                return "NTAG213/215/216"
        
        elif sens_res == 0x0002:
            return "MIFARE Ultralight C"
        
        return f"Unknown ISO14443A (SENS_RES: 0x{sens_res:04x}, SEL_RES: 0x{sel_res:02x})"
    
    def test_tag_compatibility(self):
        """
        测试标签兼容性和推荐
        """
        print(f"\n🎯 标签兼容性测试和推荐")
        print(f"=" * 40)
        
        results = self.test_all_protocols()
        
        # 找到成功检测的协议
        successful_protocols = [pid for pid, result in results.items() if result is not None]
        
        print(f"\n📊 测试结果总结:")
        print(f"支持的协议数: {len(successful_protocols)}/{len(self.protocols)}")
        
        if successful_protocols:
            print(f"\n✅ 兼容的协议:")
            for pid in successful_protocols:
                protocol_name = self.protocols[pid]
                tag_info = results[pid]
                
                if pid == 0x00:  # ISO14443A - 详细分析
                    tag_type = self.identify_tag_type(tag_info)
                    print(f"  {protocol_name}: {tag_type}")
                    
                    # 给出建议
                    if "NTAG" in tag_type:
                        print(f"    💡 推荐用于你的项目: 成本低，距离远")
                    elif "MIFARE Classic" in tag_type:
                        print(f"    💡 可用于你的项目: 兼容性好")
                    elif "Ultralight" in tag_type:
                        print(f"    ⚠️  容量较小，但可用")
                else:
                    print(f"  {protocol_name}: 检测成功")
                    print(f"    ⚠️  不推荐用于你的项目")
        
        # 给出购买建议
        print(f"\n🛒 购买建议:")
        if 0x00 in successful_protocols:
            print(f"✅ 你的标签支持ISO14443A - 完美!")
            print(f"📦 推荐购买: NTAG213 (25mm圆形)")
            print(f"💰 价格: ¥2-5/个")
            print(f"📶 预期距离: 12-18cm")
        else:
            print(f"⚠️  当前标签不是ISO14443A")
            print(f"📦 建议更换为: NTAG213标签")
            print(f"🎯 原因: 最佳兼容性和性能")
    
    def compare_protocols(self):
        """
        协议对比分析
        """
        print(f"\n📊 NFC协议对比分析")
        print(f"=" * 50)
        
        comparisons = [
            {
                'protocol': 'ISO14443A',
                'examples': 'NTAG213, MIFARE Classic',
                'distance': '12-18cm',
                'cost': '¥2-8',
                'compatibility': '优秀',
                'recommendation': '强烈推荐'
            },
            {
                'protocol': 'ISO14443B',
                'examples': 'SRT512, Calypso',
                'distance': '5-10cm',
                'cost': '¥8-15',
                'compatibility': '一般',
                'recommendation': '不推荐'
            },
            {
                'protocol': 'FeliCa',
                'examples': 'Sony FeliCa',
                'distance': '8-12cm',
                'cost': '¥15-30',
                'compatibility': '限日系',
                'recommendation': '不推荐'
            }
        ]
        
        print(f"{'协议':<12} {'示例标签':<15} {'距离':<8} {'成本':<8} {'兼容性':<8} {'推荐'}")
        print(f"-" * 65)
        
        for comp in comparisons:
            print(f"{comp['protocol']:<12} {comp['examples']:<15} {comp['distance']:<8} "
                  f"{comp['cost']:<8} {comp['compatibility']:<8} {comp['recommendation']}")
        
        print(f"\n💡 结论:")
        print(f"• ISO14443A是你项目的最佳选择")
        print(f"• NTAG213标签性价比最高")
        print(f"• 避免使用其他协议的标签")

def main():
    """主函数"""
    print("=== NFC协议兼容性测试工具 ===")
    
    tester = ProtocolTester()
    
    if not tester.connect():
        print("❌ 无法连接PN532模块")
        return
    
    try:
        while True:
            print(f"\n📋 请选择测试项目:")
            print(f"1. 测试当前标签的协议兼容性")
            print(f"2. 查看协议对比分析")
            print(f"3. 显示推荐标签类型")
            print(f"4. 退出")
            
            choice = input(f"\n请选择 (1-4): ").strip()
            
            if choice == '1':
                tester.test_tag_compatibility()
            elif choice == '2':
                tester.compare_protocols()
            elif choice == '3':
                tester.show_recommended_tags()
            elif choice == '4':
                break
            else:
                print("❌ 无效选择")
    
    except KeyboardInterrupt:
        print(f"\n⏹️  测试已停止")
    finally:
        tester.stop_monitoring()
    
    def show_recommended_tags(self):
        """显示推荐标签"""
        print(f"\n🎯 推荐标签类型")
        print(f"=" * 30)
        
        recommendations = [
            {
                'name': 'NTAG213',
                'protocol': 'ISO14443A',
                'capacity': '180 bytes',
                'price': '¥2-5',
                'distance': '12-15cm',
                'rating': '⭐⭐⭐⭐⭐',
                'note': '最推荐，性价比最高'
            },
            {
                'name': 'NTAG215',
                'protocol': 'ISO14443A', 
                'capacity': '540 bytes',
                'price': '¥3-8',
                'distance': '10-14cm',
                'rating': '⭐⭐⭐⭐',
                'note': '容量大，略贵'
            },
            {
                'name': 'MIFARE Classic 1K',
                'protocol': 'ISO14443A',
                'capacity': '1024 bytes',
                'price': '¥3-8',
                'distance': '8-12cm',
                'rating': '⭐⭐⭐',
                'note': '兼容性好，距离一般'
            }
        ]
        
        for rec in recommendations:
            print(f"\n📦 {rec['name']} {rec['rating']}")
            print(f"   协议: {rec['protocol']}")
            print(f"   容量: {rec['capacity']}")
            print(f"   价格: {rec['price']}")
            print(f"   距离: {rec['distance']}")
            print(f"   备注: {rec['note']}")

if __name__ == "__main__":
    main() 