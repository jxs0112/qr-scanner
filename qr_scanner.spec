# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件和资源
datas = [
    ('README.md', '.'),
    ('CAMERA_CONTROL_GUIDE.md', '.'),
]

# 尝试包含配置文件（如果存在）
import os
if os.path.exists('camera_config.json'):
    datas.append(('camera_config.json', '.'))

# 隐藏导入（解决一些依赖问题）
hiddenimports = [
    'cv2',
    'numpy',
    'pyzbar',
    'pyzbar.pyzbar',
    'socket',
    'json',
    'time',
    'warnings',
    'logging',
    'datetime',
    'threading',
    'queue',
    're',
    'contextlib',
    'io',
]

a = Analysis(
    ['qr_scanner_optimized.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小文件大小
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
        'tornado',
        'zmq',
        'pyqt5',
        'pyqt6',
        'pyside2',
        'pyside6',
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
    upx=True,  # 使用UPX压缩减小文件大小
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台窗口以显示调试信息
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version_file='version_info.txt' if os.path.exists('version_info.txt') else None,
) 