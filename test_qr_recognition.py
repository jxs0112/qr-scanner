#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二维码识别测试脚本
用于测试不同预处理方法对彩色背景二维码的识别效果
"""

import cv2
import numpy as np
from pyzbar import pyzbar
import time

def test_preprocessing_methods(image_path):
    """
    测试不同预处理方法对二维码识别的影响
    
    Args:
        image_path (str): 测试图像路径
    """
    # 读取图像
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"无法读取图像: {image_path}")
        return
    
    print(f"测试图像: {image_path}")
    print("=" * 50)
    
    # 预处理方法列表
    methods = [
        ("原始", lambda img: img),
        ("灰度", lambda img: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)),
        ("直方图均衡", lambda img: cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))),
        ("高斯模糊", lambda img: cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)),
        ("自适应阈值", lambda img: cv2.adaptiveThreshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
        ("Otsu", lambda img: cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
        ("形态学", lambda img: cv2.morphologyEx(cv2.adaptiveThreshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))),
        ("对比度增强", lambda img: cv2.convertScaleAbs(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), alpha=1.5, beta=0)),
        ("边缘检测", lambda img: cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 50, 150)),
        ("HSV", lambda img: cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), cv2.COLOR_BGR2GRAY)),
        ("拉普拉斯", lambda img: np.uint8(np.absolute(cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F)))),
        ("双边滤波", lambda img: cv2.bilateralFilter(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 9, 75, 75))
    ]
    
    results = []
    
    for method_name, process_func in methods:
        try:
            # 预处理
            processed = process_func(frame)
            
            # 识别二维码
            start_time = time.time()
            qr_codes = pyzbar.decode(processed)
            end_time = time.time()
            
            # 记录结果
            success = len(qr_codes) > 0
            qr_data = qr_codes[0].data.decode('utf-8') if success else "无"
            processing_time = (end_time - start_time) * 1000  # 毫秒
            
            results.append({
                'method': method_name,
                'success': success,
                'data': qr_data,
                'time': processing_time,
                'count': len(qr_codes)
            })
            
            print(f"{method_name:12} | {'✓' if success else '✗'} | {qr_data[:30]:30} | {processing_time:6.1f}ms")
            
        except Exception as e:
            print(f"{method_name:12} | ✗ | 错误: {str(e)[:30]:30} | N/A")
            results.append({
                'method': method_name,
                'success': False,
                'data': f"错误: {e}",
                'time': 0,
                'count': 0
            })
    
    print("=" * 50)
    
    # 统计结果
    successful_methods = [r for r in results if r['success']]
    if successful_methods:
        print(f"成功识别的方法数量: {len(successful_methods)}")
        print("成功的方法:")
        for result in successful_methods:
            print(f"  - {result['method']}: {result['data']}")
    else:
        print("所有方法都未能识别二维码")

def main():
    """
    主函数
    """
    print("二维码识别预处理方法测试")
    print("请准备一张包含二维码的测试图像")
    
    # 可以在这里指定测试图像路径
    # test_image = "test_qr.png"  # 替换为实际的图像路径
    
    # 或者使用摄像头实时测试
    print("按 't' 键进行测试，按 'q' 键退出")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow('测试窗口 - 按 t 测试当前帧', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('t'):
            # 保存当前帧并测试
            test_image = "temp_test_frame.png"
            cv2.imwrite(test_image, frame)
            test_preprocessing_methods(test_image)
            print("\n按任意键继续...")
            cv2.waitKey(0)
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 