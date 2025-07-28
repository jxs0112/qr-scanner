#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头配置文件
用于保存和管理摄像头分辨率偏好设置
"""

import json
import os
from pathlib import Path

class CameraConfig:
    """摄像头配置管理类"""
    
    def __init__(self, config_file='camera_config.json'):
        """
        初始化配置管理器
        
        Args:
            config_file (str): 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告：配置文件加载失败: {e}")
                return self._get_default_config()
        else:
            return self._get_default_config()
    
    def _get_default_config(self):
        """获取默认配置"""
        return {
            'default_resolution': 'medium',
            'default_camera_index': 0,
            'udp_host': '127.0.0.1',
            'udp_port': 8888,
            'send_interval': 1.0,
            'custom_resolutions': {},
            'camera_preferences': {}
        }
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到 {self.config_file}")
        except IOError as e:
            print(f"错误：无法保存配置文件: {e}")
    
    def get_resolution(self, camera_index=None):
        """
        获取摄像头分辨率设置
        
        Args:
            camera_index (int): 摄像头索引
            
        Returns:
            str: 分辨率设置
        """
        if camera_index is not None:
            camera_key = str(camera_index)
            if camera_key in self.config.get('camera_preferences', {}):
                return self.config['camera_preferences'][camera_key].get('resolution', 
                                                                        self.config['default_resolution'])
        
        return self.config['default_resolution']
    
    def set_resolution(self, resolution, camera_index=None):
        """
        设置摄像头分辨率
        
        Args:
            resolution (str): 分辨率设置
            camera_index (int): 摄像头索引
        """
        if camera_index is not None:
            camera_key = str(camera_index)
            if 'camera_preferences' not in self.config:
                self.config['camera_preferences'] = {}
            if camera_key not in self.config['camera_preferences']:
                self.config['camera_preferences'][camera_key] = {}
            
            self.config['camera_preferences'][camera_key]['resolution'] = resolution
        else:
            self.config['default_resolution'] = resolution
    
    def get_camera_index(self):
        """获取默认摄像头索引"""
        return self.config.get('default_camera_index', 0)
    
    def set_camera_index(self, index):
        """设置默认摄像头索引"""
        self.config['default_camera_index'] = index
    
    def get_udp_config(self):
        """获取UDP配置"""
        return {
            'host': self.config.get('udp_host', '127.0.0.1'),
            'port': self.config.get('udp_port', 8888)
        }
    
    def set_udp_config(self, host, port):
        """设置UDP配置"""
        self.config['udp_host'] = host
        self.config['udp_port'] = port
    
    def get_send_interval(self):
        """获取发送间隔"""
        return self.config.get('send_interval', 1.0)
    
    def set_send_interval(self, interval):
        """设置发送间隔"""
        self.config['send_interval'] = interval
    
    def add_custom_resolution(self, name, width, height):
        """
        添加自定义分辨率
        
        Args:
            name (str): 分辨率名称
            width (int): 宽度
            height (int): 高度
        """
        if 'custom_resolutions' not in self.config:
            self.config['custom_resolutions'] = {}
        
        self.config['custom_resolutions'][name] = [width, height]
    
    def get_custom_resolutions(self):
        """获取自定义分辨率"""
        return self.config.get('custom_resolutions', {})
    
    def list_all_resolutions(self):
        """列出所有可用分辨率"""
        from qr_scanner import QRCodeScanner
        
        print("=== 预定义分辨率 ===")
        for name, (width, height) in QRCodeScanner.RESOLUTIONS.items():
            print(f"  {name}: {width}x{height}")
        
        custom = self.get_custom_resolutions()
        if custom:
            print("\n=== 自定义分辨率 ===")
            for name, (width, height) in custom.items():
                print(f"  {name}: {width}x{height}")
    
    def interactive_setup(self):
        """交互式配置设置"""
        print("=== 摄像头配置设置 ===")
        
        # 分辨率设置
        print("\n1. 分辨率设置")
        self.list_all_resolutions()
        
        current_res = self.get_resolution()
        new_res = input(f"请输入默认分辨率 (当前: {current_res}): ").strip()
        if new_res:
            self.set_resolution(new_res)
        
        # 摄像头索引设置
        print("\n2. 摄像头设置")
        current_cam = self.get_camera_index()
        new_cam = input(f"请输入默认摄像头索引 (当前: {current_cam}): ").strip()
        if new_cam:
            try:
                self.set_camera_index(int(new_cam))
            except ValueError:
                print("无效的摄像头索引")
        
        # UDP设置
        print("\n3. UDP设置")
        udp_config = self.get_udp_config()
        new_host = input(f"请输入UDP主机地址 (当前: {udp_config['host']}): ").strip()
        new_port = input(f"请输入UDP端口 (当前: {udp_config['port']}): ").strip()
        
        if new_host or new_port:
            host = new_host if new_host else udp_config['host']
            port = int(new_port) if new_port else udp_config['port']
            self.set_udp_config(host, port)
        
        # 发送间隔设置
        print("\n4. 发送间隔设置")
        current_interval = self.get_send_interval()
        new_interval = input(f"请输入发送间隔(秒) (当前: {current_interval}): ").strip()
        if new_interval:
            try:
                self.set_send_interval(float(new_interval))
            except ValueError:
                print("无效的间隔时间")
        
        # 保存配置
        print("\n5. 保存配置")
        save = input("是否保存配置? (y/n): ").strip().lower()
        if save == 'y':
            self.save_config()
            print("配置已保存！")
        else:
            print("配置未保存")

def main():
    """主函数"""
    import sys
    
    config = CameraConfig()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--setup':
            config.interactive_setup()
        elif sys.argv[1] == '--show':
            print("=== 当前配置 ===")
            print(json.dumps(config.config, indent=2, ensure_ascii=False))
        elif sys.argv[1] == '--reset':
            config.config = config._get_default_config()
            config.save_config()
            print("配置已重置为默认值")
        elif sys.argv[1] == '--help':
            print("摄像头配置管理工具")
            print("\n使用方法:")
            print("  python3 camera_config.py --setup    # 交互式配置")
            print("  python3 camera_config.py --show     # 显示当前配置")
            print("  python3 camera_config.py --reset    # 重置为默认配置")
            print("  python3 camera_config.py --help     # 显示帮助")
        else:
            print("未知参数，使用 --help 查看帮助")
    else:
        config.interactive_setup()

if __name__ == "__main__":
    main() 