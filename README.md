# 二维码识别UDP发送程序

这是一个使用Python编写的二维码识别程序，它通过摄像头实时识别二维码内容，并将识别结果通过UDP包发送到指定的目标地址。

## 功能特点

- 🎥 实时摄像头二维码识别
- 📡 UDP包发送功能
- 🔄 防重复发送机制
- 🖼️ 可视化二维码边框显示
- 📝 JSON格式数据传输
- ⚡ 高性能实时处理
- 🎨 **增强的图像预处理** - 支持12种不同的图像处理方法
- 🔍 **调试模式** - 可视化显示所有预处理结果
- 🌈 **彩色背景优化** - 专门针对有颜色背景的二维码进行优化

## 新增功能

### 增强的二维码识别

程序现在使用多种图像预处理方法来提高二维码识别效果，特别是对于有颜色背景的二维码：

1. **原始图像** - 直接识别
2. **灰度化** - 转换为灰度图像
3. **直方图均衡** - 自适应直方图均衡化
4. **高斯模糊** - 去噪处理
5. **自适应阈值** - 自适应二值化
6. **Otsu二值化** - 自动阈值二值化
7. **形态学操作** - 开运算去噪
8. **对比度增强** - 提高图像对比度
9. **边缘检测** - Canny边缘检测
10. **HSV颜色空间** - HSV颜色空间转换
11. **拉普拉斯锐化** - 图像锐化
12. **双边滤波** - 保持边缘的去噪

### 调试模式

启用调试模式可以实时查看所有预处理方法的效果：

```bash
# 启用调试模式
python3 qr_scanner.py --debug

# 使用高分辨率和调试模式
python3 qr_scanner.py high 0 --debug
```

在调试模式下：
- 按 `d` 键切换调试窗口显示
- 调试窗口显示所有12种预处理方法的结果
- 程序会显示成功识别时使用的预处理方法

## 系统要求

- Python 3.7+
- 摄像头设备
- macOS / Linux / Windows
- **macOS 用户需要安装 Homebrew 和 zbar 库**

## 安装依赖

由于 macOS 的 Python 环境管理限制，建议使用虚拟环境：

### 首先安装系统依赖（macOS 用户）

```bash
# 安装 Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 zbar 库
brew install zbar
```

### 方法一：使用虚拟环境（推荐）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 方法二：使用启动脚本

```bash
# 直接运行启动脚本（会自动处理虚拟环境）
./run_qr_scanner.sh
```

### 依赖包说明

- `opencv-python`: OpenCV库，用于摄像头操作和图像处理
- `pyzbar`: 二维码解码库
- `numpy`: 数值计算库

## 使用方法

### 1. 基本运行

```bash
# 使用虚拟环境运行
source venv/bin/activate
python3 qr_scanner.py
```

或者使用启动脚本：

```bash
./run_qr_scanner.sh
```

### 2. 调整分辨率

```bash
# 查看可用分辨率选项
python3 qr_scanner.py --list

# 使用预定义分辨率
python3 qr_scanner.py low          # 320x240 (低分辨率)
python3 qr_scanner.py medium       # 640x480 (中等分辨率，默认)
python3 qr_scanner.py high         # 1280x720 (高分辨率)
python3 qr_scanner.py full_hd      # 1920x1080 (全高清)
python3 qr_scanner.py ultra_hd     # 3840x2160 (4K)

# 指定摄像头索引
python3 qr_scanner.py medium 1     # 使用摄像头1，中等分辨率
```

### 3. 调试模式

```bash
# 启用调试模式
python3 qr_scanner.py --debug

# 使用高分辨率和调试模式
python3 qr_scanner.py high 0 --debug

# 使用中等分辨率、摄像头1和调试模式
python3 qr_scanner.py medium 1 --debug
```

### 4. 测试二维码识别效果

```bash
# 运行测试脚本
python3 test_qr_recognition.py
```

测试脚本可以实时测试不同预处理方法对二维码识别的效果。

### 5. 测试摄像头分辨率

```bash
# 测试摄像头支持的分辨率
python3 test_camera_resolution.py

# 测试特定摄像头
python3 test_camera_resolution.py 0
```

### 6. 修改UDP目标地址

在 `qr_scanner.py` 文件中修改以下参数：

```python
UDP_HOST = '127.0.0.1'  # 目标主机IP
UDP_PORT = 8888         # 目标端口
```

### 7. 操作说明

- 程序启动后会自动打开摄像头窗口
- 将二维码对准摄像头即可自动识别
- 识别成功后会在控制台显示发送状态和使用的预处理方法
- 按 `q` 键退出程序
- 在调试模式下，按 `d` 键切换调试窗口显示

## UDP数据格式

程序发送的UDP包采用JSON格式：

```json
{
    "timestamp": "2024-01-01T12:00:00.000000",
    "qr_content": "二维码内容",
    "source": "qr_scanner"
}
```

### 字段说明

- `timestamp`: 识别时间戳（ISO格式）
- `qr_content`: 二维码内容
- `source`: 数据来源标识

## 程序特性

### 智能识别算法

程序会自动尝试所有12种预处理方法，选择能够成功识别二维码的方法。这大大提高了对有颜色背景二维码的识别成功率。

### 防重复发送

程序内置防重复发送机制，相同的二维码内容在1秒内不会重复发送UDP包。

### 可视化显示

- 绿色边框：标识识别到的二维码
- 文本标签：显示二维码内容
- 调试窗口：显示所有预处理方法的结果（调试模式）

### 错误处理

- 摄像头初始化失败检测
- UDP发送异常处理
- 优雅的程序退出机制
- 预处理方法异常处理

## 测试UDP接收

可以使用以下Python脚本测试UDP包接收：

```python
import socket
import json

def udp_receiver(host='127.0.0.1', port=8888):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"UDP接收器启动，监听 {host}:{port}")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            message = json.loads(data.decode('utf-8'))
            print(f"收到来自 {addr} 的数据: {message}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"接收错误: {e}")
    
    sock.close()

if __name__ == "__main__":
    udp_receiver()
```

## 故障排除

### 摄像头无法打开

- 检查摄像头是否被其他程序占用
- 确认摄像头权限设置
- 尝试更改摄像头索引（修改 `cv2.VideoCapture(0)` 中的数字）

### 二维码识别失败

- 确保二维码清晰可见
- 调整摄像头焦距和光线
- 检查二维码是否损坏
- **尝试启用调试模式查看预处理效果**
- **对于彩色背景二维码，程序会自动尝试多种预处理方法**

### UDP发送失败

- 检查网络连接
- 确认目标主机和端口可达
- 检查防火墙设置

### 调试模式问题

- 确保系统支持多窗口显示
- 调试窗口可能需要较新的OpenCV版本
- 如果调试窗口显示异常，可以尝试调整窗口大小

## 性能优化建议

1. **分辨率选择**: 对于快速识别，建议使用 `medium` 或 `high` 分辨率
2. **调试模式**: 仅在需要调试时启用，会消耗更多CPU资源
3. **光线条件**: 良好的光线条件有助于提高识别成功率
4. **摄像头质量**: 高质量的摄像头可以提供更好的图像质量

## 许可证

本项目采用MIT许可证。 