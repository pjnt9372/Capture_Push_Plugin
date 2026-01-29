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
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from core.log import get_logger

PROXY_URL_PREFIX = "https://ghfast.top/"

logger = get_logger()


class Updater:
    """软件更新管理器"""
    
    GITHUB_REPO = "pjnt9372/Capture_Push"  # 替换为实际仓库
    API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    ALL_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    
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
    
    def check_update(self, include_prerelease=False) -> Optional[Tuple[str, dict]]:
        """
        检查是否有新版本
        
        Args:
            include_prerelease: 是否包括预发布版本
        
        Returns:
            (版本号, 资产信息) 如果有更新
            None 如果没有更新或检查失败
        """
        try:
            logger.info(f"正在检查更新... (包含预发布版本: {include_prerelease})")
            
            if include_prerelease:
                # 检查所有发布版本，包括预发布
                req = urllib.request.Request(
                    self.ALL_RELEASES_API_URL,
                    headers={'User-Agent': 'Capture_Push-Updater'}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    releases = json.loads(response.read().decode('utf-8'))
                
                # 查找最新的版本（包括预发布）
                latest_release = None
                latest_version = "0.0.0"
                
                for release in releases:
                    # 如果不包含预发布版本，则跳过预发布
                    if not include_prerelease and release.get('prerelease', False):
                        continue
                    
                    release_version = release['tag_name'].lstrip('v').replace('-', '.').replace('_', '.')
                    
                    # 比较版本号
                    if self._compare_version(release_version, latest_version) > 0:
                        latest_version = release_version
                        latest_release = release
                
                if latest_release and self._compare_version(latest_version, self.current_version) > 0:
                    logger.info(f"发现新版本: {latest_version} (预发布: {latest_release.get('prerelease', False)})")
                    return latest_version, latest_release
                else:
                    logger.info("当前已是最新版本")
                    return None
            else:
                # 只检查最新的稳定版本
                req = urllib.request.Request(
                    self.API_URL,
                    headers={'User-Agent': 'Capture_Push-Updater'}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data['tag_name'].lstrip('v').replace('-', '.').replace('_', '.')
                
                logger.info(f"当前版本: {self.current_version}, 最新稳定版本: {latest_version}")
                
                if self._compare_version(latest_version, self.current_version) > 0:
                    logger.info(f"发现新版本: {latest_version}")
                    return latest_version, data
                else:
                    logger.info("当前已是最新版本")
                    return None
                    
        except urllib.error.URLError as e:
            logger.warning(f"直接访问GitHub API失败: {e}")
            
            # 尝试使用代理访问API
            try:
                if include_prerelease:
                    logger.info(f"尝试使用代理访问API: {PROXY_URL_PREFIX}{self.ALL_RELEASES_API_URL}")
                    proxy_api_url = PROXY_URL_PREFIX + self.ALL_RELEASES_API_URL
                    req_proxy = urllib.request.Request(
                        proxy_api_url,
                        headers={'User-Agent': 'Capture_Push-Updater'}
                    )
                    
                    with urllib.request.urlopen(req_proxy, timeout=20) as response:
                        releases = json.loads(response.read().decode('utf-8'))
                    
                    # 查找最新的版本（包括预发布）
                    latest_release = None
                    latest_version = "0.0.0"
                    
                    for release in releases:
                        # 如果不包含预发布版本，则跳过预发布
                        if not include_prerelease and release.get('prerelease', False):
                            continue
                        
                        release_version = release['tag_name'].lstrip('v').replace('-', '.').replace('_', '.')
                        
                        # 比较版本号
                        if self._compare_version(release_version, latest_version) > 0:
                            latest_version = release_version
                            latest_release = release
                    
                    if latest_release and self._compare_version(latest_version, self.current_version) > 0:
                        logger.info(f"通过代理发现新版本: {latest_version} (预发布: {latest_release.get('prerelease', False)})")
                        return latest_version, latest_release
                    else:
                        logger.info("当前已是最新版本")
                        return None
                else:
                    logger.info(f"尝试使用代理访问API: {PROXY_URL_PREFIX}{self.API_URL}")
                    proxy_api_url = PROXY_URL_PREFIX + self.API_URL
                    req_proxy = urllib.request.Request(
                        proxy_api_url,
                        headers={'User-Agent': 'Capture_Push-Updater'}
                    )
                    
                    with urllib.request.urlopen(req_proxy, timeout=20) as response:
                        data = json.loads(response.read().decode('utf-8'))
                    
                    latest_version = data['tag_name'].lstrip('v').replace('-', '.').replace('_', '.')
                    
                    logger.info(f"通过代理获取到版本: {self.current_version}, 最新版本: {latest_version}")
                    
                    if self._compare_version(latest_version, self.current_version) > 0:
                        logger.info(f"发现新版本: {latest_version}")
                        return latest_version, data
                    else:
                        logger.info("当前已是最新版本")
                        return None
                    
            except urllib.error.URLError as proxy_error:
                logger.error(f"通过代理访问GitHub API也失败: {proxy_error}")
                return None
            except Exception as proxy_error:
                logger.error(f"通过代理检查更新失败: {proxy_error}")
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
            # 格式: x.x.x, x.x.x_Beta, x.x.x_Dev (严格按照 GitHub Actions 规则)
            import re
            
            # 使用正则表达式分离版本号和后缀，严格按照 GitHub Actions 规则
            # 稳定版: ^\d+\.\d+\.\d+$
            # Beta版: ^\d+\.\d+\.\d+_Beta$
            # Dev版: ^\d+\.\d+\.\d+_Dev$
            v1_match = re.match(r'^([0-9]+\.[0-9]+\.[0-9]+)(_(Beta|Dev))?$', v1)
            v2_match = re.match(r'^([0-9]+\.[0-9]+\.[0-9]+)(_(Beta|Dev))?$', v2)
            
            v1_base = v1_match.group(1) if v1_match else v1
            v1_suffix = v1_match.group(2)[1:] if v1_match and v1_match.group(2) else ''  # 去掉下划线前缀
            
            v2_base = v2_match.group(1) if v2_match else v2
            v2_suffix = v2_match.group(2)[1:] if v2_match and v2_match.group(2) else ''  # 去掉下划线前缀
            
            # 2. 比较基础版本 (x.x.x)
            parts1 = [int(x) for x in v1_base.split('.') if x.isdigit()]
            parts2 = [int(x) for x in v2_base.split('.') if x.isdigit()]
            
            # 比较每个版本段
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            # 如果一个版本有更多的段且数值更大，则认为它更新
            if len(parts1) > len(parts2):
                return 1
            elif len(parts1) < len(parts2):
                return -1
            
            # 3. 基础版本相同，比较后缀
            # 规则: 
            # - 无后缀 (正式版) > 有后缀 (Beta/Dev等)
            # - 有后缀时，按字母顺序比较
            
            # 情况 A: 远程是正式版，本地有后缀 -> 升级
            if not v1_suffix and v2_suffix:
                return 1
            
            # 情况 B: 远程有后缀，本地是正式版 -> 不升级 (回退)
            if v1_suffix and not v2_suffix:
                return -1
            
            # 情况 C: 两者都有后缀 -> 比较后缀字符串
            if v1_suffix and v2_suffix:
                if v1_suffix.lower() > v2_suffix.lower():
                    return 1
                elif v1_suffix.lower() < v2_suffix.lower():
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
            
            # 尝试从资产中获取校验和信息
            asset_checksum = None
            if 'body' in release_data:
                # 尝试从发布说明中提取校验和
                body_text = release_data['body']
                if 'sha256:' in body_text.lower():
                    import re
                    # 查找SHA256校验和（64个十六进制字符）
                    checksum_matches = re.findall(r'[a-fA-F0-9]{64}', body_text)
                    if checksum_matches:
                        # 根据文件名尝试匹配正确的校验和
                        for match in checksum_matches:
                            if target_name.lower() in body_text.lower() or len(checksum_matches) == 1:
                                asset_checksum = match
                                break
            
            # 下载到临时目录
            temp_dir = Path(tempfile.gettempdir()) / "Capture_Push_Update"
            temp_dir.mkdir(parents=True, exist_ok=True)
            download_path = temp_dir / target_name
            
            # 带进度的下载
            def _progress_hook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    progress = min(100, (block_num * block_size / total_size) * 100)
                    progress_callback(progress)
            
            # 尝试直接下载
            req = urllib.request.Request(
                download_url,
                headers={'User-Agent': 'Capture_Push-Updater'}
            )
            
            try:
                urllib.request.urlretrieve(download_url, download_path, _progress_hook)
            except Exception as direct_error:
                logger.warning(f"直接下载失败: {direct_error}")
                
                # 使用代理地址尝试下载
                proxy_url = PROXY_URL_PREFIX + download_url
                logger.info(f"尝试使用代理下载: {proxy_url}")
                
                try:
                    req_proxy = urllib.request.Request(
                        proxy_url,
                        headers={'User-Agent': 'Capture_Push-Updater'}
                    )
                    urllib.request.urlretrieve(proxy_url, download_path, _progress_hook)
                    logger.info("代理下载成功")
                except Exception as proxy_error:
                    logger.error(f"代理下载也失败: {proxy_error}")
                    raise proxy_error  # 抛出异常以便外层捕获
            
            # 验证下载文件的完整性
            calculated_checksum = self._calculate_file_hash(str(download_path))
            
            if asset_checksum:
                if calculated_checksum.lower() == asset_checksum.lower():
                    logger.info("文件完整性验证成功 - 校验和匹配")
                else:
                    logger.error(f"文件完整性验证失败! 期望校验和: {asset_checksum}, 实际校验和: {calculated_checksum}")
                    os.remove(download_path)  # 删除可能被篡改的文件
                    return None
            else:
                # 如果没有提供校验和，至少检查文件大小
                downloaded_size = os.path.getsize(download_path)
                if downloaded_size != file_size:
                    logger.error(f"文件大小不匹配! 期望: {file_size}, 实际: {downloaded_size}")
                    os.remove(download_path)  # 删除损坏的文件
                    return None
                else:
                    logger.info(f"文件大小验证通过，校验和信息未提供，无法进行完整性校验")
            
            # 将安装包保存到程序目录，以便后续修复使用
            saved_path = self.save_installer_locally(str(download_path))
            
            logger.info(f"下载完成: {saved_path}")
            return saved_path
            
        except Exception as e:
            logger.error(f"下载更新失败: {e}")
            return None
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """
        计算文件的SHA256哈希值
        
        Args:
            filepath: 文件路径
        
        Returns:
            文件的SHA256哈希值
        """
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            # 分块读取文件，避免大文件占用过多内存
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
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
            
            # 如果是轻量级安装包，或者显式指定静默安装，则使用静默模式
            if silent or 'Lite_Setup' in os.path.basename(installer_path):
                cmd.append('/VERYSILENT')
                cmd.append('/NORESTART')
            
            # 启动安装程序（不等待）
            subprocess.Popen(cmd, shell=True)
            
            logger.info("安装程序已启动，即将退出当前程序")
            
            # 安装完成后自启动托盘程序
            import threading
            import time
            import winreg
            
            def delayed_start_tray():
                # 等待安装完成
                time.sleep(5)
                
                # 尝试从注册表获取安装路径
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                        r"SOFTWARE\\Capture_Push", 
                                        0, 
                                        winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                    install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                    winreg.CloseKey(key)
                    
                    tray_exe = Path(install_path) / "Capture_Push_tray.exe"
                    if tray_exe.exists():
                        # 启动托盘程序
                        subprocess.Popen([str(tray_exe)], shell=True)
                        logger.info("托盘程序已启动")
                    else:
                        logger.warning(f"托盘程序不存在: {tray_exe}")
                except Exception as e:
                    logger.error(f"启动托盘程序失败: {e}")
            
            # 在后台线程中启动托盘程序
            thread = threading.Thread(target=delayed_start_tray, daemon=True)
            thread.start()
            
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
    
    def verify_existing_installer(self, installer_path: str, expected_checksum: str = None) -> bool:
        """
        验证已存在的安装包的完整性
        
        Args:
            installer_path: 安装包路径
            expected_checksum: 期望的校验和（可选）
        
        Returns:
            True 如果校验通过
        """
        if not os.path.exists(installer_path):
            logger.error(f"安装包不存在: {installer_path}")
            return False
        
        # 计算文件的SHA256校验和
        calculated_checksum = self._calculate_file_hash(installer_path)
        logger.info(f"正在验证安装包: {os.path.basename(installer_path)}")
        logger.info(f"计算得到的校验和: {calculated_checksum}")
        
        if expected_checksum:
            if calculated_checksum.lower() == expected_checksum.lower():
                logger.info("安装包完整性验证成功 - 校验和匹配")
                return True
            else:
                logger.error(f"安装包完整性验证失败! 期望: {expected_checksum}, 实际: {calculated_checksum}")
                return False
        else:
            # 如果没有提供期望校验和，至少输出计算结果供参考
            logger.warning(f"未提供期望校验和，计算得到: {calculated_checksum}")
            return True  # 在这种情况下，我们认为只要文件存在就算通过
    
    def save_installer_locally(self, installer_path: str) -> str:
        """
        将安装包保存到程序目录下
        
        Args:
            installer_path: 当前安装包路径
        
        Returns:
            保存后的安装包路径
        """
        try:
            # 获取安装目录
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"SOFTWARE\Capture_Push", 
                                0, 
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            
            # 确定目标路径
            target_dir = Path(install_path)
            target_path = target_dir / os.path.basename(installer_path)
            
            # 复制文件到程序目录
            import shutil
            shutil.copy2(installer_path, target_path)
            
            logger.info(f"安装包已保存到程序目录: {target_path}")
            return str(target_path)
            
        except Exception as e:
            logger.error(f"保存安装包到程序目录失败: {e}")
            # 如果无法获取安装目录，保存到当前目录
            try:
                local_path = Path.cwd() / os.path.basename(installer_path)
                import shutil
                shutil.copy2(installer_path, local_path)
                logger.info(f"安装包已保存到当前目录: {local_path}")
                return str(local_path)
            except Exception as e2:
                logger.error(f"保存安装包失败: {e2}")
                return installer_path  # 返回原始路径
    
    def repair_installation(self, installer_path: str = None, expected_checksum: str = None, use_lite: bool = True) -> bool:
        """
        修复安装功能 - 重新校验哈希并安装安装包
        
        Args:
            installer_path: 安装包路径，如果为None则尝试从程序目录获取
            expected_checksum: 期望的校验和
            use_lite: 是否使用轻量级安装包
        
        Returns:
            是否修复成功
        """
        logger.info("开始执行修复安装...")
        
        # 如果没有提供安装包路径，尝试获取本地保存的安装包
        if not installer_path:
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                    r"SOFTWARE\Capture_Push", 
                                    0, 
                                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                
                # 尝试查找本地保存的安装包
                install_dir = Path(install_path)
                installer_candidates = []
                if use_lite:
                    installer_candidates = [install_dir / "Capture_Push_Lite_Setup.exe"]
                else:
                    installer_candidates = [install_dir / "Capture_Push_Setup.exe"]
                
                for candidate in installer_candidates:
                    if candidate.exists():
                        installer_path = str(candidate)
                        logger.info(f"找到本地安装包: {installer_path}")
                        break
                
                # 如果本地没有找到安装包，则下载新包
                if not installer_path:
                    logger.warning("未找到本地保存的安装包，正在下载...")
                    
                    # 检查是否有新版本可用
                    update_info = self.check_update()
                    if update_info:
                        version, release_data = update_info
                        logger.info(f"发现可用版本: {version}，正在下载安装包...")
                    else:
                        # 如果没有新版本，仍然尝试下载当前版本的安装包
                        logger.info("正在获取最新版本信息以下载安装包...")
                        # 直接使用API获取最新版本信息
                        try:
                            req = urllib.request.Request(
                                self.API_URL,
                                headers={'User-Agent': 'Capture_Push-Updater'}
                            )
                            with urllib.request.urlopen(req, timeout=10) as response:
                                release_data = json.loads(response.read().decode('utf-8'))
                        except Exception as api_error:
                            logger.error(f"获取版本信息失败: {api_error}")
                            # 尝试使用代理
                            try:
                                proxy_api_url = PROXY_URL_PREFIX + self.API_URL
                                req_proxy = urllib.request.Request(
                                    proxy_api_url,
                                    headers={'User-Agent': 'Capture_Push-Updater'}
                                )
                                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                                    release_data = json.loads(response.read().decode('utf-8'))
                            except Exception as proxy_error:
                                logger.error(f"通过代理获取版本信息也失败: {proxy_error}")
                                return False
                    
                    # 下载安装包
                    installer_path = self.download_update(release_data, use_lite=use_lite)
                    
                    if not installer_path:
                        logger.error("下载安装包失败")
                        return False
                    
                    logger.info(f"安装包下载完成: {installer_path}")
                    
            except Exception as e:
                logger.error(f"获取安装目录失败: {e}")
                logger.info("正在尝试下载安装包...")
                
                # 尝试获取最新版本并下载
                try:
                    req = urllib.request.Request(
                        self.API_URL,
                        headers={'User-Agent': 'Capture_Push-Updater'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        release_data = json.loads(response.read().decode('utf-8'))
                    
                    installer_path = self.download_update(release_data, use_lite=use_lite)
                    
                    if not installer_path:
                        logger.error("下载安装包失败")
                        return False
                    
                except Exception as download_error:
                    logger.error(f"下载安装包失败: {download_error}")
                    return False
        
        # 验证安装包完整性
        if not self.verify_existing_installer(installer_path, expected_checksum):
            logger.error("安装包完整性验证失败，无法继续修复")
            return False
        
        # 保存安装包到程序目录（如果还没保存的话）
        saved_path = self.save_installer_locally(installer_path)
        
        # 执行安装
        logger.info("开始安装修复...")
        return self.install_update(saved_path, silent=True)


def check_for_updates_cli():

    """命令行检查更新"""
    updater = Updater()
    
    # 询问用户是否检查预发布版本
    choice = input("是否检查预发布版本? (y/n): ").strip().lower()
    include_prerelease = choice == 'y'
    
    result = updater.check_update(include_prerelease=include_prerelease)
    
    if result:
        version, data = result
        is_prerelease = data.get('prerelease', False)
        print(f"发现新版本: {version}{' (预发布)' if is_prerelease else ''}")
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
                    # 对于轻量级更新包，使用静默安装
                    installer_filename = os.path.basename(installer)
                    is_lite_installer = 'Lite_Setup' in installer_filename
                    if updater.install_update(installer, silent=is_lite_installer):
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
