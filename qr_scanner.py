#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二维码识别程序
通过摄像头识别二维码内容，并发送UDP包
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

# 过滤zbar相关的警告
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyzbar")

class QRCodeScanner:
    # 预定义的分辨率选项
    RESOLUTIONS = {
        'low': (320, 240),      # 低分辨率
        'medium': (640, 480),   # 中等分辨率（默认）
        'high': (1280, 720),    # 高分辨率 (720p)
        'full_hd': (1920, 1080), # 全高清 (1080p)
        'ultra_hd': (3840, 2160) # 4K超高清
    }
    
    def __init__(self, udp_host='127.0.0.1', udp_port=8888, resolution='medium', camera_index=0, debug_mode=False, target_fps=30):
        """
        初始化二维码扫描器
        
        Args:
            udp_host (str): UDP目标主机地址
            udp_port (int): UDP目标端口
            resolution (str or tuple): 分辨率设置，可以是预定义的字符串或(width, height)元组
            camera_index (int): 摄像头索引，默认为0
            debug_mode (bool): 是否启用调试模式，显示预处理结果
            target_fps (int): 目标帧率，默认30 FPS
        """
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_qr_data = None
        self.last_send_time = 0
        self.send_interval = 2.0  # 增加防重复发送间隔时间（秒）
        self.debug_mode = debug_mode
        self.target_fps = target_fps
        
        # 添加识别稳定性跟踪
        self.qr_confidence = {}  # 跟踪每个二维码的识别次数
        self.min_confidence = 3  # 需要连续识别3次才发送
        self.frame_count = 0
        
        # 解析分辨率设置
        if isinstance(resolution, str):
            if resolution in self.RESOLUTIONS:
                self.width, self.height = self.RESOLUTIONS[resolution]
            else:
                print(f"警告：未知的分辨率设置 '{resolution}'，使用默认分辨率")
                self.width, self.height = self.RESOLUTIONS['medium']
        elif isinstance(resolution, tuple) and len(resolution) == 2:
            self.width, self.height = resolution
        else:
            print(f"警告：无效的分辨率格式，使用默认分辨率")
            self.width, self.height = self.RESOLUTIONS['medium']
        
        # 初始化摄像头
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 {camera_index}")
        
        # 优化摄像头性能设置
        self.optimize_camera_settings()
        
        # 获取实际设置的分辨率和帧率
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"二维码扫描器已初始化")
        print(f"UDP目标: {udp_host}:{udp_port}")
        print(f"请求分辨率: {self.width}x{self.height}")
        print(f"实际分辨率: {actual_width}x{actual_height}")
        print(f"目标帧率: {target_fps} FPS")
        print(f"实际帧率: {actual_fps:.1f} FPS")
        print(f"摄像头索引: {camera_index}")
        print(f"调试模式: {'开启' if debug_mode else '关闭'}")
        print(f"识别稳定性检查: 需要连续识别{self.min_confidence}次")
        print(f"按 'q' 键退出程序")
        if debug_mode:
            print(f"按 'd' 键切换调试模式显示")
        
        # 如果帧率低于目标值，给出建议
        if actual_fps < target_fps:
            print(f"⚠️  当前帧率 ({actual_fps:.1f}) 低于目标帧率 ({target_fps})")
            print(f"💡 建议：尝试降低分辨率以提高帧率")
    
    def optimize_camera_settings(self):
        """
        优化摄像头设置以获得更好的帧率
        """
        # 设置目标帧率
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        
        # 设置分辨率
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # 尝试各种优化设置
        try:
            # 设置缓冲区大小（减少延迟）
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 设置自动曝光和自动对焦
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 自动曝光
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # 自动对焦
            
            # 设置编码格式（如果支持）
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
        except Exception as e:
            # 某些设置可能不被所有摄像头支持
            pass
        
        # 如果当前分辨率下帧率仍然太低，自动降级分辨率
        self.auto_adjust_resolution_for_fps()
    
    def auto_adjust_resolution_for_fps(self):
        """
        智能调整分辨率以达到目标帧率
        """
        # 简化的帧率测试
        test_frames = 5
        start_time = time.time()
        
        for i in range(test_frames):
            ret, frame = self.cap.read()
            if not ret:
                break
        
        elapsed_time = time.time() - start_time
        measured_fps = test_frames / elapsed_time if elapsed_time > 0 else 0
        
        print(f"📊 测量帧率: {measured_fps:.1f} FPS")
        
        # 只在帧率明显低于目标时才调整（给20%的容差）
        if measured_fps < self.target_fps * 0.8:
            print(f"🔄 帧率偏低，尝试优化...")
            
            # 简化的分辨率调整策略
            if self.width > 1920:  # 4K -> 1080p
                new_width, new_height = 1920, 1080
                print(f"🔽 4K性能不足，降级到1080p")
            elif self.width > 1280:  # 1080p -> 720p
                new_width, new_height = 1280, 720
                print(f"🔽 1080p性能不足，降级到720p")
            elif self.width > 640:  # 720p -> 480p
                new_width, new_height = 640, 480
                print(f"🔽 720p性能不足，降级到480p")
            else:
                # 已经是最低分辨率，不再调整
                print(f"⚠️ 已是最低分辨率，帧率可能受限于硬件性能")
                return
            
            # 应用新设置
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # 等待调整生效
            time.sleep(0.3)
            
            # 验证调整效果
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if actual_width == new_width and actual_height == new_height:
                self.width, self.height = new_width, new_height
                print(f"✅ 调整到 {new_width}x{new_height}")
            else:
                print(f"⚠️ 分辨率调整可能不完全生效")
        else:
            print(f"✅ 帧率符合要求")
    
    def send_udp_packet(self, qr_data):
        """
        发送UDP包
        
        Args:
            qr_data (str): 二维码内容
        """
        try:
            # 构造要发送的数据
            packet_data = {
                'timestamp': datetime.now().isoformat(),
                'qr_content': qr_data,
                'source': 'qr_scanner'
            }
            
            # 转换为JSON字符串并编码
            json_data = json.dumps(packet_data, ensure_ascii=False)
            encoded_data = json_data.encode('utf-8')
            
            # 发送UDP包
            self.socket.sendto(encoded_data, (self.udp_host, self.udp_port))
            print(f"✓ UDP包已发送: {qr_data}")
            
        except Exception as e:
            print(f"✗ UDP发送失败: {e}")
    
    def preprocess_frame(self, frame):
        """
        预处理帧以提高二维码识别效果（高识别率版本）
        
        Args:
            frame: 原始摄像头帧
            
        Returns:
            list: 预处理后的图像列表，专注于提高识别成功率
        """
        processed_frames = []
        
        # 1. 原始帧
        processed_frames.append(frame)
        
        # 2. 灰度化
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        processed_frames.append(gray)
        
        # 3. 高斯模糊去噪 + 锐化
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        sharpened = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
        processed_frames.append(sharpened)
        
        # 4. 自适应直方图均衡化
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        processed_frames.append(enhanced)
        
        # 5. 多种二值化方法组合
        # Otsu + 高斯阈值
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_frames.append(otsu)
        
        # 6. 自适应阈值（更大的块大小）
        adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 21, 10)
        processed_frames.append(adaptive)
        
        # 7. 反转的自适应阈值（处理深色背景）
        adaptive_inv = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 21, 10)
        processed_frames.append(adaptive_inv)
        
        # 8. 对比度拉伸
        min_val = np.min(gray)
        max_val = np.max(gray)
        if max_val > min_val:
            stretched = ((gray - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            processed_frames.append(stretched)
        else:
            processed_frames.append(gray)
        
        # 9. 形态学处理（去噪）
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        morph = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
        processed_frames.append(morph)
        
        # 10. 多尺度处理（放大图像）
        height, width = gray.shape
        if width < 800:  # 如果图像较小，放大处理
            scale_factor = 800 / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            upscaled = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            processed_frames.append(upscaled)
        
        return processed_frames
    
    def process_qr_codes(self, frame):
        """
        处理帧中的二维码（增强版本）
        
        Args:
            frame: 摄像头帧
        """
        self.frame_count += 1
        
        # 预处理帧
        processed_frames = self.preprocess_frame(frame)
        
        # 尝试在所有预处理帧中识别二维码
        detected_qr_codes = []
        
        # 使用所有预处理方法，按优先级顺序
        for i in range(len(processed_frames)):
            processed_frame = processed_frames[i]
            try:
                # 临时重定向stderr来抑制zbar警告
                import os
                import sys
                from contextlib import redirect_stderr
                from io import StringIO
                
                f = StringIO()
                with redirect_stderr(f):
                    # 解码二维码，只查找QR码
                    detected_codes = pyzbar.decode(processed_frame, symbols=[pyzbar.ZBarSymbol.QRCODE])
                
                for qr_code in detected_codes:
                    # 检查是否已经识别过相同的二维码
                    qr_data = qr_code.data.decode('utf-8')
                    if not any(existing['data'] == qr_data for existing in detected_qr_codes):
                        detected_qr_codes.append({
                            'data': qr_data,
                            'rect': qr_code.rect,
                            'polygon': qr_code.polygon,
                            'method': i  # 记录使用的预处理方法
                        })
                        
            except Exception as e:
                # 静默处理异常，避免干扰用户体验
                continue
        
        # 更新识别信心度
        current_qr_data = set(qr['data'] for qr in detected_qr_codes)
        
        # 增加当前检测到的二维码的信心度
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
        
        # 处理识别到的二维码
        for qr_info in detected_qr_codes:
            qr_data = qr_info['data']
            current_time = time.time()
            
            # 检查是否达到发送条件
            confidence = self.qr_confidence.get(qr_data, 0)
            should_send = (
                confidence >= self.min_confidence and
                (qr_data != self.last_qr_data or current_time - self.last_send_time > self.send_interval)
            )
            
            if should_send:
                self.send_udp_packet(qr_data)
                self.last_qr_data = qr_data
                self.last_send_time = current_time
                
                # 显示使用的预处理方法
                method_names = ['原始', '灰度', '高斯模糊锐化', 'CLAHE', 'Otsu', '自适应阈值', '自适应阈值(反转)', '对比度拉伸', '形态学处理', '多尺度处理']
                if qr_info['method'] < len(method_names):
                    print(f"✓ 使用预处理方法: {method_names[qr_info['method']]} (信心度: {confidence})")
            
            # 在图像上绘制二维码边框
            points = qr_info['polygon']
            if len(points) > 4:
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                points = hull
            
            # 转换点坐标
            points = np.array(points, dtype=np.int32)
            
            # 根据信心度改变边框颜色
            if confidence >= self.min_confidence:
                color = (0, 255, 0)  # 绿色 - 可以发送
            else:
                color = (0, 255, 255)  # 黄色 - 识别中
            
            cv2.polylines(frame, [points], True, color, 2)
            
            # 添加文本标签（包含信心度）
            rect = qr_info['rect']
            label = f"{qr_data} ({confidence})"
            cv2.putText(frame, label, (rect.left, rect.top - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def show_debug_frames(self, processed_frames):
        """
        显示调试帧，展示所有预处理结果
        
        Args:
            processed_frames: 预处理后的帧列表
        """
        method_names = ['原始', '灰度', '高斯模糊锐化', 'CLAHE', 'Otsu', '自适应阈值', '自适应阈值(反转)', '对比度拉伸', '形态学处理', '多尺度处理']
        
        # 创建网格显示 - 3行4列（适应10个方法）
        rows = 3
        cols = 4
        cell_height = 150
        cell_width = 200
        
        # 创建大画布
        canvas = np.zeros((cell_height * rows, cell_width * cols, 3), dtype=np.uint8)
        
        for i, frame in enumerate(processed_frames):
            if i >= len(method_names) or i >= rows * cols:
                break
                
            row = i // cols
            col = i % cols
            
            # 调整帧大小
            if len(frame.shape) == 3:
                resized = cv2.resize(frame, (cell_width, cell_height))
            else:
                # 灰度图转BGR
                resized = cv2.resize(frame, (cell_width, cell_height))
                resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
            
            # 放置到画布上
            y_start = row * cell_height
            y_end = (row + 1) * cell_height
            x_start = col * cell_width
            x_end = (col + 1) * cell_width
            
            canvas[y_start:y_end, x_start:x_end] = resized
            
            # 添加标签（缩短文字以适应更小的格子）
            label = method_names[i]
            if len(label) > 8:
                label = label[:7] + '.'
            cv2.putText(canvas, label, (x_start + 5, y_start + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.imshow('预处理调试窗口', canvas)
    
    def run(self):
        """
        运行二维码扫描器
        """
        show_debug = False  # 调试显示开关
        
        try:
            while True:
                # 读取摄像头帧
                ret, frame = self.cap.read()
                if not ret:
                    print("无法读取摄像头数据")
                    break
                
                # 处理二维码
                processed_frames = self.preprocess_frame(frame)
                frame = self.process_qr_codes(frame)
                
                # 显示图像
                cv2.imshow('QR Code Scanner', frame)
                
                # 如果启用调试模式且需要显示调试窗口
                if self.debug_mode and show_debug:
                    self.show_debug_frames(processed_frames)
                
                # 检查键盘输入
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('d') and self.debug_mode:
                    show_debug = not show_debug
                    if not show_debug:
                        cv2.destroyWindow('预处理调试窗口')
                    print(f"调试显示: {'开启' if show_debug else '关闭'}")
                    
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        except Exception as e:
            print(f"程序运行错误: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        清理资源
        """
        print("正在清理资源...")
        self.cap.release()
        cv2.destroyAllWindows()
        self.socket.close()
        print("资源清理完成")
    
    @classmethod
    def list_resolutions(cls):
        """
        列出所有可用的分辨率选项
        """
        print("可用的分辨率选项:")
        for key, (width, height) in cls.RESOLUTIONS.items():
            print(f"  {key}: {width}x{height}")
        print("  或者使用自定义分辨率: (width, height)")
    
    def get_camera_info(self):
        """
        获取摄像头信息
        """
        print("\n=== 摄像头信息 ===")
        print(f"当前分辨率: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        print(f"帧率: {self.cap.get(cv2.CAP_PROP_FPS):.1f} FPS")
        print(f"亮度: {self.cap.get(cv2.CAP_PROP_BRIGHTNESS):.2f}")
        print(f"对比度: {self.cap.get(cv2.CAP_PROP_CONTRAST):.2f}")
        print(f"饱和度: {self.cap.get(cv2.CAP_PROP_SATURATION):.2f}")
        print("==================\n")

def main():
    """
    主函数
    """
    import sys
    
    print("=== 二维码识别UDP发送程序 ===")
    print("程序将通过摄像头识别二维码，并将内容通过UDP发送")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 qr_scanner.py [分辨率] [摄像头索引] [选项]")
            print("\n参数:")
            print("  分辨率: low/medium/high/full_hd/ultra_hd (默认: medium)")
            QRCodeScanner.list_resolutions()
            print("  摄像头索引: 0, 1, 2... (默认: 0)")
            print("\n选项:")
            print("  --debug: 启用调试模式")
            print("  --fps=数值: 设置目标帧率 (默认: 30)")
            print("\n常用示例:")
            print("  python3 qr_scanner.py                    # 默认设置")
            print("  python3 qr_scanner.py high               # 720p分辨率")
            print("  python3 qr_scanner.py ultra_hd --fps=15  # 4K分辨率，15帧")
            print("  python3 qr_scanner.py --debug            # 调试模式")
            return
        elif sys.argv[1] == '--list':
            QRCodeScanner.list_resolutions()
            return
    
    # 解析命令行参数
    resolution = 'medium'  # 默认分辨率
    camera_index = 0       # 默认摄像头索引
    debug_mode = False     # 默认关闭调试模式
    target_fps = 30       # 默认目标帧率
    
    # 解析参数
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
                print(f"警告：无效的目标帧率 '{args[i].replace('--fps=', '')}'，使用默认值 30")
        else:
            i += 1
    
    if len(args) > 0:
        resolution = args[0]
    if len(args) > 1:
        try:
            camera_index = int(args[1])
        except ValueError:
            print(f"警告：无效的摄像头索引 '{args[1]}'，使用默认值 0")
    
    # 可以在这里修改UDP目标地址和端口
    UDP_HOST = '127.0.0.1'  # 目标主机
    UDP_PORT = 8888         # 目标端口
    
    try:
        scanner = QRCodeScanner(UDP_HOST, UDP_PORT, resolution, camera_index, debug_mode, target_fps)
        scanner.get_camera_info()
        scanner.run()
    except RuntimeError as e:
        print(f"初始化失败: {e}")
        print("\n可能的解决方案:")
        print("1. 检查摄像头是否被其他程序占用")
        print("2. 尝试不同的摄像头索引（0, 1, 2...）")
        print("3. 检查摄像头权限设置")
    except Exception as e:
        print(f"程序错误: {e}")

if __name__ == "__main__":
    main() 