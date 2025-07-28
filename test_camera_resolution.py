#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头分辨率测试脚本
用于测试摄像头支持的分辨率
"""

import cv2
import time

def test_camera_resolutions(camera_index=0):
    """
    测试摄像头支持的分辨率
    
    Args:
        camera_index (int): 摄像头索引
    """
    print(f"=== 测试摄像头 {camera_index} 支持的分辨率 ===")
    
    # 常见的分辨率
    test_resolutions = [
        (160, 120),     # QQVGA
        (320, 240),     # QVGA
        (640, 480),     # VGA
        (800, 600),     # SVGA
        (1024, 768),    # XGA
        (1280, 720),    # HD 720p
        (1280, 1024),   # SXGA
        (1600, 1200),   # UXGA
        (1920, 1080),   # Full HD 1080p
        (2560, 1440),   # QHD
        (3840, 2160),   # 4K UHD
    ]
    
    # 打开摄像头
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"错误：无法打开摄像头 {camera_index}")
        return
    
    supported_resolutions = []
    
    print("正在测试分辨率...")
    for width, height in test_resolutions:
        # 设置分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # 获取实际设置的分辨率
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 测试是否能读取帧
        ret, frame = cap.read()
        if ret and frame is not None:
            status = "✓" if (actual_width == width and actual_height == height) else "⚠"
            print(f"{status} {width}x{height} -> 实际: {actual_width}x{actual_height}")
            
            if ret:
                supported_resolutions.append((actual_width, actual_height))
        else:
            print(f"✗ {width}x{height} -> 无法读取帧")
    
    cap.release()
    
    # 去重并排序
    supported_resolutions = sorted(list(set(supported_resolutions)))
    
    print(f"\n=== 摄像头 {camera_index} 支持的分辨率总结 ===")
    print("支持的分辨率:")
    for width, height in supported_resolutions:
        print(f"  {width}x{height}")
    
    return supported_resolutions

def test_camera_properties(camera_index=0, resolution=(640, 480)):
    """
    测试摄像头属性
    
    Args:
        camera_index (int): 摄像头索引
        resolution (tuple): 测试分辨率
    """
    print(f"\n=== 摄像头 {camera_index} 属性测试 ===")
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"错误：无法打开摄像头 {camera_index}")
        return
    
    # 设置分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    
    # 获取摄像头属性
    properties = {
        'frame_width': cv2.CAP_PROP_FRAME_WIDTH,
        'frame_height': cv2.CAP_PROP_FRAME_HEIGHT,
        'fps': cv2.CAP_PROP_FPS,
        'brightness': cv2.CAP_PROP_BRIGHTNESS,
        'contrast': cv2.CAP_PROP_CONTRAST,
        'saturation': cv2.CAP_PROP_SATURATION,
        'hue': cv2.CAP_PROP_HUE,
        'gain': cv2.CAP_PROP_GAIN,
        'exposure': cv2.CAP_PROP_EXPOSURE,
    }
    
    print(f"分辨率: {resolution[0]}x{resolution[1]}")
    for name, prop in properties.items():
        value = cap.get(prop)
        print(f"{name}: {value}")
    
    cap.release()

def interactive_resolution_test():
    """
    交互式分辨率测试
    """
    print("=== 交互式摄像头分辨率测试 ===")
    
    # 获取摄像头索引
    camera_index = 0
    try:
        camera_input = input("请输入摄像头索引 (默认0): ").strip()
        if camera_input:
            camera_index = int(camera_input)
    except ValueError:
        print("无效输入，使用默认摄像头索引 0")
    
    # 测试分辨率
    supported = test_camera_resolutions(camera_index)
    
    if not supported:
        print("未找到支持的分辨率")
        return
    
    # 测试属性
    test_camera_properties(camera_index)
    
    # 实时预览
    while True:
        choice = input("\n是否要进行实时预览测试？(y/n): ").strip().lower()
        if choice == 'y':
            try:
                res_input = input("请输入要测试的分辨率 (格式: 宽x高，如 1280x720): ").strip()
                if 'x' in res_input:
                    width, height = map(int, res_input.split('x'))
                    live_preview_test(camera_index, (width, height))
                else:
                    print("无效的分辨率格式")
            except ValueError:
                print("无效的分辨率格式")
        elif choice == 'n':
            break
        else:
            print("请输入 y 或 n")

def live_preview_test(camera_index=0, resolution=(640, 480)):
    """
    实时预览测试
    
    Args:
        camera_index (int): 摄像头索引
        resolution (tuple): 测试分辨率
    """
    print(f"开始实时预览测试: {resolution[0]}x{resolution[1]}")
    print("按 'q' 键退出预览")
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"错误：无法打开摄像头 {camera_index}")
        return
    
    # 设置分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    
    # 获取实际分辨率
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"实际分辨率: {actual_width}x{actual_height}")
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break
        
        frame_count += 1
        
        # 显示帧率信息
        if frame_count % 30 == 0:
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time
            print(f"当前帧率: {fps:.1f} FPS")
        
        # 在图像上显示分辨率信息
        cv2.putText(frame, f"Resolution: {actual_width}x{actual_height}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Camera Resolution Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # 显示最终统计
    total_time = time.time() - start_time
    avg_fps = frame_count / total_time
    print(f"测试结束 - 总帧数: {frame_count}, 平均帧率: {avg_fps:.1f} FPS")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("摄像头分辨率测试脚本")
            print("\n使用方法:")
            print("  python3 test_camera_resolution.py           # 交互式测试")
            print("  python3 test_camera_resolution.py [索引]    # 测试指定摄像头")
            print("  python3 test_camera_resolution.py --help    # 显示帮助")
            sys.exit(0)
        else:
            try:
                camera_index = int(sys.argv[1])
                test_camera_resolutions(camera_index)
                test_camera_properties(camera_index)
            except ValueError:
                print("无效的摄像头索引")
    else:
        interactive_resolution_test() 