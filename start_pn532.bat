@echo off
REM PN532分页导航启动脚本

cd /d "%~dp0"

echo === PN532分页导航系统 ===
echo 正在启动...

REM 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ 虚拟环境已激活
) else (
    echo ❌ 找不到虚拟环境
    pause
    exit /b 1
)

REM 启动PN532控制器
python pn532_controller.py

echo PN532控制器已停止
pause
