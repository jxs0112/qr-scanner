#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
帧率测试和优化脚本
测试不同分辨率下的摄像头帧率，并提供优化建议
"""

import cv2
import time
import numpy as np

def test_camera_fps(camera_index=0, test_duration=3):
    """
    测试摄像头在不同分辨率下的帧率
    
    Args:
        camera_index (int): 摄像头索引
        test_duration (int): 测试时长（秒）
    """
    print(f"=== 摄像头 {camera_index} 帧率测试 ===")
    print(f"测试时长: {test_duration} 秒")
    print()
    
    # 测试的分辨率列表
    resolutions = [
        ('240p (low)', 320, 240),
        ('480p (medium)', 640, 480),
        ('720p (high)', 1280, 720),
        ('1080p (full_hd)', 1920, 1080),
        ('4K (ultra_hd)', 3840, 2160)
    ]
    
    target_fps_list = [30, 60]
    
    results = []
    
    for res_name, width, height in resolutions:
        print(f"📺 测试分辨率: {res_name} ({width}x{height})")
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"❌ 无法打开摄像头 {camera_index}")
            return
        
        for target_fps in target_fps_list:
            try:
                # 设置分辨率和帧率
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS, target_fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 等待摄像头调整
                time.sleep(0.5)
                
                # 获取实际设置的值
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                reported_fps = cap.get(cv2.CAP_PROP_FPS)
                
                # 实际测量帧率
                frame_count = 0
                start_time = time.time()
                end_time = start_time + test_duration
                
                while time.time() < end_time:
                    ret, frame = cap.read()
                    if ret:
                        frame_count += 1
                    else:
                        break
                
                elapsed_time = time.time() - start_time
                measured_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
                
                # 评估结果
                if actual_width == width and actual_height == height:
                    resolution_ok = "✅"
                else:
                    resolution_ok = "⚠️"
                
                if measured_fps >= target_fps * 0.8:
                    fps_ok = "✅"
                elif measured_fps >= target_fps * 0.6:
                    fps_ok = "⚠️"
                else:
                    fps_ok = "❌"
                
                result = {
                    'resolution': res_name,
                    'requested': (width, height),
                    'actual': (actual_width, actual_height),
                    'target_fps': target_fps,
                    'reported_fps': reported_fps,
                    'measured_fps': measured_fps,
                    'resolution_ok': resolution_ok,
                    'fps_ok': fps_ok
                }
                results.append(result)
                
                print(f"  🎯 目标: {target_fps} FPS")
                print(f"     分辨率: {resolution_ok} {actual_width}x{actual_height}")
                print(f"     报告帧率: {reported_fps:.1f} FPS")
                print(f"     实测帧率: {fps_ok} {measured_fps:.1f} FPS")
                print()
                
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                print()
        
        cap.release()
    
    return results

def recommend_optimal_settings(results):
    """
    根据测试结果推荐最佳设置
    
    Args:
        results (list): 测试结果列表
    """
    print("=== 优化建议 ===")
    print()
    
    # 找到满足30 FPS的最高分辨率
    good_30fps = [r for r in results if r['target_fps'] == 30 and r['measured_fps'] >= 24]
    good_60fps = [r for r in results if r['target_fps'] == 60 and r['measured_fps'] >= 48]
    
    if good_30fps:
        best_30 = max(good_30fps, key=lambda x: x['actual'][0] * x['actual'][1])
        print(f"🏆 推荐设置 (30 FPS):")
        print(f"   分辨率: {best_30['resolution']}")
        print(f"   实际帧率: {best_30['measured_fps']:.1f} FPS")
        print(f"   命令: python3 qr_scanner.py {get_resolution_name(best_30['actual'])} --fps=30")
        print()
    
    if good_60fps:
        best_60 = max(good_60fps, key=lambda x: x['actual'][0] * x['actual'][1])
        print(f"🚀 高帧率设置 (60 FPS):")
        print(f"   分辨率: {best_60['resolution']}")
        print(f"   实际帧率: {best_60['measured_fps']:.1f} FPS")
        print(f"   命令: python3 qr_scanner.py {get_resolution_name(best_60['actual'])} --fps=60")
        print()
    
    # 特殊建议
    print("💡 使用建议:")
    if not good_30fps:
        print("   - 当前摄像头可能不支持高帧率，建议使用较低分辨率")
        print("   - 尝试: python3 qr_scanner.py low --fps=30")
    else:
        print("   - 对于二维码识别，30 FPS 通常已经足够")
        print("   - 如果需要更平滑的显示，可以尝试 60 FPS")
    
    print("   - 使用 --debug 模式可以看到预处理效果")
    print("   - 光线充足的环境有助于提高识别成功率")

def get_resolution_name(actual_resolution):
    """
    根据实际分辨率获取预设名称
    """
    width, height = actual_resolution
    if width <= 320:
        return "low"
    elif width <= 640:
        return "medium"
    elif width <= 1280:
        return "high"
    elif width <= 1920:
        return "full_hd"
    else:
        return "ultra_hd"

def quick_fps_test(camera_index=0):
    """
    快速帧率测试，只测试关键分辨率
    """
    print("=== 快速帧率测试 ===")
    print("测试常用分辨率的30 FPS性能")
    print()
    
    quick_resolutions = [
        ('medium', 640, 480),
        ('high', 1280, 720),
        ('full_hd', 1920, 1080)
    ]
    
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"❌ 无法打开摄像头 {camera_index}")
        return
    
    recommendations = []
    
    for res_name, width, height in quick_resolutions:
        # 设置参数
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        time.sleep(0.3)
        
        # 快速测试
        frame_count = 0
        start_time = time.time()
        test_duration = 2
        
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
        
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if fps >= 25:
            status = "✅ 推荐"
            recommendations.append((res_name, fps))
        elif fps >= 20:
            status = "⚠️ 可用"
        else:
            status = "❌ 不建议"
        
        print(f"{res_name:10} ({actual_width}x{actual_height}): {fps:5.1f} FPS {status}")
    
    cap.release()
    
    if recommendations:
        best = max(recommendations, key=lambda x: x[1])
        print()
        print(f"🏆 推荐使用: {best[0]} ({best[1]:.1f} FPS)")
        print(f"💻 启动命令: python3 qr_scanner.py {best[0]}")
    else:
        print()
        print("⚠️ 建议使用更低的分辨率或检查摄像头设置")

def main():
    """
    主函数
    """
    print("摄像头帧率测试和优化工具")
    print("=" * 50)
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_fps_test()
    else:
        print("选择测试模式:")
        print("1. 快速测试 (推荐)")
        print("2. 完整测试")
        print("3. 退出")
        
        try:
            choice = input("\n请选择 (1-3): ").strip()
            
            if choice == '1':
                quick_fps_test()
            elif choice == '2':
                results = test_camera_fps()
                if results:
                    recommend_optimal_settings(results)
            elif choice == '3':
                print("退出")
                return
            else:
                print("无效选择")
                
        except KeyboardInterrupt:
            print("\n测试中断")

if __name__ == "__main__":
    main() 