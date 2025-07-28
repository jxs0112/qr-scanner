#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zbar警告测试和处理脚本
用于测试和解决zbar库产生的警告信息
"""

import cv2
import numpy as np
import warnings
import logging
import sys
from io import StringIO
from contextlib import redirect_stderr
from pyzbar import pyzbar

# 配置日志和警告过滤
logging.basicConfig(level=logging.ERROR)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pyzbar")

def test_zbar_warnings():
    """
    测试zbar警告的产生和处理
    """
    print("=== zbar警告测试 ===")
    print("测试不同图像处理方法是否会产生zbar警告")
    print()
    
    # 创建一个测试图像（可能触发警告的图像）
    test_image = np.random.randint(0, 255, (400, 400), dtype=np.uint8)
    
    # 添加一些可能被误认为条码的模式
    for i in range(0, 400, 20):
        cv2.line(test_image, (i, 0), (i, 400), 255, 2)
    
    print("1. 测试原始pyzbar.decode（可能产生警告）:")
    try:
        # 不过滤警告的版本
        detected = pyzbar.decode(test_image)
        print(f"   检测到 {len(detected)} 个符号（可能有警告输出）")
    except Exception as e:
        print(f"   异常: {e}")
    
    print("\n2. 测试过滤警告的版本:")
    try:
        # 过滤stderr输出
        f = StringIO()
        with redirect_stderr(f):
            detected = pyzbar.decode(test_image, symbols=[pyzbar.ZBarSymbol.QRCODE])
        
        stderr_output = f.getvalue()
        print(f"   检测到 {len(detected)} 个QR码")
        if stderr_output:
            print(f"   捕获的警告信息: {len(stderr_output.splitlines())} 行")
        else:
            print("   无警告信息")
    except Exception as e:
        print(f"   异常: {e}")
    
    print("\n3. 测试不同预处理方法:")
    methods = [
        ("原始", lambda img: img),
        ("灰度转换", lambda img: img),  # 已经是灰度
        ("自适应阈值", lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)),
        ("Otsu", lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
        ("边缘检测", lambda img: cv2.Canny(img, 50, 150)),
    ]
    
    for method_name, process_func in methods:
        try:
            processed = process_func(test_image)
            f = StringIO()
            with redirect_stderr(f):
                detected = pyzbar.decode(processed, symbols=[pyzbar.ZBarSymbol.QRCODE])
            
            stderr_output = f.getvalue()
            warning_count = len(stderr_output.splitlines()) if stderr_output else 0
            
            print(f"   {method_name:12}: {len(detected)} QR码, {warning_count} 警告")
            
        except Exception as e:
            print(f"   {method_name:12}: 错误 - {e}")

def demonstrate_warning_suppression():
    """
    演示警告抑制的效果
    """
    print("\n=== 警告抑制演示 ===")
    
    # 创建一个更可能触发databar警告的图像
    test_image = np.zeros((200, 400), dtype=np.uint8)
    
    # 创建类似databar的模式
    for i in range(10, 390, 30):
        cv2.rectangle(test_image, (i, 50), (i+20, 150), 255, -1)
    for i in range(20, 380, 30):
        cv2.rectangle(test_image, (i, 60), (i+10, 140), 0, -1)
    
    print("1. 原始pyzbar调用（可能产生databar警告）:")
    print("   注意观察是否有类似 'decoder/databar.c' 的警告信息")
    
    try:
        detected = pyzbar.decode(test_image)
        print(f"   结果: 检测到 {len(detected)} 个符号")
    except Exception as e:
        print(f"   异常: {e}")
    
    print("\n2. 抑制警告的调用:")
    try:
        f = StringIO()
        with redirect_stderr(f):
            detected = pyzbar.decode(test_image, symbols=[pyzbar.ZBarSymbol.QRCODE])
        
        stderr_content = f.getvalue()
        print(f"   结果: 检测到 {len(detected)} 个QR码")
        if stderr_content:
            lines = stderr_content.strip().split('\n')
            print(f"   捕获了 {len(lines)} 行警告信息（已抑制显示）")
            if any('databar' in line.lower() for line in lines):
                print("   ✓ 成功捕获databar相关警告")
        else:
            print("   无警告产生")
            
    except Exception as e:
        print(f"   异常: {e}")

def best_practices():
    """
    展示最佳实践
    """
    print("\n=== 最佳实践建议 ===")
    print()
    print("1. 🔇 抑制警告输出:")
    print("   - 使用 redirect_stderr 重定向错误输出")
    print("   - 配置 warnings.filterwarnings")
    print("   - 设置适当的日志级别")
    print()
    print("2. 🎯 限制符号类型:")
    print("   - 使用 symbols=[pyzbar.ZBarSymbol.QRCODE] 只识别QR码")
    print("   - 避免不必要的条码类型检测")
    print("   - 减少误报和警告")
    print()
    print("3. 🚀 优化预处理:")
    print("   - 优先使用效果好的预处理方法")
    print("   - 避免过度的图像处理")
    print("   - 找到结果后及时停止")
    print()
    print("4. 🛡️ 异常处理:")
    print("   - 静默处理预期的异常")
    print("   - 提供用户友好的错误信息")
    print("   - 确保程序稳定运行")

def main():
    """
    主函数
    """
    print("zbar库警告测试和处理工具")
    print("=" * 50)
    
    test_zbar_warnings()
    demonstrate_warning_suppression()
    best_practices()
    
    print("\n=== 总结 ===")
    print("之前看到的警告信息:")
    print("  WARNING: decoder/databar.c:1211: _zbar_decode_databar:")
    print("  Assertion \"seg->finder >= 0\" failed.")
    print()
    print("解释:")
    print("- 这是zbar库在尝试解码DataBar条码时的内部警告")
    print("- 当图像中有类似条码的图案但不是真正的条码时会出现")
    print("- 对QR码识别功能没有实际影响")
    print("- 通过限制符号类型和错误输出重定向可以抑制")
    print()
    print("✅ 已在qr_scanner.py中实施了修复方案")

if __name__ == "__main__":
    main() 