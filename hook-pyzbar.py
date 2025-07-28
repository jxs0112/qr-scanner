# PyInstaller hook for pyzbar
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# 收集pyzbar的所有数据文件
datas = collect_data_files('pyzbar')

# 收集pyzbar的动态链接库
binaries = collect_dynamic_libs('pyzbar')

# 收集pyzbar的所有子模块
hiddenimports = collect_submodules('pyzbar')

# 添加额外的隐藏导入
hiddenimports += [
    'pyzbar.pyzbar',
    'pyzbar.wrapper',
    'pyzbar.zbar_library',
    'pyzbar.locations',
] 