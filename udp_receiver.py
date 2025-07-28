#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP接收器测试程序
用于测试二维码扫描器发送的UDP包
"""

import socket
import json
from datetime import datetime

def udp_receiver(host='127.0.0.1', port=8888):
    """
    UDP接收器
    
    Args:
        host (str): 监听主机地址
        port (int): 监听端口
    """
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 绑定地址和端口
        sock.bind((host, port))
        print(f"=== UDP接收器启动 ===")
        print(f"监听地址: {host}:{port}")
        print(f"等待接收数据... (按 Ctrl+C 退出)")
        print("-" * 50)
        
        while True:
            try:
                # 接收数据
                data, addr = sock.recvfrom(1024)
                
                # 解码JSON数据
                message = json.loads(data.decode('utf-8'))
                
                # 格式化输出
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] 收到来自 {addr[0]}:{addr[1]} 的数据:")
                print(f"  时间戳: {message.get('timestamp', 'N/A')}")
                print(f"  二维码内容: {message.get('qr_content', 'N/A')}")
                print(f"  数据源: {message.get('source', 'N/A')}")
                print("-" * 50)
                
            except json.JSONDecodeError:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 收到非JSON数据: {data}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 接收错误: {e}")
                
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序错误: {e}")
    finally:
        sock.close()
        print("UDP接收器已关闭")

if __name__ == "__main__":
    # 可以在这里修改监听地址和端口
    HOST = '127.0.0.1'
    PORT = 8888
    
    udp_receiver(HOST, PORT) 