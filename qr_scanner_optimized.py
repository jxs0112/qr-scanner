#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版二维码识别程序
专门针对4K分辨率下的性能优化
"""

import cv2
import socket
import json
import time
import warnings
import logging
from datetime import datetime
from pyzbar import pyzbar
import threading
import queue
import numpy as np

# 设置日志级别，减少zbar的调试输出
logging.getLogger().setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyzbar")

class OptimizedQRCodeScanner:
    # 预定义的分辨率选项
    RESOLUTIONS = {
        'low': (320, 240),
        'medium': (640, 480),
        'high': (1280, 720),
        'full_hd': (1920, 1080),
        'ultra_hd': (3840, 2160)
    }
    
    def __init__(self, udp_host='127.0.0.1', udp_port=8888, resolution='ultra_hd', 
                 camera_index=0, debug_mode=False, target_fps=30):
        """
        初始化优化版二维码扫描器
        """
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_qr_data = None
        self.last_send_time = 0
        self.send_interval = 1.5  # 减少重复发送间隔
        self.debug_mode = debug_mode
        self.target_fps = target_fps
        
        # 高级优化参数
        self.frame_skip_count = 0
        self.adaptive_skip_interval = 2  # 自适应跳帧间隔
        self.detection_region_scale = 0.4  # 更小的检测区域（40%）
        self.use_simple_preprocess = True
        self.use_opencv_qr = True  # 使用OpenCV的QR检测器（更快）
        self.dynamic_resolution = True  # 动态分辨率调整
        
        # 摄像头控制参数（仅显示，macOS AVFOUNDATION后端不支持软件控制）
        self.camera_backend = "unknown"
        self.supports_manual_control = False  # 是否支持手动控制
        self.show_camera_warning = True  # 是否显示摄像头控制警告
        
        # 性能监控
        self.fps_history = []
        self.performance_check_interval = 60  # 每60帧检查一次性能
        self.target_min_fps = 15  # 目标最低FPS
        
        # 多尺度检测
        self.detection_scales = [1.0, 0.7, 0.5]  # 多尺度检测
        self.current_scale_index = 0
        
        # 识别稳定性跟踪
        self.qr_confidence = {}
        self.min_confidence = 2
        self.frame_count = 0
        
        # 预编译正则表达式（如果需要内容过滤）
        import re
        self.url_pattern = re.compile(r'https?://[^\s]+')
        
        # OpenCV QR检测器初始化
        self.cv_qr_detector = cv2.QRCodeDetector()
        
        # 缓存最近的检测结果
        self.detection_cache = {}
        self.cache_ttl = 5  # 缓存5帧
        
        # 解析分辨率设置
        if isinstance(resolution, str):
            if resolution in self.RESOLUTIONS:
                self.width, self.height = self.RESOLUTIONS[resolution]
            else:
                print(f"警告：未知的分辨率设置 '{resolution}'，使用默认分辨率")
                self.width, self.height = self.RESOLUTIONS['ultra_hd']
        elif isinstance(resolution, tuple) and len(resolution) == 2:
            self.width, self.height = resolution
        else:
            print(f"警告：无效的分辨率格式，使用默认分辨率")
            self.width, self.height = self.RESOLUTIONS['ultra_hd']
        
        # 初始化摄像头
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_index}")
        
        # 检测摄像头能力并优化设置
        self.detect_camera_capabilities()
        self.optimize_camera_settings()
        
        # 获取实际设置
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"优化版二维码扫描器已初始化")
        print(f"UDP目标: {udp_host}:{udp_port}")
        print(f"实际分辨率: {actual_width}x{actual_height}")
        print(f"实际帧率: {actual_fps:.1f} FPS")
        print(f"摄像头后端: {self.camera_backend}")
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
        """
        h, w = frame.shape[:2]
        
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
                
                # 显示
                cv2.imshow('Optimized QR Scanner V2', frame)
                
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
        cv2.destroyAllWindows()
        self.socket.close()
        print("资源清理完成")

def main():
    """主函数"""
    import sys
    
    print("=== 高级优化版二维码识别程序 ===")
    print("优化功能:")
    print("  - 自适应跳帧和区域调整")
    print("  - OpenCV + pyzbar双重检测")
    print("  - 多尺度检测")
    print("  - 智能结果缓存")
    print("  - 实时性能监控")
    print("\n按键控制:")
    print("  q: 退出程序")
    print("  d: 切换调试模式")
    print("  s: 切换简化预处理")
    print("  o: 切换OpenCV检测器")
    print("  a: 切换自适应优化")
    print("  r: 调整检测区域大小")
    print("  c: 清除检测缓存")
    print("\n信息显示:")
    print("  i: 显示摄像头信息")
    print("  h: 显示性能提示")
    print("  w: 切换警告显示")
    
    # 解析参数
    resolution = 'ultra_hd'
    camera_index = 0
    debug_mode = False
    target_fps = 30
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--debug':
            debug_mode = True
            args.pop(i)
        elif args[i].startswith('--fps='):
            try:
                target_fps = int(args[i].replace('--fps=', ''))
                args.pop(i)
            except ValueError:
                print(f"警告：无效的目标帧率")
        else:
            i += 1
    
    if len(args) > 0:
        resolution = args[0]
    if len(args) > 1:
        try:
            camera_index = int(args[1])
        except ValueError:
            print(f"警告：无效的摄像头索引")
    
    UDP_HOST = '127.0.0.1'
    UDP_PORT = 8888
    
    try:
        scanner = OptimizedQRCodeScanner(UDP_HOST, UDP_PORT, resolution, 
                                       camera_index, debug_mode, target_fps)
        scanner.run()
    except RuntimeError as e:
        print(f"初始化失败: {e}")
    except Exception as e:
        print(f"程序错误: {e}")

if __name__ == "__main__":
    main() 