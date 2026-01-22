# -*- coding: utf-8 -*-
"""
生成安装配置信息文件（txt格式）
记录安装路径、注册表项等信息
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 强制设置 stdout 为 UTF-8 以避免在 Windows CI 环境下出现编码错误
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def generate_install_config(install_dir):
    """生成安装配置文件"""
    config_file = Path(install_dir) / "install_config.txt"
    
    config_content = f"""========================================
Capture_Push - 安装配置信息
========================================
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[安装路径]
安装目录: {install_dir}
虚拟环境: {install_dir}\\.venv
Python脚本: {install_dir}\\core
托盘程序: {install_dir}\\Capture_Push_tray.exe
配置文件: {install_dir}\\config.ini

[注册表项]
程序路径注册:
  位置: HKLM\\SOFTWARE\\Capture_Push
  键名: InstallPath
  键值: {install_dir}

自启动托盘程序:
  位置: HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
  键名: Capture_Push_Tray
  键值: {install_dir}\Capture_Push_tray.exe

[虚拟环境]
Python解释器: {install_dir}\\.venv\\Scripts\\python.exe
Pythonw（无窗口）: {install_dir}\\.venv\\Scripts\\pythonw.exe
Pip: {install_dir}\\.venv\\Scripts\\pip.exe

[已安装依赖]
- requests
- beautifulsoup4
- pyside6

[安装源]
使用阿里云PyPI镜像: https://mirrors.aliyun.com/pypi/simple/

[卸载说明]
1. 运行卸载程序: {install_dir}\\unins000.exe
2. 或手动删除整个安装目录
3. 清理注册表项（可选）:
   - 删除 HKLM\SOFTWARE\Capture_Push
   - 删除 HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\Capture_Push_Tray

========================================
注意事项
========================================
1. 请勿手动修改虚拟环境内容
2. 如需重新安装依赖，运行 install_deps.bat
3. 配置文件位于 config.ini
4. 日志文件: app.log

========================================
"""
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"配置文件已生成: {config_file}")
    return True

def main():
    if len(sys.argv) > 1:
        install_dir = sys.argv[1]
    else:
        install_dir = os.path.dirname(os.path.abspath(__file__))
    
    generate_install_config(install_dir)

if __name__ == "__main__":
    main()
