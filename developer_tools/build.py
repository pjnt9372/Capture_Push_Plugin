# -*- coding: utf-8 -*-
"""
Capture_Push 综合构建脚本
1. 准备便携式 Python 环境 (.venv)
2. 收集所有必要的程序文件到 build/ 目录
3. 为 Inno Setup 准备最终的打包目录
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess
import hashlib

from pathlib import Path
from datetime import datetime

def log(msg):
    print(f"[*] {msg}", flush=True)

def error(msg):
    print(f"[!] 错误: {msg}", file=sys.stderr)
    sys.exit(1)

def copy_tree(src, dst):
    if not src.exists():
        log(f"跳过不存在的目录: {src}")
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    log(f"已复制: {src.name} -> {dst}")

def get_file_hash(filepath):
    """计算文件的 SHA256 哈希值"""
    if not filepath.exists():
        return None
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def download_with_cache(url, cache_path, expected_hash=None):
    """
    下载文件并使用缓存
    :param url: 下载链接
    :param cache_path: 缓存路径
    :param expected_hash: 期望的哈希值（可选）
    :return: 是否使用了缓存
    """
    # 检查缓存文件是否存在且有效
    if cache_path.exists():
        if expected_hash:
            # 如果指定了期望哈希值，验证缓存文件
            actual_hash = get_file_hash(cache_path)
            if actual_hash == expected_hash:
                log(f"使用本地缓存: {cache_path.name}")
                return True
            else:
                log(f"缓存文件损坏或过期，重新下载: {cache_path.name}")
                cache_path.unlink()  # 删除无效缓存
        else:
            # 没有指定哈希值，直接使用缓存
            log(f"使用本地缓存: {cache_path.name}")
            return True

    # 缓存不存在或无效，进行下载
    log(f"正在下载: {url.split('/')[-1]}...")
    try:
        urllib.request.urlretrieve(url, cache_path)
        log(f"下载完成: {cache_path.name}")
        return False
    except Exception as e:
        error(f"下载失败: {e}")

def install_dependencies_with_cache(venv_dir, requirements_file, pip_cache_dir):
    """使用本地缓存安装依赖"""
    log("安装项目依赖 (使用本地缓存)...")
    
    if not requirements_file.exists():
        log("[!] requirements.txt 不存在，跳过依赖安装")
        return
    
    # 首先尝试从缓存安装
    cmd = [
        str(venv_dir / "python.exe"), "-m", "pip", "install",
        "-r", str(requirements_file),
        "--cache-dir", str(pip_cache_dir),
        "--find-links", str(pip_cache_dir),  # 优先使用本地缓存
        "--prefer-binary",  # 优先使用预编译的二进制包
        "--no-index",  # 只使用本地缓存/链接，不访问网络
        "--timeout", "10"  # 设置超时时间
    ]
    
    try:
        # 先尝试仅使用本地缓存安装
        log("尝试使用本地缓存安装依赖...")
        subprocess.run(cmd, cwd=venv_dir, check=True)
        log("成功从本地缓存安装依赖")
    except subprocess.CalledProcessError:
        # 如果本地缓存安装失败，允许从网络下载
        log("本地缓存安装失败，允许从网络下载...")
        cmd_net = [
            str(venv_dir / "python.exe"), "-m", "pip", "install",
            "-r", str(requirements_file),
            "--cache-dir", str(pip_cache_dir),
            "--find-links", str(pip_cache_dir),
            "--prefer-binary",
            "--timeout", "300"  # 更长的超时时间用于网络下载
        ]
        subprocess.run(cmd_net, cwd=venv_dir, check=True)
        log("成功安装依赖（部分从网络下载）")

def main():
    project_root = Path(__file__).parent.parent.absolute()
    build_dir = project_root / "build"
    venv_dir = build_dir / ".venv"
    requirements_file = project_root / "requirements.txt"
    
    # 缓存目录配置
    cache_dir = project_root / "developer_tools" / "build_cache"
    cache_dir.mkdir(exist_ok=True)
    
    # 嵌入式 Python 配置
    py_version = "3.11.9"
    py_url = f"https://www.python.org/ftp/python/{py_version}/python-{py_version}-embed-amd64.zip"
    zip_path = cache_dir / f"python-{py_version}-embed-amd64.zip"
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = venv_dir / "get-pip.py"
    cached_get_pip = cache_dir / "get-pip.py"
    pip_cache_dir = cache_dir / "pip_cache"
    pip_cache_dir.mkdir(exist_ok=True)

    log("=" * 60)
    log(f"开始构建隔离环境 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"项目根目录: {project_root}")
    log(f"隔离构建空间: {build_dir}")
    log("=" * 60)

    # 1. 准备构建目录
    if not build_dir.exists():
        build_dir.mkdir(parents=True)
    
    # 2. 准备便携式 Python 环境 (在 build 目录下)
    # 如果 .venv 已存在且满足要求，尝试增量更新而不是全部删除
    # 但为了确保 100% 隔离，这里依然保留逻辑，主要通过 pip 缓存加速
    if venv_dir.exists():
        log(f"发现已有 .venv，将进行清理以确保隔离环境纯净...")
        shutil.rmtree(venv_dir)
    venv_dir.mkdir(parents=True, exist_ok=True)

    # 使用改进的缓存机制下载 Python
    download_with_cache(py_url, zip_path)

    log("正在解压 Python 核心...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(venv_dir)

    log("配置 ._pth 文件以支持 site-packages...")
    pth_files = list(venv_dir.glob("python*._pth"))
    if pth_files:
        pth_file = pth_files[0]
        with open(pth_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(pth_file, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line.replace("#import site", "import site"))

    log("准备 pip...")
    # 使用改进的缓存机制下载 get-pip.py
    download_with_cache(get_pip_url, cached_get_pip)
    shutil.copy2(cached_get_pip, get_pip_path)
    
    subprocess.run([str(venv_dir / "python.exe"), str(get_pip_path), "--no-warn-script-location"], cwd=venv_dir, check=True)
    os.remove(get_pip_path)

    # 安装项目依赖（使用改进的缓存机制）
    install_dependencies_with_cache(venv_dir, requirements_file, pip_cache_dir)
    
    # 3. 同步源码到构建空间 (保持与仓库相同的相对结构，以便 .iss 无需修改即可运行)
    log("正在同步组件到构建空间...")
    
    # 复制 core 目录，但只保留 school/12345 子目录
    if (project_root / "core").exists():
        core_dst = build_dir / "core"
        copy_tree(project_root / "core", core_dst)
        
        # 清理 school 目录，只保留 12345 目录
        school_dir = core_dst / "school"
        if school_dir.exists():
            for school_subdir in school_dir.iterdir():
                if school_subdir.is_dir() and school_subdir.name != "12345":
                    shutil.rmtree(school_subdir)
                    log(f"已移除非12345的学校目录: {school_subdir.name}")
        
        # 清理 plugins/school 目录，只保留 12345 目录（如果存在）
        plugins_school_dir = core_dst / "plugins" / "school"
        if plugins_school_dir.exists():
            for school_subdir in plugins_school_dir.iterdir():
                if school_subdir.is_dir() and school_subdir.name != "12345":
                    shutil.rmtree(school_subdir)
                    log(f"已移除非12345的学校插件目录: {school_subdir.name}")
    
    copy_tree(project_root / "gui", build_dir / "gui")
    copy_tree(project_root / "resources", build_dir / "resources")
    
    # 复制必要文件到 build 根目录
    files_to_copy = ["VERSION", "config.ini", "generate_config.py", "Capture_Push_Setup.iss", "Capture_Push_Lite_Setup.iss", "ChineseSimplified.isl"]
    for f_name in files_to_copy:
        src_f = project_root / f_name
        if src_f.exists():
            shutil.copy2(src_f, build_dir / f_name)
            log(f"已同步: {f_name}")

    # 4. 确保语言包资源存在 (使用本地缓存)
    cached_isl = cache_dir / "ChineseSimplified.isl"
    isl_file = build_dir / "ChineseSimplified.isl"
    
    isl_url = "https://raw.githubusercontent.com/kira-96/Inno-Setup-Chinese-Simplified-Translation/master/ChineseSimplified.isl"
    # 使用改进的缓存机制下载语言包
    download_with_cache(isl_url, cached_isl)
    
    if cached_isl.exists():
        shutil.copy2(cached_isl, isl_file)
        log("已同步语言包到构建目录")

    # 5. 尝试复制现有的托盘程序（如果存在）
    tray_exe_src = project_root / "tray" / "build" / "Release" / "Capture_Push_tray.exe"
    iss_tray_path = build_dir / "tray" / "build" / "Release"
    iss_tray_path.mkdir(parents=True, exist_ok=True)
    
    if tray_exe_src.exists():
        shutil.copy2(tray_exe_src, iss_tray_path / "Capture_Push_tray.exe")
        log("已复制托盘程序到打包目录")
    else:
        log("[!] 提示: 托盘程序不存在，可能需要先单独构建 C++ 部分。")

    log("=" * 60)
    log("构建空间准备就绪！")
    log("打包指令:")
    log(f"完整版: ISCC build\\Capture_Push_Setup.iss")
    log(f"轻量版: ISCC build\\Capture_Push_Lite_Setup.iss")
    log("=" * 60)

if __name__ == "__main__":
    if sys.platform != "win32":
        print("[!] 该脚本仅支持 Windows 平台。")
        sys.exit(1)
    main()