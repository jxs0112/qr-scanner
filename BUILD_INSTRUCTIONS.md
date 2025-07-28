# 🏗️ QR Scanner Windows构建指南

## 📦 自动构建 (推荐)

### 使用GitHub Actions

1. **推送代码到GitHub**：
   ```bash
   git add .
   git commit -m "Add Windows build support"
   git push origin main
   ```

2. **自动触发构建**：
   - 每次推送到 `main` 或 `master` 分支都会自动构建
   - 也可以在GitHub仓库的 Actions 页面手动触发

3. **下载构建结果**：
   - 进入GitHub仓库的 **Actions** 页面
   - 点击最新的构建任务
   - 在 **Artifacts** 部分下载 `QRScanner-Windows`

### 创建发布版本

1. **创建Git标签**：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **自动创建Release**：
   - GitHub Actions会自动创建Release
   - 包含完整的Windows可执行包
   - 自动生成发布说明

## 🔨 本地构建

### Windows环境

1. **运行构建脚本**：
   ```cmd
   build_windows.bat
   ```

2. **手动构建**：
   ```cmd
   # 安装依赖
   pip install -r requirements.txt
   pip install pyinstaller
   
   # 使用spec文件构建
   pyinstaller qr_scanner.spec
   
   # 或使用命令行参数
   pyinstaller --onefile --console --name "QRScanner" qr_scanner_optimized.py
   ```

## 📋 构建配置说明

### PyInstaller配置 (qr_scanner.spec)

- **单文件打包**: 所有依赖打包到一个exe文件
- **控制台模式**: 保留命令行窗口显示调试信息
- **UPX压缩**: 减小文件大小
- **排除模块**: 排除不需要的大型库
- **版本信息**: 包含文件版本和描述

### GitHub Actions配置 (.github/workflows/build.yml)

- **自动触发**: push、PR、手动触发
- **Python 3.11**: 使用稳定的Python版本
- **缓存依赖**: 加速构建过程
- **多文件打包**: 包含文档和配置文件
- **自动发布**: 标签推送时自动创建Release

## 🎯 输出文件说明

构建完成后会生成以下文件：

```
release/
├── QRScanner.exe              # 主程序
├── start_qr_scanner_4k.bat    # 4K模式启动脚本
├── start_qr_scanner_1080p.bat # 1080p模式启动脚本
├── start_qr_scanner_720p.bat  # 720p模式启动脚本
├── 使用说明.txt                # 中文使用说明
├── README.md                   # 项目说明
├── CAMERA_CONTROL_GUIDE.md     # 摄像头控制指南
└── camera_config.json          # 配置文件(如果存在)
```

## 🔧 故障排除

### 构建失败

1. **依赖问题**：
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt --force-reinstall
   ```

2. **PyInstaller问题**：
   ```cmd
   pip install --upgrade pyinstaller
   ```

3. **内存不足**：
   - 关闭其他程序
   - 使用 `--noupx` 参数禁用压缩

### 运行时错误

1. **缺少DLL**：
   - 在目标系统安装 Visual C++ 2019 Redistributable
   - 或使用 `--onedir` 模式打包

2. **摄像头问题**：
   - 检查摄像头权限
   - 确保摄像头驱动正常
   - 尝试不同的摄像头索引

## ⚡ 优化建议

### 减小文件大小

1. **排除更多模块**：
   ```python
   excludes=[
       'tkinter', 'matplotlib', 'scipy', 'pandas',
       'PIL', 'IPython', 'jupyter', 'notebook'
   ]
   ```

2. **使用UPX压缩**：
   ```python
   upx=True
   ```

3. **分离资源文件**：
   ```python
   # 使用 --onedir 代替 --onefile
   ```

### 提高性能

1. **启用优化**：
   ```cmd
   python -O -m PyInstaller qr_scanner.spec
   ```

2. **预编译导入**：
   ```python
   hiddenimports=['cv2', 'numpy', 'pyzbar']
   ```

## 📈 CI/CD集成

### 多平台构建

可以扩展GitHub Actions支持多平台：

```yaml
strategy:
  matrix:
    os: [windows-latest, ubuntu-latest, macos-latest]
```

### 自动测试

在构建前添加测试步骤：

```yaml
- name: Run tests
  run: |
    python -m pytest tests/
```

### 发布到多个平台

- GitHub Releases
- PyPI
- Windows Store
- 自建下载服务器

---

💡 **提示**: 首次构建可能需要较长时间下载依赖，后续构建会利用缓存加速。 