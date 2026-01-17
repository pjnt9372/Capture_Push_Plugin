# -*- coding: utf-8 -*-
"""
本地构建便携式 Python 环境脚本
该脚本模拟 GitHub Action 的构建过程，下载嵌入式 Python 并配置 pip 和依赖。
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess
from pathlib import Path

def log(msg):
    print(f"[*] {msg}", flush=True)

def error(msg):
    print(f"[!] 错误: {msg}", file=sys.stderr)
    sys.exit(1)

def main():
    project_root = Path(__file__).parent.parent.absolute()
    venv_dir = project_root / ".venv"
    requirements_file = project_root / "requirements.txt"
    
    py_version = "3.11.9"
    py_url = f"https://www.python.org/ftp/python/{py_version}/python-{py_version}-embed-amd64.zip"
    zip_path = project_root / "python_embed.zip"
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = venv_dir / "get-pip.py"

    log(f"项目根目录: {project_root}")
    
    # 1. 清理旧环境
    if venv_dir.exists():
        log("清理旧的 .venv 目录...")
        shutil.rmtree(venv_dir)
    venv_dir.mkdir(parents=True, exist_ok=True)

    # 2. 下载嵌入式 Python
    if not zip_path.exists():
        log(f"正在从 {py_url} 下载嵌入式 Python...")
        try:
            urllib.request.urlretrieve(py_url, zip_path)
        except Exception as e:
            error(f"下载失败: {e}")
    else:
        log("使用本地已存在的 python_embed.zip")

    # 3. 解压
    log(f"解压到 {venv_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(venv_dir)

    # 4. 修改 ._pth 文件以允许使用 site-packages
    log("配置 ._pth 文件以允许使用 site-packages...")
    pth_files = list(venv_dir.glob("python*._pth"))
    if not pth_files:
        error("找不到 ._pth 文件")
    
    pth_file = pth_files[0]
    with open(pth_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open(pth_file, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.strip() == "#import site":
                f.write("import site\n")
            else:
                f.write(line)

    # 5. 下载并安装 pip
    python_exe = venv_dir / "python.exe"
    log("下载 get-pip.py...")
    try:
        urllib.request.urlretrieve(get_pip_url, get_pip_path)
    except Exception as e:
        error(f"下载 get-pip.py 失败: {e}")

    log("正在安装 pip (这可能需要一点时间)...")
    subprocess_cmd = [str(python_exe), str(get_pip_path), "--no-warn-script-location"]
    import subprocess
    result = subprocess.run(subprocess_cmd, cwd=venv_dir)
    if result.returncode != 0:
        error("安装 pip 失败")

    # 6. 安装 requirements.txt 中的依赖
    if requirements_file.exists():
        log(f"正在安装依赖项: {requirements_file}...")
        result = subprocess.run([str(python_exe), "-m", "pip", "install", "-r", str(requirements_file), "--no-warn-script-location"], cwd=venv_dir)
        if result.returncode != 0:
            error("依赖安装失败")
    else:
        log("未发现 requirements.txt，跳过依赖安装")

    # 7. 清理
    log("正在清理临时文件...")
    if get_pip_path.exists():
        os.remove(get_pip_path)
    # 询问是否删除 zip
    # os.remove(zip_path) 

    log("=" * 40)
    log("便携式 Python 环境构建成功！")
    log(f"位置: {venv_dir}")
    log("=" * 40)

if __name__ == "__main__":
    if sys.platform != "win32":
        print("[!] 该脚本仅支持 Windows 平台。")
        sys.exit(1)
    main()
