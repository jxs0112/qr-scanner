#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版二维码识别程序
专门针对4K分辨率下的性能优化
支持配置文件和多摄像头
"""

import cv2
import socket
import json
import time
import warnings
import logging
import os
from datetime import datetime
from pyzbar import pyzbar
import threading
import queue
import numpy as np

# 设置日志级别，减少zbar的调试输出
logging.getLogger().setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyzbar")

class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "default_resolution": "ultra_hd",
        "default_camera_index": 0,
        "udp_host": "127.0.0.1",
        "udp_port": 8888,
        "send_interval": 1.0,
        "target_fps": 30,
        "debug_mode": False,
        "show_ui": True,  # 是否显示界面
        "custom_resolutions": {},
        "camera_preferences": {},
        "available_cameras": [],
        "performance": {
            "adaptive_skip_interval": 2,
            "detection_region_scale": 0.4,
            "detection_region_custom": {  # 自定义检测区域
                "enabled": False,
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0
            },
            "use_simple_preprocess": True,
            "use_opencv_qr": True,
            "dynamic_resolution": True,
            "detection_scales": [1.0, 0.7, 0.5],
            "min_confidence": 2,
            "cache_ttl": 5
        }
    }
    
    def __init__(self, config_file="camera_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 合并默认配置和加载的配置
                config = self.DEFAULT_CONFIG.copy()
                self._merge_dict(config, loaded_config)
                
                print(f"✓ 已加载配置文件: {self.config_file}")
                return config
            else:
                print(f"⚠️  配置文件不存在，使用默认配置")
                return self.DEFAULT_CONFIG.copy()
                
        except Exception as e:
            print(f"⚠️  加载配置文件失败: {e}")
            print("使用默认配置")
            return self.DEFAULT_CONFIG.copy()
    
    def _merge_dict(self, base_dict, update_dict):
        """递归合并字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._merge_dict(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✓ 配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"⚠️  保存配置失败: {e}")
    
    def get(self, key, default=None):
        """获取配置值，支持点分隔的键"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key, value):
        """设置配置值，支持点分隔的键"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def detect_available_cameras(self):
        """检测可用的摄像头"""
        available_cameras = []
        print("🔍 正在检测可用摄像头...")
        
        for i in range(10):  # 检测前10个摄像头索引
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 获取摄像头信息
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                backend = cap.getBackendName()
                
                camera_info = {
                    "index": i,
                    "resolution": f"{width}x{height}",
                    "fps": fps,
                    "backend": backend,
                    "name": f"Camera {i}"
                }
                
                available_cameras.append(camera_info)
                print(f"  ✓ 摄像头 {i}: {width}x{height} @ {fps:.1f}fps ({backend})")
                cap.release()
            else:
                cap.release()
        
        if not available_cameras:
            print("  ⚠️  未检测到可用摄像头")
        else:
            print(f"  📷 共检测到 {len(available_cameras)} 个摄像头")
        
        self.config["available_cameras"] = available_cameras
        return available_cameras

class OptimizedQRCodeScanner:
    # 预定义的分辨率选项
    RESOLUTIONS = {
        'low': (320, 240),
        'medium': (640, 480),
        'high': (1280, 720),
        'full_hd': (1920, 1080),
        'ultra_hd': (3840, 2160)
    }
    
    def __init__(self, udp_host=None, udp_port=None, resolution=None, 
                 camera_index=None, debug_mode=None, target_fps=None, config_file="camera_config.json"):
        """
        初始化优化版二维码扫描器
        参数可以从配置文件加载，命令行参数会覆盖配置文件设置
        """
        # 初始化配置管理器
        self.config_manager = ConfigManager(config_file)
        
        # 从配置文件获取默认值，命令行参数优先
        self.udp_host = udp_host or self.config_manager.get('udp_host')
        self.udp_port = udp_port or self.config_manager.get('udp_port')
        self.debug_mode = debug_mode if debug_mode is not None else self.config_manager.get('debug_mode')
        self.target_fps = target_fps or self.config_manager.get('target_fps')
        self.show_ui = self.config_manager.get('show_ui', True)  # 是否显示界面
        
        # 摄像头索引处理
        camera_index = camera_index if camera_index is not None else self.config_manager.get('default_camera_index')
        
        # 分辨率处理
        if resolution is None:
            resolution = self.config_manager.get('default_resolution')
        
        # 初始化socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_qr_data = None
        self.last_send_time = 0
        self.send_interval = self.config_manager.get('send_interval')
        
        # 从配置文件加载性能参数
        perf_config = self.config_manager.get('performance', {})
        self.frame_skip_count = 0
        self.adaptive_skip_interval = perf_config.get('adaptive_skip_interval', 2)
        self.detection_region_scale = perf_config.get('detection_region_scale', 0.4)
        
        # 自定义检测区域
        detection_region_custom = perf_config.get('detection_region_custom', {})
        self.detection_region_custom_enabled = detection_region_custom.get('enabled', False)
        self.detection_region_custom_x = detection_region_custom.get('x', 0)
        self.detection_region_custom_y = detection_region_custom.get('y', 0)
        self.detection_region_custom_width = detection_region_custom.get('width', 0)
        self.detection_region_custom_height = detection_region_custom.get('height', 0)
        
        self.use_simple_preprocess = perf_config.get('use_simple_preprocess', True)
        self.use_opencv_qr = perf_config.get('use_opencv_qr', True)
        self.dynamic_resolution = perf_config.get('dynamic_resolution', True)
        
        # 摄像头控制参数（仅显示，macOS AVFOUNDATION后端不支持软件控制）
        self.camera_backend = "unknown"
        self.supports_manual_control = False
        self.show_camera_warning = True
        
        # 性能监控
        self.fps_history = []
        self.performance_check_interval = 60
        self.target_min_fps = 15
        
        # 多尺度检测
        self.detection_scales = perf_config.get('detection_scales', [1.0, 0.7, 0.5])
        self.current_scale_index = 0
        
        # 识别稳定性跟踪
        self.qr_confidence = {}
        self.min_confidence = perf_config.get('min_confidence', 2)
        self.frame_count = 0
        
        # 预编译正则表达式
        import re
        self.url_pattern = re.compile(r'https?://[^\s]+')
        
        # OpenCV QR检测器初始化
        self.cv_qr_detector = cv2.QRCodeDetector()
        
        # 缓存最近的检测结果
        self.detection_cache = {}
        self.cache_ttl = perf_config.get('cache_ttl', 5)
        
        # 解析分辨率设置
        custom_resolutions = self.config_manager.get('custom_resolutions', {})
        all_resolutions = {**self.RESOLUTIONS, **custom_resolutions}
        
        if isinstance(resolution, str):
            if resolution in all_resolutions:
                self.width, self.height = all_resolutions[resolution]
            else:
                print(f"警告：未知的分辨率设置 '{resolution}'，使用默认分辨率")
                self.width, self.height = self.RESOLUTIONS['ultra_hd']
        elif isinstance(resolution, tuple) and len(resolution) == 2:
            self.width, self.height = resolution
        else:
            print(f"警告：无效的分辨率格式，使用默认分辨率")
            self.width, self.height = self.RESOLUTIONS['ultra_hd']
        
        # 检测可用摄像头
        available_cameras = self.config_manager.detect_available_cameras()
        
        # 验证摄像头索引
        if available_cameras:
            available_indices = [cam['index'] for cam in available_cameras]
            if camera_index not in available_indices:
                print(f"⚠️  指定的摄像头索引 {camera_index} 不可用")
                print(f"可用摄像头: {available_indices}")
                camera_index = available_indices[0]
                print(f"使用摄像头: {camera_index}")
                # 更新配置文件
                self.config_manager.set('default_camera_index', camera_index)
        
        # 初始化摄像头
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_index}")
        
        # 保存当前摄像头索引
        self.current_camera_index = camera_index
        
        # 检测摄像头能力并优化设置
        self.detect_camera_capabilities()
        self.optimize_camera_settings()
        
        # 获取实际设置
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # 保存摄像头信息到配置
        camera_info = {
            "index": camera_index,
            "resolution": f"{actual_width}x{actual_height}",
            "fps": actual_fps,
            "backend": self.camera_backend
        }
        self.config_manager.set(f'camera_preferences.camera_{camera_index}', camera_info)
        
        print(f"优化版二维码扫描器已初始化")
        print(f"UDP目标: {self.udp_host}:{self.udp_port}")
        print(f"使用摄像头: {camera_index}")
        print(f"实际分辨率: {actual_width}x{actual_height}")
        print(f"实际帧率: {actual_fps:.1f} FPS")
        print(f"摄像头后端: {self.camera_backend}")
        print(f"配置文件: {self.config_manager.config_file}")
        print(f"高级性能优化:")
        print(f"  - 自适应跳帧: 初始每{self.adaptive_skip_interval + 1}帧检测一次")
        print(f"  - 检测区域: 中心{self.detection_region_scale*100:.0f}%区域")
        print(f"  - OpenCV QR检测: {'开启' if self.use_opencv_qr else '关闭'}")
        print(f"  - 动态优化: {'开启' if self.dynamic_resolution else '关闭'}")
        print(f"  - 多尺度检测: {len(self.detection_scales)}个尺度")
        print(f"  - 结果缓存: {self.cache_ttl}帧TTL")
        
        if not self.supports_manual_control and self.show_camera_warning:
            print(f"⚠️  摄像头控制限制:")
            print(f"  - macOS不允许软件直接控制摄像头参数")
            print(f"  - 建议使用系统相机应用预先调整设置")
            print(f"  - 或在摄像头设置软件中配置")
        
        print(f"按 'q' 键退出程序")
    
    def detect_camera_capabilities(self):
        """
        检测摄像头能力
        """
        # 获取后端信息
        self.camera_backend = self.cap.getBackendName()
        
        # 检测是否支持手动控制
        if self.camera_backend == "AVFOUNDATION":
            self.supports_manual_control = False
            print(f"🔍 检测到macOS AVFOUNDATION后端 - 软件控制受限")
        else:
            # 简单测试是否支持控制
            original_focus = self.cap.get(cv2.CAP_PROP_FOCUS)
            self.cap.set(cv2.CAP_PROP_FOCUS, original_focus + 1)
            time.sleep(0.1)
            new_focus = self.cap.get(cv2.CAP_PROP_FOCUS)
            self.supports_manual_control = abs(new_focus - (original_focus + 1)) < 0.1
            self.cap.set(cv2.CAP_PROP_FOCUS, original_focus)  # 恢复原值
    
    def optimize_camera_settings(self):
        """优化摄像头设置"""
        # 基本设置
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if self.supports_manual_control:
            print("🔧 应用摄像头手动设置...")
            try:
                # 编码格式设置
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                
                # 其他可能的优化设置
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 手动曝光
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # 禁用自动对焦
                
                print("   ✓ 手动控制设置已应用")
                
            except Exception as e:
                print(f"   ⚠️ 部分设置可能不被支持: {e}")
        else:
            print("🔧 应用基本优化设置...")
            try:
                # 只设置基本参数
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                print("   ✓ 基本设置已应用")
            except Exception as e:
                print(f"   ⚠️ 设置可能不被支持: {e}")
        
        # 等待设置生效
        time.sleep(0.3)
    
    def show_camera_info(self):
        """
        显示摄像头信息
        """
        print(f"\n📋 当前摄像头信息:")
        print(f"  后端: {self.camera_backend}")
        print(f"  分辨率: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        print(f"  帧率: {self.cap.get(cv2.CAP_PROP_FPS):.1f} FPS")
        print(f"  手动控制: {'支持' if self.supports_manual_control else '不支持'}")
        
        if not self.supports_manual_control:
            print(f"\n💡 优化建议:")
            print(f"  1. 在系统相机应用中调整摄像头设置")
            print(f"  2. 确保光线充足，减少自动调整")
            print(f"  3. 保持摄像头与QR码的固定距离")
            print(f"  4. 避免手抖，使用三脚架固定")
        
        print()
    
    def show_performance_tips(self):
        """
        显示性能优化提示
        """
        print(f"\n🚀 性能优化提示:")
        print(f"  - 当前检测区域: {self.detection_region_scale*100:.0f}%")
        print(f"  - 跳帧间隔: 每{self.adaptive_skip_interval + 1}帧检测一次")
        print(f"  - OpenCV检测: {'开启' if self.use_opencv_qr else '关闭'}")
        print(f"  - 自适应优化: {'开启' if self.dynamic_resolution else '关闭'}")
        print(f"  - 缓存大小: {len(self.detection_cache)}项")
        print()
    
    def adaptive_performance_adjust(self, current_fps):
        """
        自适应性能调整
        """
        if len(self.fps_history) >= self.performance_check_interval:
            avg_fps = sum(self.fps_history[-30:]) / min(30, len(self.fps_history))
            
            if avg_fps < self.target_min_fps:
                # 性能不足，增加优化
                if self.adaptive_skip_interval < 4:
                    self.adaptive_skip_interval += 1
                    print(f"📉 性能优化: 跳帧间隔调整为 {self.adaptive_skip_interval}")
                
                if self.detection_region_scale > 0.3:
                    self.detection_region_scale = max(0.3, self.detection_region_scale - 0.1)
                    print(f"📉 性能优化: 检测区域调整为 {self.detection_region_scale*100:.0f}%")
                
            elif avg_fps > self.target_min_fps * 1.5:
                # 性能充足，可以提升质量
                if self.adaptive_skip_interval > 1:
                    self.adaptive_skip_interval -= 1
                    print(f"📈 质量提升: 跳帧间隔调整为 {self.adaptive_skip_interval}")
                
                if self.detection_region_scale < 0.8:
                    self.detection_region_scale = min(0.8, self.detection_region_scale + 0.1)
                    print(f"📈 质量提升: 检测区域调整为 {self.detection_region_scale*100:.0f}%")
            
            # 清理历史记录
            self.fps_history = self.fps_history[-30:]
    
    def get_detection_region(self, frame):
        """
        获取检测区域（中心区域，减少计算量）
        支持自定义区域设置
        """
        h, w = frame.shape[:2]
        
        if self.detection_region_custom_enabled:
            # 使用自定义区域
            x = self.detection_region_custom_x
            y = self.detection_region_custom_y
            width = self.detection_region_custom_width
            height = self.detection_region_custom_height
            
            # 如果宽高为0，则使用整个图像宽高
            if width <= 0:
                width = w
            if height <= 0:
                height = h
                
            # 确保区域在图像范围内
            x = max(0, min(x, w - 10))
            y = max(0, min(y, h - 10))
            width = min(width, w - x)
            height = min(height, h - y)
            
            # 裁剪区域
            region = frame[y:y + height, x:x + width]
            return region, (x, y)
        else:
            # 计算中心区域
            center_w = int(w * self.detection_region_scale)
            center_h = int(h * self.detection_region_scale)
            
            # 计算起始位置
            start_x = (w - center_w) // 2
            start_y = (h - center_h) // 2
            
            # 裁剪区域
            region = frame[start_y:start_y + center_h, start_x:start_x + center_w]
            
            return region, (start_x, start_y)
    
    def get_scaled_region(self, frame, scale=1.0):
        """
        获取缩放后的检测区域
        """
        if scale == 1.0:
            return self.get_detection_region(frame)
        
        h, w = frame.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        
        # 缩放图像
        scaled_frame = cv2.resize(frame, (new_w, new_h))
        
        # 获取检测区域
        region, offset = self.get_detection_region(scaled_frame)
        
        # 调整偏移量
        adjusted_offset = (int(offset[0] / scale), int(offset[1] / scale))
        
        return region, adjusted_offset, scale
    
    def detect_qr_opencv(self, frame):
        """
        使用OpenCV的QR检测器（通常比pyzbar更快）
        """
        detected_qrs = []
        try:
            # OpenCV QR检测
            data, bbox, rectified_image = self.cv_qr_detector.detectAndDecode(frame)
            
            if data:
                # 转换边界框格式
                if bbox is not None and len(bbox) > 0:
                    points = bbox[0].astype(int)
                    
                    # 计算矩形边界
                    x = int(np.min(points[:, 0]))
                    y = int(np.min(points[:, 1]))
                    w = int(np.max(points[:, 0]) - x)
                    h = int(np.max(points[:, 1]) - y)
                    
                    # 模拟pyzbar的矩形格式
                    rect = type('Rect', (), {
                        'left': x, 'top': y, 'width': w, 'height': h
                    })()
                    
                    detected_qrs.append({
                        'data': data,
                        'rect': rect,
                        'polygon': [(int(p[0]), int(p[1])) for p in points],
                        'method': 'opencv'
                    })
        except Exception as e:
            pass
        
        return detected_qrs
    
    def detect_qr_pyzbar(self, frame):
        """
        使用pyzbar检测QR码（备用方法）
        """
        detected_qrs = []
        try:
            import os
            from contextlib import redirect_stderr
            from io import StringIO
            
            f = StringIO()
            with redirect_stderr(f):
                detected_codes = pyzbar.decode(frame, symbols=[pyzbar.ZBarSymbol.QRCODE])
            
            for qr_code in detected_codes:
                qr_data = qr_code.data.decode('utf-8')
                detected_qrs.append({
                    'data': qr_data,
                    'rect': qr_code.rect,
                    'polygon': [(p[0], p[1]) for p in qr_code.polygon],
                    'method': 'pyzbar'
                })
        except Exception as e:
            pass
        
        return detected_qrs
    
    def preprocess_frame_optimized(self, frame):
        """
        优化的预处理方法 - 只使用最有效的几种
        """
        processed_frames = []
        
        if self.use_simple_preprocess:
            # 简化版：只使用最必要的预处理
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            processed_frames.append(gray)
            
            # 自适应阈值（最有效的一种）
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY, 21, 10)
            processed_frames.append(adaptive)
        else:
            # 标准版：包含更多预处理方法
            processed_frames.append(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            processed_frames.append(gray)
            
            # 自适应阈值
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY, 21, 10)
            processed_frames.append(adaptive)
            
            # Otsu阈值
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_frames.append(otsu)
        
        return processed_frames
    
    def detect_qr_in_region(self, processed_frames, offset=(0, 0), scale=1.0):
        """
        在指定区域检测QR码（支持多种检测方法）
        """
        detected_qr_codes = []
        offset_x, offset_y = offset
        
        # 1. 优先使用OpenCV检测器（如果启用）
        if self.use_opencv_qr and len(processed_frames) > 0:
            opencv_results = self.detect_qr_opencv(processed_frames[0])
            for qr in opencv_results:
                # 调整坐标
                adjusted_rect = type('Rect', (), {
                    'left': int(qr['rect'].left / scale) + offset_x,
                    'top': int(qr['rect'].top / scale) + offset_y,
                    'width': int(qr['rect'].width / scale),
                    'height': int(qr['rect'].height / scale)
                })()
                
                detected_qr_codes.append({
                    'data': qr['data'],
                    'rect': adjusted_rect,
                    'polygon': [(int(p[0]/scale) + offset_x, int(p[1]/scale) + offset_y) for p in qr['polygon']],
                    'method': 'opencv'
                })
        
        # 2. 如果OpenCV没有检测到，使用pyzbar作为备用
        if not detected_qr_codes:
            for i, processed_frame in enumerate(processed_frames):
                pyzbar_results = self.detect_qr_pyzbar(processed_frame)
                for qr in pyzbar_results:
                    # 检查是否已经存在
                    if not any(existing['data'] == qr['data'] for existing in detected_qr_codes):
                        # 调整坐标
                        adjusted_rect = type('Rect', (), {
                            'left': int(qr['rect'].left / scale) + offset_x,
                            'top': int(qr['rect'].top / scale) + offset_y,
                            'width': int(qr['rect'].width / scale),
                            'height': int(qr['rect'].height / scale)
                        })()
                        
                        detected_qr_codes.append({
                            'data': qr['data'],
                            'rect': adjusted_rect,
                            'polygon': [(int(p[0]/scale) + offset_x, int(p[1]/scale) + offset_y) for p in qr['polygon']],
                            'method': f'pyzbar_{i}'
                        })
        
        return detected_qr_codes
    
    def check_detection_cache(self, frame_hash):
        """
        检查检测缓存
        """
        current_frame = self.frame_count
        
        # 清理过期缓存
        expired_keys = []
        for key, (cached_frame, result) in self.detection_cache.items():
            if current_frame - cached_frame > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.detection_cache[key]
        
        # 检查当前帧
        if frame_hash in self.detection_cache:
            cached_frame, result = self.detection_cache[frame_hash]
            if current_frame - cached_frame <= self.cache_ttl:
                return result
        
        return None
    
    def cache_detection_result(self, frame_hash, result):
        """
        缓存检测结果
        """
        self.detection_cache[frame_hash] = (self.frame_count, result)
    
    def send_udp_packet(self, qr_data):
        """发送UDP包"""
        try:
            packet_data = {
                'timestamp': datetime.now().isoformat(),
                'qr_content': qr_data,
                'source': 'optimized_qr_scanner_v2'
            }
            
            json_data = json.dumps(packet_data, ensure_ascii=False)
            encoded_data = json_data.encode('utf-8')
            
            self.socket.sendto(encoded_data, (self.udp_host, self.udp_port))
            print(f"✓ UDP包已发送: {qr_data}")
            
        except Exception as e:
            print(f"✗ UDP发送失败: {e}")
    
    def process_frame(self, frame):
        """
        处理单帧图像（高级优化版本）
        """
        self.frame_count += 1
        
        # 跳帧优化：自适应跳帧间隔
        if self.frame_skip_count < self.adaptive_skip_interval:
            self.frame_skip_count += 1
            return frame
        
        self.frame_skip_count = 0
        
        # 计算帧哈希用于缓存
        frame_hash = hash(frame.tobytes()[::1000])  # 简化哈希，只采样部分数据
        
        # 检查缓存
        cached_result = self.check_detection_cache(frame_hash)
        if cached_result is not None:
            detected_qr_codes = cached_result
        else:
            # 多尺度检测
            detected_qr_codes = []
            
            for scale in self.detection_scales:
                if scale == 1.0:
                    detection_region, offset = self.get_detection_region(frame)
                    scale_factor = 1.0
                else:
                    detection_region, offset, scale_factor = self.get_scaled_region(frame, scale)
                
                # 预处理
                processed_frames = self.preprocess_frame_optimized(detection_region)
                
                # QR检测
                scale_results = self.detect_qr_in_region(processed_frames, offset, scale_factor)
                
                # 如果找到了QR码，就停止继续尝试其他尺度
                if scale_results:
                    detected_qr_codes.extend(scale_results)
                    break
            
            # 缓存结果
            self.cache_detection_result(frame_hash, detected_qr_codes)
        
        # 更新置信度
        current_qr_data = set(qr['data'] for qr in detected_qr_codes)
        
        for qr_data in current_qr_data:
            if qr_data in self.qr_confidence:
                self.qr_confidence[qr_data] += 1
            else:
                self.qr_confidence[qr_data] = 1
        
        # 减少未检测到的二维码的信心度
        for qr_data in list(self.qr_confidence.keys()):
            if qr_data not in current_qr_data:
                self.qr_confidence[qr_data] = max(0, self.qr_confidence[qr_data] - 1)
                if self.qr_confidence[qr_data] == 0:
                    del self.qr_confidence[qr_data]
        
        # 处理检测到的二维码
        for qr_info in detected_qr_codes:
            qr_data = qr_info['data']
            current_time = time.time()
            
            confidence = self.qr_confidence.get(qr_data, 0)
            should_send = (
                confidence >= self.min_confidence and
                (qr_data != self.last_qr_data or current_time - self.last_send_time > self.send_interval)
            )
            
            if should_send:
                self.send_udp_packet(qr_data)
                self.last_qr_data = qr_data
                self.last_send_time = current_time
                print(f"✓ 检测成功 (信心度: {confidence}, 方法: {qr_info.get('method', 'unknown')})")
            
            # 绘制边框
            points = qr_info['polygon']
            if len(points) > 4:
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                points = hull
            
            points = np.array(points, dtype=np.int32)
            
            # 根据信心度和检测方法改变颜色
            if confidence >= self.min_confidence:
                color = (0, 255, 0)  # 绿色
            else:
                color = (0, 255, 255)  # 黄色
            
            cv2.polylines(frame, [points], True, color, 2)
            
            # 添加文本（包含检测方法）
            rect = qr_info['rect']
            method = qr_info.get('method', 'unknown')
            label = f"{qr_data[:15]}... ({confidence})[{method}]" if len(qr_data) > 15 else f"{qr_data} ({confidence})[{method}]"
            cv2.putText(frame, label, (rect.left, rect.top - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # 绘制检测区域边框
        if self.debug_mode:
            h, w = frame.shape[:2]
            
            if self.detection_region_custom_enabled:
                # 绘制自定义检测区域
                x = self.detection_region_custom_x
                y = self.detection_region_custom_y
                width = self.detection_region_custom_width if self.detection_region_custom_width > 0 else w
                height = self.detection_region_custom_height if self.detection_region_custom_height > 0 else h
                
                # 确保区域在图像范围内
                x = max(0, min(x, w - 10))
                y = max(0, min(y, h - 10))
                width = min(width, w - x)
                height = min(height, h - y)
                
                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 255), 2)
                cv2.putText(frame, f"Custom Region ({width}x{height})", 
                           (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                # 绘制中心检测区域
                center_w = int(w * self.detection_region_scale)
                center_h = int(h * self.detection_region_scale)
                start_x = (w - center_w) // 2
                start_y = (h - center_h) // 2
                
                cv2.rectangle(frame, (start_x, start_y), 
                             (start_x + center_w, start_y + center_h), 
                             (255, 0, 0), 2)
                cv2.putText(frame, f"Detection Region ({self.detection_region_scale*100:.0f}%)", 
                           (start_x, start_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        return frame
    
    def switch_camera(self, direction='next'):
        """切换摄像头"""
        available_cameras = self.config_manager.get('available_cameras', [])
        if len(available_cameras) <= 1:
            print("⚠️  只有一个摄像头可用，无法切换")
            return
        
        current_index = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))  # 获取当前摄像头索引的替代方法
        current_camera_info = None
        
        # 找到当前摄像头在列表中的位置
        for i, cam in enumerate(available_cameras):
            if cam['index'] == getattr(self, 'current_camera_index', 0):
                current_camera_info = cam
                current_pos = i
                break
        else:
            current_pos = 0
        
        # 计算新的摄像头位置
        if direction == 'next':
            new_pos = (current_pos + 1) % len(available_cameras)
        else:  # prev
            new_pos = (current_pos - 1) % len(available_cameras)
        
        new_camera = available_cameras[new_pos]
        new_camera_index = new_camera['index']
        
        print(f"🔄 切换摄像头: {getattr(self, 'current_camera_index', 0)} -> {new_camera_index}")
        
        # 释放当前摄像头
        self.cap.release()
        
        # 打开新摄像头
        self.cap = cv2.VideoCapture(new_camera_index)
        if not self.cap.isOpened():
            print(f"❌ 无法打开摄像头 {new_camera_index}")
            # 回退到原摄像头
            self.cap = cv2.VideoCapture(getattr(self, 'current_camera_index', 0))
            return
        
        # 更新当前摄像头索引
        self.current_camera_index = new_camera_index
        
        # 重新优化设置
        self.detect_camera_capabilities()
        self.optimize_camera_settings()
        
        # 更新配置
        self.config_manager.set('default_camera_index', new_camera_index)
        
        # 显示新摄像头信息
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"✓ 摄像头切换成功:")
        print(f"  索引: {new_camera_index}")
        print(f"  分辨率: {actual_width}x{actual_height}")
        print(f"  帧率: {actual_fps:.1f} FPS")
        print(f"  后端: {self.camera_backend}")
    
    def list_cameras(self):
        """列出所有可用摄像头"""
        available_cameras = self.config_manager.get('available_cameras', [])
        
        if not available_cameras:
            print("⚠️  未检测到可用摄像头")
            return
        
        print(f"\n📷 可用摄像头列表:")
        current_index = getattr(self, 'current_camera_index', self.config_manager.get('default_camera_index'))
        
        for i, cam in enumerate(available_cameras):
            marker = "👉" if cam['index'] == current_index else "  "
            print(f"{marker} 摄像头 {cam['index']}: {cam['resolution']} @ {cam['fps']:.1f}fps ({cam['backend']})")
        
        print(f"\n💡 使用 'n'/'p' 键切换摄像头")
        print()
    
    def save_current_config(self):
        """保存当前配置到文件"""
        # 更新性能配置
        perf_config = {
            'adaptive_skip_interval': self.adaptive_skip_interval,
            'detection_region_scale': self.detection_region_scale,
            'detection_region_custom': {
                'enabled': self.detection_region_custom_enabled,
                'x': self.detection_region_custom_x,
                'y': self.detection_region_custom_y,
                'width': self.detection_region_custom_width,
                'height': self.detection_region_custom_height
            },
            'use_simple_preprocess': self.use_simple_preprocess,
            'use_opencv_qr': self.use_opencv_qr,
            'dynamic_resolution': self.dynamic_resolution,
            'detection_scales': self.detection_scales,
            'min_confidence': self.min_confidence,
            'cache_ttl': self.cache_ttl
        }
        
        self.config_manager.set('performance', perf_config)
        self.config_manager.set('send_interval', self.send_interval)
        self.config_manager.set('debug_mode', self.debug_mode)
        self.config_manager.set('show_ui', self.show_ui)
        
        # 保存当前摄像头索引
        current_index = getattr(self, 'current_camera_index', self.config_manager.get('default_camera_index'))
        self.config_manager.set('default_camera_index', current_index)
        
        self.config_manager.save_config()
        print("✓ 当前配置已保存")

    def run(self):
        """运行扫描器"""
        fps_counter = 0
        fps_start_time = time.time()
        last_fps_time = time.time()
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("无法读取摄像头数据")
                    break
                
                # 处理帧
                frame = self.process_frame(frame)
                
                # 根据配置决定是否显示界面
                if self.show_ui:
                    # 显示
                    cv2.imshow('Optimized QR Scanner V2', frame)
                    
                    # 按键处理
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('d'):
                        self.debug_mode = not self.debug_mode
                        print(f"调试模式: {'开启' if self.debug_mode else '关闭'}")
                    elif key == ord('s'):  # 切换简化预处理
                        self.use_simple_preprocess = not self.use_simple_preprocess
                        print(f"简化预处理: {'开启' if self.use_simple_preprocess else '关闭'}")
                    elif key == ord('o'):  # 切换OpenCV检测器
                        self.use_opencv_qr = not self.use_opencv_qr
                        print(f"OpenCV检测器: {'开启' if self.use_opencv_qr else '关闭'}")
                    elif key == ord('a'):  # 切换自适应优化
                        self.dynamic_resolution = not self.dynamic_resolution
                        print(f"自适应优化: {'开启' if self.dynamic_resolution else '关闭'}")
                    elif key == ord('r'):  # 调整检测区域
                        if self.detection_region_scale == 0.5:
                            self.detection_region_scale = 0.7
                        elif self.detection_region_scale == 0.7:
                            self.detection_region_scale = 1.0
                        else:
                            self.detection_region_scale = 0.5
                        print(f"检测区域: {self.detection_region_scale*100:.0f}%")
                    elif key == ord('t'):  # 切换自定义检测区域
                        self.detection_region_custom_enabled = not self.detection_region_custom_enabled
                        print(f"自定义检测区域: {'启用' if self.detection_region_custom_enabled else '禁用'}")
                        if self.detection_region_custom_enabled:
                            print(f"  位置: ({self.detection_region_custom_x}, {self.detection_region_custom_y}), "
                                  f"大小: {self.detection_region_custom_width}x{self.detection_region_custom_height}")
                    elif key == ord('c'):  # 清除缓存
                        self.detection_cache.clear()
                        print("缓存已清除")
                    elif key == ord('i'):  # 显示摄像头信息
                        self.show_camera_info()
                    elif key == ord('h'):  # 显示性能提示
                        self.show_performance_tips()
                    elif key == ord('w'):  # 切换警告显示
                        self.show_camera_warning = not self.show_camera_warning
                        print(f"摄像头警告: {'显示' if self.show_camera_warning else '隐藏'}")
                    elif key == ord('n'):  # 切换到下一个摄像头
                        self.switch_camera('next')
                    elif key == ord('p'):  # 切换到上一个摄像头
                        self.switch_camera('prev')
                    elif key == ord('l'):  # 列出可用摄像头
                        self.list_cameras()
                    elif key == ord('z'):  # 保存当前配置
                        self.save_current_config()
                    elif key == ord('x'):  # 重新检测摄像头
                        self.config_manager.detect_available_cameras()
                        self.config_manager.save_config()
                        print("摄像头检测完成并保存到配置文件")
                    elif key == ord('u'):  # 切换UI显示
                        self.show_ui = not self.show_ui
                        print(f"界面显示: {'开启' if self.show_ui else '关闭'}")
                        if not self.show_ui:
                            cv2.destroyAllWindows()
                            print("界面已关闭，程序继续在后台运行")
                            print("按Ctrl+C中断程序")
                else:
                    # 无界面模式下，增加短暂延时避免CPU占用过高
                    time.sleep(0.001)
                    
                    # 检查是否有中断信号
                    import select
                    import sys
                    # 检查stdin是否有输入，非阻塞方式
                    if select.select([sys.stdin], [], [], 0)[0]:
                        cmd = sys.stdin.readline().strip()
                        if cmd == 'q':
                            break
                
                # FPS计算和性能监控
                fps_counter += 1
                current_time = time.time()
                
                if current_time - last_fps_time >= 1.0:  # 每秒计算一次FPS
                    current_fps = fps_counter / (current_time - fps_start_time) * fps_counter / fps_counter
                    self.fps_history.append(current_fps)
                    
                    if fps_counter % 30 == 0:
                        print(f"当前FPS: {current_fps:.1f}, 缓存命中: {len(self.detection_cache)}")
                    
                    # 自适应性能调整
                    if self.dynamic_resolution and fps_counter % self.performance_check_interval == 0:
                        self.adaptive_performance_adjust(current_fps)
                    
                    last_fps_time = current_time
                    
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        except Exception as e:
            print(f"程序运行错误: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        print("正在清理资源...")
        self.cap.release()
        if self.show_ui:
            cv2.destroyAllWindows()
        self.socket.close()
        print("资源清理完成")

    def set_custom_detection_region(self, x, y, width, height, enabled=True):
        """
        设置自定义检测区域
        
        参数:
            x, y: 区域左上角坐标
            width, height: 区域宽高
            enabled: 是否启用自定义区域
        """
        self.detection_region_custom_enabled = enabled
        self.detection_region_custom_x = x
        self.detection_region_custom_y = y
        self.detection_region_custom_width = width
        self.detection_region_custom_height = height
        
        print(f"✓ 已设置检测区域: {'启用' if enabled else '禁用'}")
        if enabled:
            print(f"  位置: ({x}, {y}), 大小: {width}x{height}")
        
        # 自动保存配置
        self.save_current_config()

def main():
    """主函数"""
    import sys
    
    print("=== 高级优化版二维码识别程序 ===")
    print("优化功能:")
    print("  - 配置文件支持和自动保存")
    print("  - 多摄像头检测和切换")
    print("  - 自适应跳帧和区域调整")
    print("  - OpenCV + pyzbar双重检测")
    print("  - 多尺度检测")
    print("  - 智能结果缓存")
    print("  - 实时性能监控")
    print("\n基本控制:")
    print("  q: 退出程序")
    print("  d: 切换调试模式")
    print("  s: 切换简化预处理")
    print("  o: 切换OpenCV检测器")
    print("  a: 切换自适应优化")
    print("  r: 调整检测区域大小")
    print("  t: 切换自定义检测区域")
    print("  c: 清除检测缓存")
    print("  u: 切换界面显示")
    print("\n摄像头控制:")
    print("  n: 切换到下一个摄像头")
    print("  p: 切换到上一个摄像头")
    print("  l: 列出所有可用摄像头")
    print("  x: 重新检测摄像头")
    print("\n信息和配置:")
    print("  i: 显示摄像头信息")
    print("  h: 显示性能提示")
    print("  w: 切换警告显示")
    print("  z: 保存当前配置到文件")
    
    # 解析参数
    resolution = None
    camera_index = None
    debug_mode = None
    target_fps = None
    config_file = "camera_config.json"
    show_ui = None
    detection_region = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--debug':
            debug_mode = True
            args.pop(i)
        elif args[i] == '--no-ui':
            show_ui = False
            args.pop(i)
        elif args[i].startswith('--region='):
            try:
                region_str = args[i].replace('--region=', '')
                # 格式: x,y,width,height
                parts = [int(p) for p in region_str.split(',')]
                if len(parts) == 4:
                    detection_region = {
                        'enabled': True,
                        'x': parts[0],
                        'y': parts[1],
                        'width': parts[2],
                        'height': parts[3]
                    }
                else:
                    print(f"警告：无效的检测区域格式，应为 x,y,width,height")
                args.pop(i)
            except ValueError:
                print(f"警告：无效的检测区域格式")
                i += 1
        elif args[i].startswith('--fps='):
            try:
                target_fps = int(args[i].replace('--fps=', ''))
                args.pop(i)
            except ValueError:
                print(f"警告：无效的目标帧率")
                i += 1
        elif args[i].startswith('--config='):
            config_file = args[i].replace('--config=', '')
            args.pop(i)
        elif args[i].startswith('--camera='):
            try:
                camera_index = int(args[i].replace('--camera=', ''))
                args.pop(i)
            except ValueError:
                print(f"警告：无效的摄像头索引")
                i += 1
        else:
            i += 1
    
    # 剩余参数作为分辨率
    if len(args) > 0:
        resolution = args[0]
    if len(args) > 1 and camera_index is None:
        try:
            camera_index = int(args[1])
        except ValueError:
            print(f"警告：无效的摄像头索引")
    
    UDP_HOST = None  # 从配置文件读取
    UDP_PORT = None  # 从配置文件读取
    
    print(f"\n配置文件: {config_file}")
    
    try:
        # 先加载配置文件
        config_manager = ConfigManager(config_file)
        
        # 如果命令行指定了检测区域，更新配置
        if detection_region:
            config_manager.set('performance.detection_region_custom', detection_region)
            config_manager.save_config()
            print(f"✓ 已更新检测区域设置: x={detection_region['x']}, y={detection_region['y']}, "
                  f"width={detection_region['width']}, height={detection_region['height']}")
        
        # 如果命令行指定了UI显示设置，更新配置
        if show_ui is not None:
            config_manager.set('show_ui', show_ui)
            config_manager.save_config()
            print(f"✓ 已更新UI显示设置: {'显示' if show_ui else '不显示'}")
        
        scanner = OptimizedQRCodeScanner(
            udp_host=UDP_HOST, 
            udp_port=UDP_PORT, 
            resolution=resolution,
            camera_index=camera_index, 
            debug_mode=debug_mode, 
            target_fps=target_fps,
            config_file=config_file
        )
        scanner.run()
    except RuntimeError as e:
        print(f"初始化失败: {e}")
    except Exception as e:
        print(f"程序错误: {e}")

if __name__ == "__main__":
    main() 