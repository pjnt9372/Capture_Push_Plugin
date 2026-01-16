# -*- coding: utf-8 -*-
"""
Capture_Push - 安装后首次运行配置
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
import hashlib
import ssl
import certifi

# 强制设置 stdout 为 UTF-8 以避免在 Windows CI 环境下出现编码错误
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def detect_region():
    """检测地区，判断是否使用国内镜像"""
    try:
        lang = locale.getdefaultlocale()[0]
        if lang and 'zh_CN' in lang:
            return 'CN'
        if os.getenv('LANG', '').startswith('zh_CN'):
            return 'CN'
        return 'GLOBAL'
    except Exception:
        return 'GLOBAL'


class SilentInstaller:
    PYTHON_DOWNLOAD_URLS = {
        'CN': {
            # 华为镜像 404，改用清华源（稳定提供 Python 安装包）
            'url': 'https://mirrors.tuna.tsinghua.edu.cn/python/3.11.9/python-3.11.9-amd64.exe',
            'name': 'Python 3.11.9 (清华镜像)'
        },
        'GLOBAL': {
            'url': 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe',
            'name': 'Python 3.11.9 (官方)'
        }
    }

    DEFAULT_DEPENDENCIES = ["requests", "beautifulsoup4", "pyside6"]

    def __init__(self, install_dir):
        self.install_dir = Path(install_dir).resolve()
        self.venv_dir = self.install_dir / ".venv"
        self.python_dir = self.install_dir / "python"
        self.region = detect_region()
        self.mirror_url = "https://mirrors.aliyun.com/pypi/simple/" if self.region == 'CN' else None
        self.python_exe = self.python_dir / "python.exe"
        self.req_file = Path(__file__).parent / "requirements.txt"

    def log(self, message):
        print(message, flush=True)

    def find_system_python(self):
        common_paths = [
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
            r"C:\Python39\python.exe",
            r"C:\Program Files\Python311\python.exe",
            r"C:\Program Files\Python310\python.exe",
            r"C:\Program Files\Python39\python.exe",
        ]
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
                    paths = result2.stdout.strip().split('\n')
                    for p in paths:
                        p = p.strip()
                        if p and Path(p).exists():
                            return p
        except Exception:
            pass

        for path in common_paths:
            if Path(path).exists():
                return path
        return None

    def download_python(self):
        python_info = self.PYTHON_DOWNLOAD_URLS[self.region]
        self.log(f"[INFO] 准备下载: {python_info['name']}")
        self.log(f"[INFO] 下载地址: {python_info['url']}")

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

            # 使用 urllib.request.urlopen 并传入 SSL 上下文
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(python_info['url'])
            with urllib.request.urlopen(req, context=ssl_context) as response:
                with open(temp_path, 'wb') as out_file:
                    while True:
                        chunk = response.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        out_file.write(chunk)
                        # Simulate the progress callback
                        downloaded = out_file.tell()
                        if total_size > 0:
                            percent = min(downloaded * 100 / total_size, 100)
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            print(f"\r[INFO] 下载进度: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)", end='', flush=True)
            print()  # 换行
            self.log("[INFO] ✓ Python 安装包下载完成")
            return temp_path

        except Exception as e:
            self.log(f"[ERROR] 下载失败: {str(e)}")
            if Path(temp_path).exists():
                os.unlink(temp_path)
            return None

    def install_python(self, installer_path):
        self.log(f"[INFO] 安装 Python 到: {self.python_dir}")

        self.python_dir.mkdir(parents=True, exist_ok=True)

        install_cmd = [
            installer_path,
            "/quiet",
            "InstallAllUsers=0",
            f"TargetDir={self.python_dir}",
            "PrependPath=0",
            "Include_test=0",
            "Include_tcltk=0",
        ]

        try:
            self.log("[INFO] 正在静默安装 Python（请稍候，约需 1-3 分钟）...")
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 延长至 10 分钟
            )

            if result.returncode == 0 and self.python_exe.exists():
                self.log("[INFO] ✓ Python 安装完成")
                return True
            else:
                self.log(f"[ERROR] 安装失败或 python.exe 未生成。返回码: {result.returncode}")
                if result.stderr:
                    self.log(f"[ERROR] stderr: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.log("[ERROR] Python 安装超时（超过 10 分钟）")
            return False
        except Exception as e:
            self.log(f"[ERROR] 安装异常: {str(e)}")
            return False

    def get_required_packages(self):
        """获取需要安装的包列表"""
        if self.req_file.exists():
            try:
                with open(self.req_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                packages = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 移除版本号，只取包名（简化比较）
                        pkg = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0]
                        packages.append(pkg.lower())
                return sorted(set(packages))
            except Exception as e:
                self.log(f"[WARN] 读取 requirements.txt 失败: {e}，使用默认依赖")
        return self.DEFAULT_DEPENDENCIES

    def get_installed_packages(self, pip_exe):
        """获取已安装的包名（小写）"""
        try:
            result = subprocess.run(
                [str(pip_exe), "list", "--format=freeze"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return set()
            installed = set()
            for line in result.stdout.splitlines():
                if '==' in line:
                    pkg = line.split('==')[0].strip().lower()
                    installed.add(pkg)
            return installed
        except Exception:
            return set()

    def is_venv_satisfied(self):
        """检查 .venv 是否存在且满足依赖"""
        if not self.venv_dir.exists():
            return False

        venv_pip = self.venv_dir / "Scripts" / "pip.exe"
        venv_python = self.venv_dir / "Scripts" / "python.exe"

        if not (venv_pip.exists() and venv_python.exists()):
            return False

        required = set(self.get_required_packages())
        installed = self.get_installed_packages(venv_pip)

        missing = required - installed
        if missing:
            self.log(f"[INFO] 虚拟环境中缺少依赖: {sorted(missing)}")
            return False
        else:
            self.log("[INFO] ✓ 虚拟环境已存在且依赖完整，跳过安装")
            return True

    def install_dependencies(self, venv_pip):
        """安装依赖"""
        if self.req_file.exists():
            self.log("[INFO] 使用 requirements.txt 安装依赖...")
            cmd = [str(venv_pip), "install", "-r", str(self.req_file)]
            if self.mirror_url:
                cmd.extend(["-i", self.mirror_url, "--trusted-host", "mirrors.aliyun.com"])
        else:
            self.log("[INFO] 使用默认依赖列表安装...")
            deps = self.DEFAULT_DEPENDENCIES
            cmd = [str(venv_pip), "install"] + deps
            if self.mirror_url:
                cmd.extend(["-i", self.mirror_url, "--trusted-host", "mirrors.aliyun.com"])

        self.log("[INFO] 正在安装依赖（可能需要几分钟）...")
        try:
            # 实时输出便于观察进度
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            for line in process.stdout:
                print(line.rstrip(), flush=True)
            process.wait(timeout=1200)  # 最多 20 分钟

            if process.returncode != 0:
                raise Exception("依赖安装失败")
            self.log("[INFO] ✓ 所有依赖安装成功")
            return True
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("依赖安装超时（超过 20 分钟）")
        except Exception as e:
            raise e

    def install_environment(self):
        try:
            self.log("[INFO] 检测地区: {}".format(self.region))
            if self.mirror_url:
                self.log(f"[INFO] pip 镜像: {self.mirror_url}")

            # 检查是否已满足环境
            if self.is_venv_satisfied():
                return True

            # 1. 获取 Python 路径
            python_path = None
            if self.python_exe.exists():
                self.log(f"[INFO] 发现本地 Python: {self.python_exe}")
                python_path = str(self.python_exe)
            else:
                system_python = self.find_system_python()
                if system_python:
                    self.log(f"[INFO] 发现系统 Python: {system_python}")
                    python_path = system_python
                else:
                    self.log("[INFO] 未找到 Python，开始下载安装...")
                    installer_path = self.download_python()
                    if not installer_path:
                        raise Exception("下载 Python 失败")
                    if not self.install_python(installer_path):
                        raise Exception("安装 Python 失败")
                    try:
                        os.unlink(installer_path)
                    except Exception:
                        pass
                    python_path = str(self.python_exe)

            # 验证 Python
            result = subprocess.run(
                [python_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise Exception(f"Python 执行失败: {result.stderr}")
            self.log(f"[INFO] Python 版本: {result.stdout.strip()}")

            # 2. 创建虚拟环境（仅当不满足时）
            if not self.venv_dir.exists():
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
            else:
                self.log(f"[INFO] 使用现有虚拟环境: {self.venv_dir}")

            # 3. 安装/更新依赖
            venv_pip = self.venv_dir / "Scripts" / "pip.exe"
            self.install_dependencies(venv_pip)

            self.log("[INFO] ✓ 环境配置完成！")
            return True

        except subprocess.TimeoutExpired:
            self.log("[ERROR] 操作超时，请检查网络连接后重试")
            return False
        except Exception as e:
            self.log(f"[ERROR] {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Capture_Push 环境安装器")
    parser.add_argument('install_dir', nargs='?', default=None, help='安装目录')

    args = parser.parse_args()

    if args.install_dir:
        install_dir = args.install_dir
    else:
        install_dir = str(Path(__file__).parent)

    print("=" * 60)
    print("Capture_Push - Python 环境安装器")
    print("=" * 60)
    print()

    installer = SilentInstaller(install_dir)
    success = installer.install_environment()

    print()
    if success:
        print("=" * 60)
        print("✓ 安装完成！")
        print("激活虚拟环境命令（Windows）:")
        print(f"    {installer.venv_dir / 'Scripts' / 'activate'}")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("✗ 安装失败！")
        print("请检查网络、权限，并重试。")
        print("=" * 60)
        input("按 Enter 键退出...")  # 等待用户按键
        sys.exit(1)


if __name__ == "__main__":
    main()