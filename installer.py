# -*- coding: utf-8 -*-
"""
学业助手 - 安装后首次运行配置
负责下载并安装 Python，创建虚拟环境并安装依赖
只支持命令行模式，输出到控制台
"""

import os
import sys
import subprocess
import locale
import urllib.request
import tempfile
from pathlib import Path
import argparse

# 强制设置 stdout 为 UTF-8 以避免在 Windows CI 环境下出现编码错误
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def detect_region():
    """检测地区，判断是否使用国内镜像"""
    try:
        # 检测系统语言
        lang = locale.getdefaultlocale()[0]
        if lang and 'zh_CN' in lang:
            return 'CN'
        
        # 检测环境变量
        if os.getenv('LANG', '').startswith('zh_CN'):
            return 'CN'
            
        return 'GLOBAL'
    except:
        return 'GLOBAL'


class SilentInstaller:
    """命令行安装器（控制台输出）"""
    
    # Python 下载镜像
    PYTHON_DOWNLOAD_URLS = {
        'CN': {
            'url': 'https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-amd64.exe',
            'name': 'Python 3.11.9 (华为云镜像)'
        },
        'GLOBAL': {
            'url': 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe',
            'name': 'Python 3.11.9 (官方)'
        }
    }
    
    def __init__(self, install_dir):
        self.install_dir = Path(install_dir)
        self.venv_dir = self.install_dir / ".venv"
        self.python_dir = self.install_dir / "python"
        self.region = detect_region()
        self.mirror_url = "https://mirrors.aliyun.com/pypi/simple/" if self.region == 'CN' else None
        self.python_exe = self.python_dir / "python.exe"
        
    def log(self, message):
        """输出日志"""
        print(message, flush=True)
    
    def find_system_python(self):
        """查找系统 Python"""
        common_paths = [
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
            r"C:\Python39\python.exe",
            r"C:\Program Files\Python311\python.exe",
            r"C:\Program Files\Python310\python.exe",
            r"C:\Program Files\Python39\python.exe",
        ]
        
        # 检查 PATH 环境变量
        try:
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                result2 = subprocess.run(
                    ["where", "python"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result2.returncode == 0:
                    python_path = result2.stdout.strip().split('\n')[0]
                    if Path(python_path).exists():
                        return python_path
        except:
            pass
        
        # 检查常见路径
        for path in common_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def download_python(self):
        """下载 Python 安装包"""
        python_info = self.PYTHON_DOWNLOAD_URLS[self.region]
        self.log(f"[INFO] 准备下载: {python_info['name']}")
        self.log(f"[INFO] 下载地址: {python_info['url']}")
        
        # 下载到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.exe')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            self.log("[INFO] 正在下载 Python 安装包...")
            
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(downloaded * 100 / total_size, 100)
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f"\r[INFO] 下载进度: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)", end='', flush=True)
            
            urllib.request.urlretrieve(python_info['url'], temp_path, download_progress)
            print()  # 换行
            self.log("[INFO] ✓ Python 安装包下载完成")
            return temp_path
            
        except Exception as e:
            self.log(f"[ERROR] 下载失败: {str(e)}")
            if Path(temp_path).exists():
                os.unlink(temp_path)
            return None
    
    def install_python(self, installer_path):
        """静默安装 Python"""
        self.log(f"[INFO] 安装 Python 到: {self.python_dir}")
        
        # 确保安装目录存在
        self.python_dir.mkdir(parents=True, exist_ok=True)
        
        # Python 安装命令（静默安装）
        install_cmd = [
            installer_path,
            "/quiet",                    # 静默安装
            "InstallAllUsers=0",          # 当前用户
            f"TargetDir={self.python_dir}",  # 安装目录
            "PrependPath=0",              # 不添加到 PATH
            "Include_test=0",             # 不安装测试套件
            "Include_tcltk=0",            # 不安装 Tcl/Tk
        ]
        
        try:
            self.log("[INFO] 正在静默安装 Python（请稍候）...")
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                self.log("[INFO] ✓ Python 安装完成")
                return True
            else:
                self.log(f"[ERROR] Python 安装失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("[ERROR] Python 安装超时")
            return False
        except Exception as e:
            self.log(f"[ERROR] 安装失败: {str(e)}")
            return False
        
    def install_environment(self):
        """安装环境"""
        try:
            # 1. 检查或安装 Python
            self.log("[INFO] 检测地区: {}".format(self.region))
            if self.mirror_url:
                self.log(f"[INFO] pip 镜像: {self.mirror_url}")
            
            # 先检查是否已经安装了 Python
            python_path = None
            if self.python_exe.exists():
                self.log(f"[INFO] 发现本地 Python: {self.python_exe}")
                python_path = str(self.python_exe)
            else:
                # 查找系统 Python
                system_python = self.find_system_python()
                if system_python:
                    self.log(f"[INFO] 发现系统 Python: {system_python}")
                    python_path = system_python
                else:
                    # 下载并安装 Python
                    self.log("[INFO] 未找到 Python，开始下载安装...")
                    installer_path = self.download_python()
                    if not installer_path:
                        raise Exception("下载 Python 失败")
                    
                    if not self.install_python(installer_path):
                        raise Exception("安装 Python 失败")
                    
                    # 清理安装包
                    try:
                        os.unlink(installer_path)
                    except:
                        pass
                    
                    python_path = str(self.python_exe)
            
            # 验证 Python
            result = subprocess.run(
                [python_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise Exception(f"Python 执行失败: {result.stderr}")
            
            self.log(f"[INFO] Python 版本: {result.stdout.strip()}")
            
            # 2. 创建虚拟环境
            if self.venv_dir.exists():
                self.log("[INFO] 清理旧环境...")
                import shutil
                shutil.rmtree(self.venv_dir)
                self.log("[INFO] ✓ 清理完成")
            
            self.log(f"[INFO] 创建虚拟环境: {self.venv_dir}")
            
            result = subprocess.run(
                [python_path, "-m", "venv", "--copies", str(self.venv_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise Exception(f"创建虚拟环境失败: {result.stderr}")
            
            self.log("[INFO] ✓ 虚拟环境创建成功")
            
            # 3. 安装依赖
            venv_pip = self.venv_dir / "Scripts" / "pip.exe"
            
            # 检查是否存在 requirements.txt，如果有则优先使用
            req_file = Path(__file__).parent / "requirements.txt"
            if req_file.exists():
                self.log("[INFO] 使用 requirements.txt 安装依赖...")
                
                cmd = [str(venv_pip), "install", "-r", str(req_file)]
                if self.mirror_url:
                    cmd.extend(["-i", self.mirror_url, "--trusted-host", "mirrors.aliyun.com"])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10分钟超时，因为安装多个包可能较慢
                )
                
                if result.returncode != 0:
                    raise Exception(f"安装依赖失败: {result.stderr}")
                
                self.log("[INFO] ✓ 所有依赖安装成功")
            else:
                # 向后兼容：如果没有 requirements.txt，则逐个安装
                dependencies = ["requests", "beautifulsoup4", "pyside6"]
                
                for dep in dependencies:
                    self.log(f"[INFO] 安装 {dep}...")
                    
                    cmd = [str(venv_pip), "install", dep]
                    if self.mirror_url:
                        cmd.extend(["-i", self.mirror_url, "--trusted-host", "mirrors.aliyun.com"])
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode != 0:
                        raise Exception(f"安装 {dep} 失败: {result.stderr}")
                    
                    self.log(f"[INFO] ✓ {dep} 安装成功")
            
            # 4. 完成
            self.log("[INFO] ✓ 所有依赖安装完成！")
            return True
            
        except subprocess.TimeoutExpired:
            self.log("[ERROR] 操作超时，请检查网络连接后重试")
            return False
        except Exception as e:
            self.log(f"[ERROR] {str(e)}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="学业助手环境安装器")
    parser.add_argument('install_dir', nargs='?', default=None, help='安装目录')
    
    args = parser.parse_args()
    
    # 确定安装目录
    if args.install_dir:
        install_dir = args.install_dir
    else:
        install_dir = str(Path(__file__).parent)
    
    print("="*60)
    print("学业助手 - Python 环境安装器")
    print("="*60)
    print()
    
    # 命令行模式
    installer = SilentInstaller(install_dir)
    success = installer.install_environment()
    
    print()
    if success:
        print("="*60)
        print("✓ 安装完成！")
        print("="*60)
        sys.exit(0)
    else:
        print("="*60)
        print("✗ 安装失败！")
        print("="*60)
        #sys.exit(1)


if __name__ == "__main__":
    main()
