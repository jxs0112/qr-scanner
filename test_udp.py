#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP功能测试脚本
"""

import socket
import json
import time
from datetime import datetime

def test_udp_send():
    """测试UDP发送功能"""
    print("=== UDP发送测试 ===")
    
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 测试数据
    test_data = {
        'timestamp': datetime.now().isoformat(),
        'qr_content': '测试二维码内容',
        'source': 'test_script'
    }
    
    try:
        # 发送测试数据
        json_data = json.dumps(test_data, ensure_ascii=False)
        encoded_data = json_data.encode('utf-8')
        
        sock.sendto(encoded_data, ('127.0.0.1', 8888))
        print(f"✓ 测试UDP包发送成功: {test_data['qr_content']}")
        
    except Exception as e:
        print(f"✗ UDP发送失败: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    print("这个脚本会发送一个测试UDP包到 127.0.0.1:8888")
    print("请先在另一个终端运行 udp_receiver.py 来接收测试数据")
    print("按 Enter 继续...")
    input()
    
    test_udp_send()
    print("测试完成！") 