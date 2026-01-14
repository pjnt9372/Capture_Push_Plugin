# -*- coding: utf-8 -*-
"""
使用 PyInstaller 打包 installer.py
"""

import subprocess
import sys
from pathlib import Path

# 强制设置 stdout 为 UTF-8 以避免在 Windows CI 环境下出现编码错误
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    print("=" * 60)
    print("打包 installer.py 为独立可执行文件")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    installer_py = project_root / "installer.py"
    
    if not installer_py.exists():
        print(f"✗ 找不到 {installer_py}")
        sys.exit(1)
    
    # 确定 PyInstaller 路径
    if sys.platform.startswith('win'):
        pyinstaller_path = project_root / ".venv" / "Scripts" / "pyinstaller.exe"
    else:
        pyinstaller_path = project_root / ".venv" / "bin" / "pyinstaller"
    
    # 检查虚拟环境中的 PyInstaller
    if pyinstaller_path.exists():
        pyinstaller_cmd = str(pyinstaller_path)
    else:
        # 回退到系统 PyInstaller
        pyinstaller_cmd = "pyinstaller"
    
    # PyInstaller 参数
    cmd = [
        pyinstaller_cmd,
        "--onefile",                    # 打包成单个文件
        "--console",                    # 显示控制台窗口
        "--name=Capture_Push_Installer", # 输出文件名
        "--icon=NONE",                  # 暂时不设置图标
        "--clean",                      # 清理临时文件
        "--noupx",                      # 不使用 UPX 压缩（减少压缩时间和内存）
        "--exclude-module=matplotlib",  # 排除不需要的大模块
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=tkinter",     # 排除 tkinter（不需要 GUI）
        str(installer_py)
    ]
    
    print("\n运行 PyInstaller...")
    print(f"命令: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=str(project_root))
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✓ 打包成功！")
        print(f"输出位置: dist/Capture_Push_Installer.exe")
        print("=" * 60)
    else:
        print("\n✗ 打包失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
