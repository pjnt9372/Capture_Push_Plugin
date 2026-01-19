# -*- coding: utf-8 -*-
"""
自动更新模块
通过 GitHub Releases API 检查更新并下载安装包
"""

import os
import sys
import urllib.request
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from core.log import get_logger

logger = get_logger()


class Updater:
    """软件更新管理器"""
    
    GITHUB_REPO = "pjnt9372/Capture_Push"  # 替换为实际仓库
    API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    def __init__(self):
        self.current_version = self._get_current_version()
    
    def _get_current_version(self) -> str:
        """获取当前版本号"""
        try:
            version_file = Path(__file__).parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text(encoding='utf-8').strip()
            else:
                logger.warning("VERSION 文件不存在")
                return "0.0.0"
        except Exception as e:
            logger.error(f"读取版本号失败: {e}")
            return "0.0.0"
    
    def check_update(self) -> Optional[Tuple[str, dict]]:
        """
        检查是否有新版本
        
        Returns:
            (版本号, 资产信息) 如果有更新
            None 如果没有更新或检查失败
        """
        try:
            logger.info("正在检查更新...")
            req = urllib.request.Request(
                self.API_URL,
                headers={'User-Agent': 'Capture_Push-Updater'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data['tag_name'].lstrip('v').replace('-', '.').replace('_', '.')
            
            logger.info(f"当前版本: {self.current_version}, 最新版本: {latest_version}")
            
            if self._compare_version(latest_version, self.current_version) > 0:
                logger.info(f"发现新版本: {latest_version}")
                return latest_version, data
            else:
                logger.info("当前已是最新版本")
                return None
                
        except urllib.error.URLError as e:
            logger.error(f"网络请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            return None
    
    def _compare_version(self, v1: str, v2: str) -> int:
        """
        比较版本号
        
        v1: 远程版本 (最新)
        v2: 本地版本 (当前)
        
        Returns:
            1 if v1 > v2 (有更新)
            0 if v1 == v2 (无更新)
            -1 if v1 < v2 (当前版本更高)
        """
        try:
            # 1. 处理后缀 (Beta, Dev 等)
            # 格式: x.x.x_xxxx
            v1_parts = v1.split('_')
            v2_parts = v2.split('_')
            
            v1_base = v1_parts[0].replace('_', '.')
            v2_base = v2_parts[0].replace('_', '.')
            
            # 2. 比较基础版本 (x.x.x)
            parts1 = [int(x) for x in v1_base.split('.')]
            parts2 = [int(x) for x in v2_base.split('.')]
            
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            if len(parts1) > len(parts2):
                return 1
            elif len(parts1) < len(parts2):
                return -1
            
            # 3. 基础版本相同，比较后缀
            # 规则: 
            # - 无后缀 (正式版) > 有后缀 (Beta/Dev)
            # - 有后缀时，按字母顺序比较 (Beta > Dev)
            
            # 情况 A: 远程是正式版，本地是预发布版 -> 升级
            if len(v1_parts) == 1 and len(v2_parts) > 1:
                return 1
            
            # 情况 B: 远程是预发布版，本地是正式版 -> 不升级 (回退)
            if len(v1_parts) > 1 and len(v2_parts) == 1:
                return -1
            
            # 情况 C: 两者都是预发布版 -> 比较后缀字符串
            if len(v1_parts) > 1 and len(v2_parts) > 1:
                if v1_parts[1] > v2_parts[1]:
                    return 1
                elif v1_parts[1] < v2_parts[1]:
                    return -1
            
            return 0
        except Exception as e:
            logger.error(f"版本号比较失败: {e}")
            return 0
    
    def download_update(self, release_data: dict, use_lite: bool = True, 
                       progress_callback=None) -> Optional[str]:
        """
        下载更新包
        
        Args:
            release_data: GitHub Release 数据
            use_lite: 是否优先下载轻量级包
            progress_callback: 下载进度回调函数
        
        Returns:
            下载文件路径，失败返回 None
        """
        try:
            # 选择下载目标
            assets = release_data.get('assets', [])
            target_name = "Capture_Push_Lite_Setup.exe" if use_lite else "Capture_Push_Setup.exe"
            
            target_asset = None
            for asset in assets:
                if asset['name'] == target_name:
                    target_asset = asset
                    break
            
            # 如果找不到轻量级包，尝试下载完整版
            if not target_asset and use_lite:
                logger.warning("未找到轻量级更新包，尝试下载完整版")
                target_name = "Capture_Push_Setup.exe"
                for asset in assets:
                    if asset['name'] == target_name:
                        target_asset = asset
                        break
            
            if not target_asset:
                logger.error("未找到可下载的安装包")
                return None
            
            download_url = target_asset['browser_download_url']
            file_size = target_asset['size']
            
            logger.info(f"正在下载: {target_name} ({file_size / 1024 / 1024:.2f} MB)")
            
            # 下载到临时目录
            temp_dir = Path(tempfile.gettempdir()) / "Capture_Push_Update"
            temp_dir.mkdir(parents=True, exist_ok=True)
            download_path = temp_dir / target_name
            
            # 带进度的下载
            def _progress_hook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    progress = min(100, (block_num * block_size / total_size) * 100)
                    progress_callback(progress)
            
            req = urllib.request.Request(
                download_url,
                headers={'User-Agent': 'Capture_Push-Updater'}
            )
            
            urllib.request.urlretrieve(download_url, download_path, _progress_hook)
            
            logger.info(f"下载完成: {download_path}")
            return str(download_path)
            
        except Exception as e:
            logger.error(f"下载更新失败: {e}")
            return None
    
    def install_update(self, installer_path: str, silent: bool = False) -> bool:
        """
        安装更新
        
        Args:
            installer_path: 安装包路径
            silent: 是否静默安装
        
        Returns:
            是否成功启动安装程序
        """
        try:
            if not os.path.exists(installer_path):
                logger.error(f"安装包不存在: {installer_path}")
                return False
            
            logger.info(f"正在启动安装程序: {installer_path}")
            
            # 构建安装命令
            cmd = [installer_path]
            if silent:
                cmd.append('/VERYSILENT')
                cmd.append('/NORESTART')
            
            # 启动安装程序（不等待）
            subprocess.Popen(cmd, shell=True)
            
            logger.info("安装程序已启动，即将退出当前程序")
            return True
            
        except Exception as e:
            logger.error(f"启动安装程序失败: {e}")
            return False
    
    def check_python_env(self) -> bool:
        """
        检查是否存在 Python 环境
        用于判断是否可以使用轻量级更新包
        
        Returns:
            True 如果存在 Python 环境
        """
        try:
            # 检查安装目录
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"SOFTWARE\Capture_Push", 
                                0, 
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            
            python_exe = Path(install_path) / ".venv" / "python.exe"
            return python_exe.exists()
            
        except Exception:
            # 如果读取注册表失败，假设不存在
            return False


def check_for_updates_cli():
    """命令行检查更新"""
    updater = Updater()
    result = updater.check_update()
    
    if result:
        version, data = result
        print(f"发现新版本: {version}")
        print(f"发布时间: {data.get('published_at', 'N/A')}")
        print(f"更新说明:\n{data.get('body', '无')}")
        
        # 询问是否下载
        choice = input("\n是否下载更新? (y/n): ").strip().lower()
        if choice == 'y':
            has_python = updater.check_python_env()
            use_lite = has_python
            
            print(f"\n将下载: {'轻量级' if use_lite else '完整版'}更新包")
            
            def progress(p):
                print(f"\r下载进度: {p:.1f}%", end='', flush=True)
            
            installer = updater.download_update(data, use_lite, progress)
            print()  # 换行
            
            if installer:
                print(f"\n下载完成: {installer}")
                choice = input("是否立即安装? (y/n): ").strip().lower()
                if choice == 'y':
                    if updater.install_update(installer):
                        print("正在启动安装程序...")
                        sys.exit(0)
                else:
                    print(f"安装包已保存，您可以稍后手动运行: {installer}")
            else:
                print("下载失败")
    else:
        print("当前已是最新版本")


if __name__ == "__main__":
    check_for_updates_cli()
