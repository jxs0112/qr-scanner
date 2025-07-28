# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 添加pyzbar相关的数据文件和动态链接库
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 收集pyzbar的数据文件和动态库
pyzbar_datas = collect_data_files('pyzbar')
pyzbar_binaries = collect_dynamic_libs('pyzbar')

datas = [
    ('README.md', '.'),
    ('CAMERA_CONTROL_GUIDE.md', '.'),
]

# 添加pyzbar的数据文件
datas.extend(pyzbar_datas)

# 添加配置文件（如果存在）
if os.path.exists('camera_config.json'):
    datas.append(('camera_config.json', '.'))

# 包含所有必要的隐藏导入
hiddenimports = [
    'cv2', 'numpy', 'pyzbar', 'pyzbar.pyzbar', 'pyzbar.wrapper', 'pyzbar.zbar_library',
    'socket', 'json', 'time', 'warnings', 'logging', 'datetime', 'threading', 'queue', 're',
    'contextlib', 'io', 'ctypes', 'ctypes.util',
    # OpenCV相关
    'cv2.cv2',
    # pyzbar相关的所有依赖
    'pyzbar.locations',
]

a = Analysis(
    ['qr_scanner_optimized.py'],
    pathex=[],
    binaries=pyzbar_binaries,  # 包含pyzbar的动态库
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'pandas', 'PIL', 'IPython',
        'jupyter', 'notebook', 'tornado', 'zmq', 'pyqt5', 'pyqt6',
        'pyside2', 'pyside6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QRScanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version_file='version_info.txt' if os.path.exists('version_info.txt') else None,
) 