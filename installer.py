# -*- coding: utf-8 -*-
"""
学业助手 - 安装后首次运行配置
负责创建虚拟环境并安装依赖
只支持命令行模式，输出到控制台
"""

import os
import sys
import subprocess
import locale
from pathlib import Path
import argparse
import time


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
    
    def __init__(self, install_dir):
        self.install_dir = Path(install_dir)
        self.venv_dir = self.install_dir / ".venv"
        self.python_dir = self.install_dir / "python"
        self.region = detect_region()
        self.mirror_url = "https://mirrors.aliyun.com/pypi/simple/" if self.region == 'CN' else None
        self.python_exe = self.python_dir / "python.exe"
        self.req_file = Path(__file__).parent / "requirements.txt"
        
    def log(self, message):
        """输出日志"""
        print(message, flush=True)
    
    def find_bundled_python(self):
        """查找软件同目录下的 Python"""
        # 检查软件目录下的 Python
        if self.python_exe.exists():
            return str(self.python_exe)
        return None
    
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
                        # 移除版本号限制，只取包名
                        pkg = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0]
                        packages.append(pkg.strip())
                return sorted(set(packages))
            except Exception as e:
                self.log(f"[WARN] 读取 requirements.txt 失败: {e}，使用默认依赖")
        # 默认依赖
        return ["requests", "beautifulsoup4", "pyside6"]
    
    def get_installed_packages(self, pip_exe):
        """获取已安装的包名列表"""
        try:
            result = subprocess.run(
                [pip_exe, "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return set()
            
            import json
            installed_list = json.loads(result.stdout)
            installed = set(pkg['name'].lower() for pkg in installed_list)
            return installed
        except Exception:
            # 如果JSON解析失败，尝试使用freeze格式
            try:
                result = subprocess.run(
                    [pip_exe, "list", "--format=freeze"],
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
    

        
    def install_environment(self):
        """安装环境"""
        try:
            # 1. 检查 Python
            self.log("[PROGRESS] 开始安装环境 (步骤 1/3: 检测Python环境)")
            self.log("[INFO] 检测地区: {}".format(self.region))
            if self.mirror_url:
                self.log(f"[INFO] pip 镜像: {self.mirror_url}")
            
            # 检查软件目录下的 Python
            python_path = self.find_bundled_python()
            if not python_path:
                raise Exception(f"未找到 Python 3.11.9！\n预期位置: {self.python_dir}\n请确保安装包已正确安装 Python。")
            
            self.log(f"[INFO] 使用捆绑的 Python: {python_path}")
            
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
            self.log("[PROGRESS] 创建虚拟环境 (步骤 2/3)")
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
            self.log("[PROGRESS] 安装依赖包 (步骤 3/3)")
            venv_pip = self.venv_dir / "Scripts" / "pip.exe"
            
            # 获取需要安装的依赖包列表
            required_packages = self.get_required_packages()
            
            # 检查哪些包需要安装
            installed_packages = self.get_installed_packages(str(venv_pip))
            missing_packages = [pkg for pkg in required_packages if pkg.lower() not in installed_packages]
            
            if missing_packages:
                self.log(f"[INFO] 发现缺失的依赖: {missing_packages}")
                
                # 显示总体安装进度
                total_missing = len(missing_packages)
                for i, dep in enumerate(missing_packages, 1):
                    progress = (i / total_missing) * 100
                    # 创建进度条
                    bar_length = 30
                    filled_length = int(bar_length * progress // 100)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    print(f"\r[INFO] 依赖安装进度: |{bar}| {progress:.1f}% ({i}/{total_missing}) - 正在安装: {dep}", end='', flush=True)
                    
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
                        print()  # 换行以避免覆盖进度条
                        raise Exception(f"安装 {dep} 失败: {result.stderr}")
                    
                    self.log(f"\n[INFO] ✓ {dep} 安装成功")
                print()  # 最后换行
                
                self.log("[INFO] ✓ 所有缺失依赖安装完成！")
            else:
                self.log("[INFO] ✓ 所有依赖包均已存在，跳过安装")
            
            self.log("[INFO] ✓ 所有依赖安装完成！")
            
            # 4. 完成
            self.log("[SUCCESS] ✓ 环境安装完成！")
            return True
            
        except subprocess.TimeoutExpired:
            self.log("[ERROR] 操作超时，请检查网络连接后重试")
            return False
        except Exception as e:
            self.log(f"[ERROR] {str(e)}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Capture_Push环境安装器")
    parser.add_argument('install_dir', nargs='?', default=None, help='安装目录')
    
    args = parser.parse_args()
    
    # 确定安装目录
    if args.install_dir:
        install_dir = args.install_dir
    else:
        install_dir = str(Path(__file__).parent)
    
    print("="*60)
    print("Capture_Push - Python 环境安装器")
    print("="*60)
    print()
    
    # 显示安装阶段预览
    print("[INSTALLER PROGRESS VISUALIZATION]")
    print("[PHASE 1/3] 🔍 检测Python环境")
    print("[PHASE 2/3] 🛠️  创建虚拟环境")
    print("[PHASE 3/3] 📚 安装依赖包")
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
        sys.exit(1)


if __name__ == "__main__":
    main()
