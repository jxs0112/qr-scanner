# NFC翻页功能设置指南

## 概述

NFC翻页功能允许你使用NFC标签或支持NFC的设备来控制翻页操作，提供更便捷的交互方式。

## 系统要求

### 硬件要求
- **NFC读卡器**: 支持PC/SC的NFC读卡器
  - 推荐: ACR122U, PN532, RC522等
  - USB接口NFC读卡器
  - 部分笔记本内置NFC模块

- **NFC标签**: 
  - NTAG213/215/216 (推荐)
  - Mifare Classic 1K/4K
  - ISO14443 Type A/B标签
  - 支持NFC的手机

### 软件要求
```bash
# 安装NFC库
pip install nfcpy

# 可选：键盘模拟 (用于实际翻页)
pip install pynput

# 可选：串口通信
pip install pyserial
```

## 安装和配置

### 1. 安装NFC驱动

#### Linux (Ubuntu/Debian)
```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install libusb-1.0-0-dev libnfc-bin libnfc-dev

# 安装PC/SC服务
sudo apt-get install pcscd pcsc-tools

# 启动PC/SC服务
sudo systemctl start pcscd
sudo systemctl enable pcscd
```

#### macOS
```bash
# 使用Homebrew安装
brew install libnfc

# 或者手动安装PC/SC框架（通常已预装）
# PC/SC框架通常在 /System/Library/Frameworks/PCSC.framework
```

#### Windows
```bash
# 下载并安装NFC读卡器驱动程序
# 通常厂商会提供专用驱动

# 或者使用zadig安装通用驱动
# https://zadig.akeo.ie/
```

### 2. 验证NFC设备

```bash
# 检测NFC设备
python3 -c "import nfc; print(nfc.ContactlessFrontend())"

# 或者使用系统工具
# Linux:
lsusb | grep -i nfc

# macOS:
system_profiler SPUSBDataType | grep -i nfc
```

## 使用方法

### 1. 基本使用

```bash
# 启动NFC翻页控制器
python3 nfc_page_controller.py

# 启动统一接收器（同时支持二维码和NFC）
python3 unified_receiver.py

# 启动二维码扫描器（如果需要）
python3 qr_scanner.py
```

### 2. NFC标签配置

#### 方法一：使用手机NFC应用

1. **下载NFC标签写入应用**:
   - Android: NFC Tools, TagWriter
   - iOS: NFC TagInfo, NFC Tools

2. **写入翻页命令**:
   - 文本记录: "下一页", "上一页", "首页", "末页"
   - 英文: "next", "prev", "first", "last"
   - URL记录: "http://localhost/?page=next"

#### 方法二：使用Python脚本写入

```python
#!/usr/bin/env python3
import nfc

def write_nfc_tag(text_content):
    """写入NFC标签"""
    clf = nfc.ContactlessFrontend()
    
    def connected(tag):
        if tag.ndef:
            # 创建文本记录
            text_record = nfc.ndef.TextRecord(text_content)
            tag.ndef.records = [text_record]
            print(f"已写入: {text_content}")
            return True
        return False
    
    clf.connect(rdwr={'on-connect': connected})
    clf.close()

# 使用示例
if __name__ == "__main__":
    write_nfc_tag("下一页")  # 写入"下一页"命令
```

### 3. 预设标签映射

```python
# 在nfc_page_controller.py中添加预设映射
controller = NFCPageController()

# 添加特定标签ID的映射
controller.add_tag_mapping("04A1B2C3D4E5F6", "next_page")
controller.add_tag_mapping("04A1B2C3D4E5F7", "prev_page")
controller.add_tag_mapping("04A1B2C3D4E5F8", "bookmark")

# 查看所有映射
controller.list_tag_mappings()
```

## 支持的命令

| 命令类型 | 中文 | 英文 | 功能描述 |
|---------|------|------|----------|
| next_page | 下一页, 下页 | next, next_page | 翻到下一页 |
| prev_page | 上一页, 上页 | prev, previous | 翻到上一页 |
| first_page | 首页, 第一页 | first, first_page | 跳转到首页 |
| last_page | 末页, 最后一页 | last, last_page | 跳转到末页 |
| bookmark | 书签 | bookmark, mark | 添加书签 |
| menu | 菜单 | menu, index | 打开菜单 |
| exit | 退出 | exit, quit | 退出程序 |
| debug_toggle | 调试 | debug | 切换调试模式 |

## 系统集成

### 与阅读器应用集成

#### 方法一：键盘模拟
```python
from pynput.keyboard import Key, Controller

def simulate_page_turn(command):
    keyboard = Controller()
    
    if command == 'next_page':
        keyboard.press(Key.right)
        keyboard.release(Key.right)
    elif command == 'prev_page':
        keyboard.press(Key.left)  
        keyboard.release(Key.left)
```

#### 方法二：应用API调用
```python
import requests

def call_reader_api(command):
    """调用阅读器应用的API"""
    api_url = "http://localhost:8080/api/page"
    data = {"action": command}
    
    try:
        response = requests.post(api_url, json=data)
        return response.status_code == 200
    except:
        return False
```

#### 方法三：文件监控
```python
import json
import os

def write_command_file(command):
    """写入命令文件供其他程序读取"""
    command_data = {
        "command": command,
        "timestamp": time.time()
    }
    
    with open("page_command.json", "w") as f:
        json.dump(command_data, f)
```

## 故障排除

### 常见问题

#### 1. NFC设备无法识别
```bash
# 检查设备权限 (Linux)
sudo usermod -a -G dialout $USER
sudo udevadm control --reload-rules

# 重新插拔NFC设备
# 检查USB连接
lsusb
```

#### 2. 权限问题
```bash
# Linux: 添加udev规则
sudo nano /etc/udev/rules.d/99-nfc.rules

# 添加以下内容 (以ACR122U为例):
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0666"

# 重新加载规则
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 3. Python库安装问题
```bash
# 如果nfcpy安装失败，尝试:
pip install --upgrade setuptools
pip install cython
pip install nfcpy

# 或者使用conda:
conda install -c conda-forge nfcpy
```

#### 4. NFC标签读取失败
- 确保标签距离读卡器足够近（通常<5cm）
- 检查标签是否损坏
- 尝试不同类型的NFC标签
- 确认标签格式为NDEF

### 调试模式

```bash
# 启用详细日志
python3 nfc_page_controller.py --debug

# 测试NFC设备
python3 -c "
import nfc
clf = nfc.ContactlessFrontend()
print('NFC设备:', clf)
tag = clf.connect(rdwr={'on-connect': lambda tag: print('检测到标签:', tag)})
clf.close()
"
```

### 性能优化

#### 1. 减少扫描间隔
```python
# 在nfc_page_controller.py中调整
self.tag_cooldown = 0.5  # 减少冷却时间
```

#### 2. 限制标签类型
```python
# 只扫描特定类型的标签
tag = clf.connect(rdwr={
    'targets': ['106A', '106B'],  # 只扫描ISO14443 Type A/B
    'on-connect': self.process_nfc_tag
})
```

## 扩展功能

### 1. 多标签识别
```python
# 同时处理多个标签
def process_multiple_tags(self, tags):
    for tag in tags:
        self.process_nfc_tag(tag)
```

### 2. 手机NFC支持
```python
# 识别手机NFC (Android Beam等)
def handle_phone_nfc(self, data):
    # 处理手机发送的NDEF消息
    pass
```

### 3. 自定义协议
```python
# 自定义命令协议
def parse_custom_protocol(self, tag_data):
    # 解析自定义格式的命令
    # 例如: "CMD:NEXT:PAGE:1"
    pass
```

## 最佳实践

1. **标签管理**: 为不同功能使用不同颜色的标签
2. **位置放置**: 将常用命令标签放在便于触及的位置
3. **备份配置**: 保存标签映射配置到文件
4. **安全考虑**: 避免在标签中存储敏感信息
5. **电池优化**: NFC功耗很低，但长期使用建议使用USB供电设备

## 参考资源

- [nfcpy官方文档](https://nfcpy.readthedocs.io/)
- [NFC Forum技术规范](https://nfc-forum.org/our-work/specification-releases/)
- [PC/SC Workgroup](https://www.pcscworkgroup.com/)
- [libnfc项目](http://nfc-tools.org/index.php/Libnfc) 