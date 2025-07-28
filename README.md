# 高级优化版QR码扫描器

一个高性能的QR码扫描器，专门针对4K分辨率优化，支持配置文件和多摄像头切换。

## ✨ 功能特点

### 🚀 性能优化
- **配置文件支持** - 自动保存和加载用户设置
- **多摄像头检测和切换** - 自动检测所有可用摄像头
- **自适应跳帧和区域调整** - 根据性能自动优化
- **OpenCV + pyzbar双重检测** - 最佳识别效果
- **多尺度检测** - 支持不同距离的QR码
- **智能结果缓存** - 避免重复计算
- **实时性能监控** - 动态调整参数

### 📷 摄像头支持
- 自动检测所有可用摄像头
- 运行时热切换摄像头
- 保存每个摄像头的最佳设置
- 支持macOS和Windows

## 🛠 安装

```bash
pip install -r requirements.txt
```

## 📖 使用方法

### 基本使用
```bash
# 使用默认配置启动
python qr_scanner_optimized.py

# 指定分辨率
python qr_scanner_optimized.py ultra_hd

# 指定摄像头
python qr_scanner_optimized.py --camera=1

# 指定配置文件
python qr_scanner_optimized.py --config=my_config.json

# 开启调试模式
python qr_scanner_optimized.py --debug
```

### 配置文件
程序会自动创建和使用 `camera_config.json` 配置文件，包含：

```json
{
  "default_resolution": "ultra_hd",
  "default_camera_index": 0,
  "udp_host": "127.0.0.1",
  "udp_port": 8888,
  "performance": {
    "adaptive_skip_interval": 2,
    "detection_region_scale": 0.4,
    "use_opencv_qr": true,
    "dynamic_resolution": true
  }
}
```

## ⌨️ 按键控制

### 基本控制
- `q` - 退出程序
- `d` - 切换调试模式
- `s` - 切换简化预处理
- `o` - 切换OpenCV检测器
- `a` - 切换自适应优化
- `r` - 调整检测区域大小
- `c` - 清除检测缓存

### 摄像头控制
- `n` - 切换到下一个摄像头
- `p` - 切换到上一个摄像头
- `l` - 列出所有可用摄像头
- `x` - 重新检测摄像头

### 信息和配置
- `i` - 显示摄像头信息
- `h` - 显示性能提示
- `w` - 切换警告显示
- `z` - 保存当前配置到文件

## 🎯 支持的分辨率

- `low` - 320×240
- `medium` - 640×480
- `high` - 1280×720
- `full_hd` - 1920×1080
- `ultra_hd` - 3840×2160

也可以在配置文件中定义自定义分辨率。

## 🔧 性能调优

### 多摄像头环境
程序会自动：
1. 检测所有可用摄像头
2. 测试每个摄像头的能力
3. 保存最佳设置到配置文件
4. 支持运行时切换

### 性能优化建议
- 使用 `ultra_hd` 分辨率获得最佳识别效果
- 在低性能设备上使用 `full_hd` 或更低分辨率
- 调整检测区域大小平衡性能和准确性
- 开启OpenCV检测器获得更快速度

## 📊 输出格式

UDP数据包格式：
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "qr_content": "扫描到的内容",
  "source": "optimized_qr_scanner_v2"
}
```

## ⚠️ 已知限制

- macOS上的摄像头控制受系统安全限制
- 建议使用系统相机应用预先调整摄像头设置
- 某些USB摄像头可能需要额外驱动

## 🏗 项目结构

```
camera/
├── qr_scanner_optimized.py    # 主程序
├── camera_config.json         # 配置文件
├── requirements.txt           # 依赖列表
└── README.md                  # 说明文档
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！ 