@echo off
echo === QR Scanner Windows构建脚本 ===
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

:: 检查是否在虚拟环境中
echo 检查Python环境...
python -c "import sys; print('虚拟环境' if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else '系统环境')"

:: 安装依赖
echo.
echo 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

:: 安装PyInstaller
echo.
echo 安装PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo 错误: PyInstaller安装失败
    pause
    exit /b 1
)

:: 清理旧的构建文件
echo.
echo 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release rmdir /s /q release

:: 构建可执行文件
echo.
echo 开始构建可执行文件...
if exist qr_scanner.spec (
    echo 使用spec文件构建...
    pyinstaller qr_scanner.spec
) else (
    echo 使用命令行参数构建...
    pyinstaller --onefile --console --name "QRScanner" --add-data "README.md;." --add-data "CAMERA_CONTROL_GUIDE.md;." qr_scanner_optimized.py
)

if errorlevel 1 (
    echo 错误: 构建失败
    pause
    exit /b 1
)

:: 创建发布目录
echo.
echo 创建发布包...
mkdir release

:: 复制文件
copy dist\QRScanner.exe release\
copy README.md release\
copy CAMERA_CONTROL_GUIDE.md release\
if exist camera_config.json copy camera_config.json release\

:: 创建启动脚本
echo @echo off > release\start_qr_scanner_4k.bat
echo echo === QR Scanner - 4K模式 === >> release\start_qr_scanner_4k.bat
echo echo 启动4K QR扫描器... >> release\start_qr_scanner_4k.bat
echo QRScanner.exe ultra_hd --debug >> release\start_qr_scanner_4k.bat
echo pause >> release\start_qr_scanner_4k.bat

echo @echo off > release\start_qr_scanner_1080p.bat
echo echo === QR Scanner - 1080p模式 === >> release\start_qr_scanner_1080p.bat
echo echo 启动1080p QR扫描器... >> release\start_qr_scanner_1080p.bat
echo QRScanner.exe full_hd >> release\start_qr_scanner_1080p.bat
echo pause >> release\start_qr_scanner_1080p.bat

echo @echo off > release\start_qr_scanner_720p.bat
echo echo === QR Scanner - 720p模式 === >> release\start_qr_scanner_720p.bat
echo echo 启动720p QR扫描器... >> release\start_qr_scanner_720p.bat
echo QRScanner.exe high >> release\start_qr_scanner_720p.bat
echo pause >> release\start_qr_scanner_720p.bat

:: 创建使用说明
echo QR Scanner - Windows可执行版本 > release\使用说明.txt
echo. >> release\使用说明.txt
echo === 快速启动 === >> release\使用说明.txt
echo 1. start_qr_scanner_4k.bat    - 4K高质量模式 (推荐) >> release\使用说明.txt
echo 2. start_qr_scanner_1080p.bat - 1080p平衡模式 >> release\使用说明.txt
echo 3. start_qr_scanner_720p.bat  - 720p高速模式 >> release\使用说明.txt
echo. >> release\使用说明.txt
echo === 手动运行 === >> release\使用说明.txt
echo 命令格式: QRScanner.exe [分辨率] [选项] >> release\使用说明.txt
echo. >> release\使用说明.txt
echo 分辨率参数: >> release\使用说明.txt
echo   ultra_hd  - 4K (3840x2160) >> release\使用说明.txt
echo   full_hd   - 1080p (1920x1080) >> release\使用说明.txt
echo   high      - 720p (1280x720) >> release\使用说明.txt
echo   medium    - 480p (640x480) >> release\使用说明.txt
echo   low       - 240p (320x240) >> release\使用说明.txt
echo. >> release\使用说明.txt
echo 选项参数: >> release\使用说明.txt
echo   --debug   - 启用调试模式 >> release\使用说明.txt
echo   --fps=数值 - 设置目标帧率 >> release\使用说明.txt
echo. >> release\使用说明.txt
echo === 按键控制 === >> release\使用说明.txt
echo   q - 退出程序 >> release\使用说明.txt
echo   d - 切换调试模式 >> release\使用说明.txt
echo   r - 调整检测区域 >> release\使用说明.txt
echo   i - 显示摄像头信息 >> release\使用说明.txt
echo   h - 显示性能提示 >> release\使用说明.txt
echo   o - 切换检测器 >> release\使用说明.txt
echo   a - 自适应优化 >> release\使用说明.txt
echo   s - 简化预处理 >> release\使用说明.txt
echo   c - 清除缓存 >> release\使用说明.txt
echo. >> release\使用说明.txt
echo === 系统要求 === >> release\使用说明.txt
echo - Windows 10/11 (64位推荐) >> release\使用说明.txt
echo - 4GB以上内存 >> release\使用说明.txt
echo - USB摄像头或内置摄像头 >> release\使用说明.txt
echo - 建议使用USB 3.0接口 >> release\使用说明.txt
echo. >> release\使用说明.txt
echo 详细说明请参考 CAMERA_CONTROL_GUIDE.md >> release\使用说明.txt

:: 创建ZIP压缩包
echo.
echo 创建压缩包...
powershell -command "Compress-Archive -Path 'release\*' -DestinationPath 'QRScanner-Windows.zip' -Force"

:: 显示结果
echo.
echo === 构建完成 ===
echo 可执行文件位置: release\QRScanner.exe
echo 压缩包位置: QRScanner-Windows.zip
echo.
echo 文件大小:
dir release\QRScanner.exe | findstr QRScanner.exe
echo.
echo 要测试程序，请运行: release\start_qr_scanner_4k.bat
echo.
pause 