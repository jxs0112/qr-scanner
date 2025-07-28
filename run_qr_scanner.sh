#!/bin/bash

# 二维码扫描器启动脚本
echo "=== 二维码扫描器启动脚本 ==="

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "错误：虚拟环境不存在，请先运行 python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查系统依赖
echo "检查系统依赖..."
if ! command -v brew &> /dev/null; then
    echo "警告：未找到 Homebrew，可能需要手动安装 zbar 库"
elif ! brew list zbar &> /dev/null; then
    echo "zbar 库未安装，正在安装..."
    brew install zbar
fi

# 检查Python依赖是否安装
echo "检查Python依赖包..."
python3 -c "import cv2, pyzbar, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Python依赖包未安装，正在安装..."
    pip install -r requirements.txt
fi

# 运行程序
echo "启动二维码扫描器..."
python3 qr_scanner.py 