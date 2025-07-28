#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建QR Scanner图标文件
如果PIL可用，创建真实的ico文件，否则提供说明
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    def create_icon():
        # 创建一个32x32的图标
        size = (32, 32)
        
        # 创建图像
        img = Image.new('RGBA', size, (0, 0, 0, 0))  # 透明背景
        draw = ImageDraw.Draw(img)
        
        # 绘制QR码样式的图标
        # 外框
        draw.rectangle([2, 2, 29, 29], outline='black', width=2)
        
        # 内部QR码样式的方块
        blocks = [
            # 左上角定位符
            [4, 4, 10, 10],
            [6, 6, 8, 8],
            
            # 右上角定位符
            [21, 4, 27, 10],
            [23, 6, 25, 8],
            
            # 左下角定位符
            [4, 21, 10, 27],
            [6, 23, 8, 25],
            
            # 一些数据模块
            [12, 6, 13, 7],
            [15, 6, 16, 7],
            [18, 6, 19, 7],
            [12, 9, 13, 10],
            [15, 9, 16, 10],
            [18, 9, 19, 10],
            [12, 12, 13, 13],
            [15, 12, 16, 13],
            [18, 12, 19, 13],
            [12, 15, 13, 16],
            [15, 15, 16, 16],
            [18, 15, 19, 16],
            [21, 12, 22, 13],
            [24, 12, 25, 13],
            [27, 12, 28, 13],
            [21, 15, 22, 16],
            [24, 15, 25, 16],
            [27, 15, 28, 16],
        ]
        
        for block in blocks:
            draw.rectangle(block, fill='black')
        
        # 保存为不同尺寸的ico文件
        sizes = [(16, 16), (32, 32), (48, 48)]
        images = []
        
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)
        
        # 保存为ico文件
        images[0].save('icon.ico', format='ICO', sizes=[(img.width, img.height) for img in images])
        print("✅ 图标文件 icon.ico 创建成功")
        
        # 也保存为PNG用于预览
        img.save('icon.png', 'PNG')
        print("✅ PNG预览文件 icon.png 创建成功")
        
        return True
        
except ImportError:
    def create_icon():
        # 如果PIL不可用，创建说明文件
        with open('icon_info.txt', 'w', encoding='utf-8') as f:
            f.write("QR Scanner 图标文件说明\n")
            f.write("=" * 30 + "\n\n")
            f.write("本项目需要一个图标文件 (icon.ico) 用于Windows可执行文件。\n\n")
            f.write("您可以:\n")
            f.write("1. 安装PIL库来自动生成图标:\n")
            f.write("   pip install Pillow\n")
            f.write("   python create_icon.py\n\n")
            f.write("2. 手动创建或下载一个32x32的ico文件，命名为 icon.ico\n\n")
            f.write("3. 使用在线工具创建图标:\n")
            f.write("   - favicon.io\n")
            f.write("   - convertio.co\n")
            f.write("   - icoconvert.com\n\n")
            f.write("4. 如果不提供图标，程序将使用默认的Python图标\n")
        
        print("⚠️ PIL库未安装，已创建图标说明文件: icon_info.txt")
        print("💡 运行 'pip install Pillow' 然后重新运行此脚本来创建图标")
        return False

if __name__ == "__main__":
    print("🎨 QR Scanner 图标生成器")
    create_icon() 