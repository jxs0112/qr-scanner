#!/bin/bash
# PN532分页导航启动脚本

cd "$(dirname "$0")"

echo "=== PN532分页导航系统 ==="
echo "正在启动..."

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "❌ 找不到虚拟环境"
    exit 1
fi

# 启动PN532控制器
python3 pn532_controller.py

echo "PN532控制器已停止"
