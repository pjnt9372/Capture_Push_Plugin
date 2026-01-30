# -*- coding: utf-8 -*-
"""
院校模块插件管理器
通过 GitHub API 管理院校模块插件的下载、验证、安装和加载
"""

import os
import sys
import urllib.request
import json
import tempfile
import hashlib
import zipfile
from pathlib import Path
import importlib.util
from typing import Optional, Dict, Any
from core.log import get_logger

PROXY_URL_PREFIX = "https://ghfast.top/"

logger = get_logger()


class SchoolPluginManager:
    """院校模块插件管理器"""
    
    GITHUB_REPO_DEFAULT = "pjnt9372/Capture_Push_School_Plugins"  # 默认院校插件仓库
    API_URL_DEFAULT = f"https://api.github.com/repos/{GITHUB_REPO_DEFAULT}/releases/tags/plugin%2Flatest"  # 固定标签的插件API URL
    PLUGINS_INDEX_URL_DEFAULT = f"https://raw.githubusercontent.com/{GITHUB_REPO_DEFAULT}/main/plugins_index.json"  # 插件索引文件URL (备用)
    
    def __init__(self):
        self.plugins_dir = Path(__file__).parent.parent / "plugins" / "school"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前版本文件
        self.version_file = self.plugins_dir / "current" / "version.txt"
        
        # 插件索引缓存
        self.plugins_index_cache = None
        
        # 从配置文件加载插件设置
        from core.config_manager import load_config
        config = load_config()
        
        # 获取插件仓库URL，如果没有配置则使用默认值
        if config.has_section('plugins'):
            self.repository_url = config.get('plugins', {}).get('repository_url', 
                'https://api.github.com/repos/pjnt9372/Capture_Push_School_Plugins/releases/tags/plugin%2Flatest')
        else:
            self.repository_url = 'https://api.github.com/repos/pjnt9372/Capture_Push_School_Plugins/releases/tags/plugin%2Flatest'
        
    def _get_local_plugin_version(self, school_code: str) -> str:
        """
        获取本地插件版本
        
        Args:
            school_code: 院校代码
            
        Returns:
            本地插件版本号，如果不存在则返回 '0.0.0'
        """
        try:
            version_file = self.plugins_dir / school_code / "version.txt"
            if version_file.exists():
                return version_file.read_text(encoding='utf-8').strip()
            else:
                # 尝试从插件模块中获取版本信息
                plugin_dir = self.plugins_dir / school_code
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    with open(init_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 查找 VERSION 常量
                        for line in content.split('\n'):
                            if line.strip().startswith('PLUGIN_VERSION') or line.strip().startswith('VERSION'):
                                parts = line.split('=')
                                if len(parts) > 1:
                                    version = parts[1].strip().strip('"\'')
                                    return version
        except Exception as e:
            logger.error(f"读取本地插件版本失败: {e}")
        return "0.0.0"
    
    def check_plugin_update(self, school_code: str) -> Optional[Dict[str, Any]]:
        """
        检查指定院校插件是否有更新
            
        Args:
            school_code: 院校代码
            
        Returns:
            插件更新信息字典，如果没有更新则返回 None
        """
        try:
            logger.info(f"正在检查插件更新: {school_code}")
                
            # 首先尝试从插件索引获取信息（备用方式）
            plugin_info = self.get_plugin_info_from_index(school_code)
                
            if plugin_info:
                logger.info(f"从插件索引获取到 {school_code} 的插件信息")
                    
                # 检查版本
                remote_version = plugin_info.get('plugin_version', '0.0.0')
                local_version = self._get_local_plugin_version(school_code)
                    
                logger.info(f"院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                    
                if self._compare_version(remote_version, local_version) > 0:
                    # 添加远程信息
                    plugin_info['remote_version'] = remote_version
                    plugin_info['local_version'] = local_version
                    return plugin_info
                else:
                    logger.info(f"院校 {school_code} 插件已是最新版本")
                    return None
            else:
                logger.info(f"插件索引中未找到 {school_code} 的插件信息，尝试从固定标签 plugin/latest 获取")
                    
            # 从固定的 plugin/latest 标签获取插件信息
            req = urllib.request.Request(
                self.repository_url,
                headers={'User-Agent': 'Capture_Push-SchoolPluginManager'}
            )
                        
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                            
            # 解析发布说明中的插件信息
            body = data.get('body', '')
            plugin_info = self._parse_plugin_info(body, school_code)
                        
            # 如果解析到了插件信息，添加作者信息
            if plugin_info:
                # 优先使用JSON中提供的贡献者信息
                if 'contributor' not in plugin_info:
                    # 从发布数据中获取作者信息
                    author = data.get('author', {}).get('login', 'Unknown')
                    plugin_info['contributor'] = author
                        
            # 如果没从发布说明中找到插件信息，尝试从资产中推断
            if not plugin_info:
                plugin_info = self._infer_plugin_info_from_assets(data.get('assets', []), school_code, data)
                # 如果是从资产中推断的，也需要添加贡献者信息
                if plugin_info and 'contributor' not in plugin_info:
                    author = data.get('author', {}).get('login', 'Unknown')
                    plugin_info['contributor'] = author
                        
            if not plugin_info:
                logger.warning(f"在发布说明中未找到插件信息: {school_code}")
                return None
                    
            # 检查版本
            remote_version = plugin_info.get('plugin_version', '0.0.0')
            local_version = self._get_local_plugin_version(school_code)
                
            logger.info(f"院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                
            if self._compare_version(remote_version, local_version) > 0:
                # 添加下载URL信息
                plugin_info['download_url'] = self._get_download_url(data, school_code)
                plugin_info['remote_version'] = remote_version
                plugin_info['local_version'] = local_version
                return plugin_info
            else:
                logger.info(f"院校 {school_code} 插件已是最新版本")
                return None
                    
        except urllib.error.URLError as e:
            logger.warning(f"直接访问GitHub API失败: {e}")
                
            # 尝试使用代理访问API
            try:
                logger.info(f"尝试使用代理访问API: {PROXY_URL_PREFIX}{self.repository_url}")
                proxy_api_url = PROXY_URL_PREFIX + self.repository_url
                req_proxy = urllib.request.Request(
                    proxy_api_url,
                    headers={'User-Agent': 'Capture_Push-SchoolPluginManager'}
                )
                    
                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                    data = json.loads(response.read().decode('utf-8'))
                        
                # 尝试从插件索引获取（备用方式）
                plugin_info = self.get_plugin_info_from_index(school_code)
                    
                if plugin_info:
                    logger.info(f"从插件索引获取到 {school_code} 的插件信息")
                        
                    # 检查版本
                    remote_version = plugin_info.get('plugin_version', '0.0.0')
                    local_version = self._get_local_plugin_version(school_code)
                        
                    logger.info(f"通过代理检查院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                        
                    if self._compare_version(remote_version, local_version) > 0:
                        # 添加远程信息
                        plugin_info['remote_version'] = remote_version
                        plugin_info['local_version'] = local_version
                        return plugin_info
                    else:
                        logger.info(f"院校 {school_code} 插件已是最新版本")
                        return None
                    
                # 从固定的 plugin/latest 标签获取插件信息
                # 解析发布说明中的插件信息
                body = data.get('body', '')
                plugin_info = self._parse_plugin_info(body, school_code)
                                
                # 如果解析到了插件信息，添加作者信息
                if plugin_info:
                    # 优先使用JSON中提供的贡献者信息
                    if 'contributor' not in plugin_info:
                        # 从发布数据中获取作者信息
                        author = data.get('author', {}).get('login', 'Unknown')
                        plugin_info['contributor'] = author
                                
                # 如果没从发布说明中找到插件信息，尝试从资产中推断
                if not plugin_info:
                    plugin_info = self._infer_plugin_info_from_assets(data.get('assets', []), school_code, data)
                    # 如果是从资产中推断的，也需要添加贡献者信息
                    if plugin_info and 'contributor' not in plugin_info:
                        author = data.get('author', {}).get('login', 'Unknown')
                        plugin_info['contributor'] = author
                                
                if not plugin_info:
                    logger.warning(f"在发布说明中未找到插件信息: {school_code}")
                    return None
                        
                # 检查版本
                remote_version = plugin_info.get('plugin_version', '0.0.0')
                local_version = self._get_local_plugin_version(school_code)
                    
                logger.info(f"通过代理检查院校 {school_code}: 本地版本 {local_version}, 远程版本 {remote_version}")
                    
                if self._compare_version(remote_version, local_version) > 0:
                    # 添加下载URL信息
                    plugin_info['download_url'] = self._get_download_url(data, school_code)
                    plugin_info['remote_version'] = remote_version
                    plugin_info['local_version'] = local_version
                    return plugin_info
                else:
                    logger.info(f"院校 {school_code} 插件已是最新版本")
                    return None
                        
            except Exception as proxy_error:
                logger.error(f"通过代理检查插件更新失败: {proxy_error}")
                return None
        except Exception as e:
            logger.error(f"检查插件更新失败: {e}")
            return None
    
    def _parse_plugin_info(self, body: str, school_code: str) -> Optional[Dict[str, Any]]:
        """
        从发布说明中解析插件信息
            
        Args:
            body: 发布说明文本
            school_code: 院校代码
            
        Returns:
            插件信息字典，如果未找到则返回 None
        """
        try:
            # 尝试解析JSON格式的插件信息
            lines = body.split('\n')
            for i, line in enumerate(lines):
                if f'"school_code": "{school_code}"' in line or f"'school_code': '{school_code}'" in line:
                    # 向前查找JSON开始
                    start_idx = i
                    while start_idx >= 0:
                        if '{' in lines[start_idx]:
                            break
                        start_idx -= 1
                    # 向后查找JSON结束
                    end_idx = i
                    brace_count = 0
                    for j in range(start_idx, len(lines)):
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count <= 0 and '}' in lines[j]:
                            end_idx = j
                            break
                        
                    # 组合JSON字符串
                    json_str = '\n'.join(lines[start_idx:end_idx+1])
                    # 清理可能的非JSON内容
                    json_str = self._extract_json_object(json_str)
                        
                    if json_str:
                        plugin_info = json.loads(json_str)
                        if plugin_info.get('school_code') == school_code:
                            return plugin_info
                                
            # 如果上面的方法失败，尝试查找特定格式
            import re
            # 查找包含学校代码和版本信息的格式
            pattern = rf'{school_code}.*?(plugin_version|version)["\']?\s*:\s*["\']([^"\']+)["\']?.*?sha256["\']?\s*:\s*["\']([^"\']+)["\']?', re.DOTALL
            match = re.search(pattern, body.replace('\n', ' '))
            if match:
                return {
                    'school_code': school_code,
                    'plugin_version': match.group(2),
                    'sha256': match.group(3)
                }
                    
            # 更宽松的匹配模式
            version_patterns = [
                rf'{school_code}.*?v(\d+\.\d+\.\d+).*?([a-fA-F0-9]{{64}})',  # school_code v1.0.0 sha256
                rf'{school_code}.*?(\d+\.\d+\.\d+).*?([a-fA-F0-9]{{64}})',   # school_code 1.0.0 sha256
            ]
                
            for pat in version_patterns:
                match = re.search(pat, body.replace('\n', ' '))
                if match:
                    return {
                        'school_code': school_code,
                        'plugin_version': match.group(1),
                        'sha256': match.group(2)
                    }
                    
        except Exception as e:
            logger.error(f"解析插件信息失败: {e}")
        return None
    
    def _infer_plugin_info_from_assets(self, assets: list, school_code: str, release_data: dict) -> Optional[Dict[str, Any]]:
        """
        从发布资产中推断插件信息
        
        Args:
            assets: 发布资产列表
            school_code: 院校代码
            release_data: 发布数据
        
        Returns:
            插件信息字典，如果未找到则返回 None
        """
        try:
            # 查找与学校代码匹配的ZIP文件
            for asset in assets:
                asset_name = asset.get('name', '')
                expected_name = f"school_{school_code}_plugin.zip"
                if asset_name == expected_name:
                    # 从发布说明中查找版本信息
                    tag_name = release_data.get('tag_name', 'v1.0.0')
                    version = tag_name.lstrip('v')
                    
                    # 如果发布说明中有时间戳版本，优先使用
                    body_text = release_data.get('body', '')
                    if '"plugin_version":' in body_text:
                        import re
                        # 查找 "plugin_version": "timestamp" 格式
                        version_match = re.search(r'"plugin_version":\s*"([^"]+)"', body_text)
                        if version_match:
                            version = version_match.group(1)
                    
                    # 从资产中获取校验和（如果有提供）
                    sha256 = None
                    if 'body' in release_data:
                        body_text = release_data['body']
                        if school_code in body_text:
                            import re
                            # 查找SHA256校验和
                            checksum_matches = re.findall(r'[a-fA-F0-9]{64}', body_text)
                            for match in checksum_matches:
                                # 简单检查是否与当前资产相关
                                if len(checksum_matches) == 1:
                                    sha256 = match
                                    break
                                elif school_code in body_text:
                                    # 如果有多个校验和，需要更精确的匹配
                                    # 这里简化处理，使用第一个匹配的
                                    sha256 = match
                                    break
                    
                    # 如果没找到校验和，使用资产的校验和（如果API提供）
                    if not sha256 and 'sha256' in asset:
                        sha256 = asset['sha256']
                    
                    return {
                        'school_code': school_code,
                        'plugin_version': version,
                        'sha256': sha256 or '',
                        'download_url': asset.get('browser_download_url', ''),
                        'contributor': release_data.get('author', {}).get('login', 'Unknown')
                    }
            
            # 如果没有找到特定学校的资产，使用第一个ZIP文件
            for asset in assets:
                asset_name = asset.get('name', '')
                if asset_name.endswith('.zip'):
                    tag_name = release_data.get('tag_name', 'v1.0.0')
                    version = tag_name.lstrip('v')
                    
                    return {
                        'school_code': school_code,
                        'plugin_version': version,
                        'sha256': '',
                        'download_url': asset.get('browser_download_url', ''),
                        'contributor': release_data.get('author', {}).get('login', 'Unknown')
                    }
                    
        except Exception as e:
            logger.error(f"从资产中推断插件信息失败: {e}")
        return None
    
    def _fetch_plugins_index(self) -> Optional[Dict[str, Any]]:
        """
        从远程获取插件索引文件
        
        Returns:
            插件索引字典，如果获取失败则返回 None
        """
        try:
            # 首先检查缓存
            if self.plugins_index_cache:
                return self.plugins_index_cache
            
            req = urllib.request.Request(
                f"https://raw.githubusercontent.com/{self.GITHUB_REPO_DEFAULT}/main/plugins_index.json",
                headers={'User-Agent': 'Capture_Push-SchoolPluginManager'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                index_data = json.loads(response.read().decode('utf-8'))
            
            # 缓存结果
            self.plugins_index_cache = index_data
            return index_data
            
        except urllib.error.URLError as e:
            logger.warning(f"直接访问插件索引文件失败: {e}")
            
            # 尝试使用代理访问
            try:
                proxy_url = PROXY_URL_PREFIX + f"https://raw.githubusercontent.com/{self.GITHUB_REPO_DEFAULT}/main/plugins_index.json"
                logger.info(f"尝试使用代理访问插件索引: {proxy_url}")
                req_proxy = urllib.request.Request(
                    proxy_url,
                    headers={'User-Agent': 'Capture_Push-SchoolPluginManager'}
                )
                
                with urllib.request.urlopen(req_proxy, timeout=20) as response:
                    index_data = json.loads(response.read().decode('utf-8'))
                
                # 缓存结果
                self.plugins_index_cache = index_data
                return index_data
                
            except Exception as proxy_error:
                logger.error(f"通过代理访问插件索引也失败: {proxy_error}")
                return None
        except Exception as e:
            logger.error(f"获取插件索引失败: {e}")
            return None
    
    def get_plugin_info_from_index(self, school_code: str) -> Optional[Dict[str, Any]]:
        """
        从插件索引中获取指定插件的信息
        
        Args:
            school_code: 院校代码
        
        Returns:
            插件信息字典，如果未找到则返回 None
        """
        plugins_index = self._fetch_plugins_index()
        if plugins_index and isinstance(plugins_index, dict):
            # 检查索引格式，可能是直接的插件列表，也可能有专门的plugins键
            plugins_list = plugins_index.get('plugins', [])
            if not plugins_list:  # 如果没有plugins键，尝试直接使用整个索引
                if isinstance(plugins_index, list):
                    plugins_list = plugins_index
            
            for plugin in plugins_list:
                if plugin.get('school_code') == school_code:
                    return plugin
        
        return None
    
    def _extract_json_object(self, text: str) -> Optional[str]:
        """
        从文本中提取JSON对象
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            JSON字符串，如果未找到则返回 None
        """
        try:
            # 查找第一个 { 的位置
            start = text.find('{')
            if start == -1:
                return None
                
            # 从头开始计数括号
            brace_count = 0
            for i, char in enumerate(text[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start:i+1]
        except Exception:
            pass
        return None
    
    def _get_download_url(self, release_data: dict, school_code: str) -> Optional[str]:
        """
        从发布数据中获取指定院校插件的下载URL
            
        Args:
            release_data: GitHub Release 数据
            school_code: 院校代码
            
        Returns:
            下载URL，如果未找到则返回 None
        """
        try:
            assets = release_data.get('assets', [])
            for asset in assets:
                # 查找特定院校的ZIP文件，格式为 school_[code]_plugin.zip
                expected_name = f"school_{school_code}_plugin.zip"
                if asset['name'] == expected_name:
                    return asset['browser_download_url']
            # 如果没找到特定院校的ZIP，返回第一个匹配的ZIP
            for asset in assets:
                if f"school_{school_code}_plugin.zip" in asset['name']:
                    return asset['browser_download_url']
        except Exception as e:
            logger.error(f"获取下载URL失败: {e}")
        return None
    
    def _compare_version(self, v1: str, v2: str) -> int:
        """
        比较版本号
        
        Args:
            v1: 远程版本
            v2: 本地版本
            
        Returns:
            1 if v1 > v2 (有更新)
            0 if v1 == v2 (无更新)
            -1 if v1 < v2 (当前版本更高)
        """
        try:
            # 处理版本号格式 (x.x.x)
            parts1 = [int(x) for x in v1.replace('-', '.').replace('_', '.').split('.') if x.isdigit()]
            parts2 = [int(x) for x in v2.replace('-', '.').replace('_', '.').split('.') if x.isdigit()]
            
            # 补齐长度
            max_len = max(len(parts1), len(parts2))
            parts1.extend([0] * (max_len - len(parts1)))
            parts2.extend([0] * (max_len - len(parts2)))
            
            # 比较每个版本段
            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except Exception as e:
            logger.error(f"版本号比较失败: {e}")
            return 0
    
    def download_and_install_plugin(self, school_code: str, plugin_info: Dict[str, Any]) -> bool:
        """
        下载并安装插件
            
        Args:
            school_code: 院校代码
            plugin_info: 插件信息字典
            
        Returns:
            是否成功安装
        """
        try:
            download_url = plugin_info.get('download_url')
            expected_sha256 = plugin_info.get('sha256')
                
            if not download_url:
                logger.error(f"插件 {school_code} 缺少下载URL")
                return False
                    
            logger.info(f"正在下载插件包: {download_url}")
                
            # 下载插件到临时目录
            temp_dir = Path(tempfile.gettempdir()) / "Capture_Push_Plugins"
            temp_dir.mkdir(exist_ok=True)
            zip_path = temp_dir / f"school_{school_code}_plugin.zip"
                
            # 下载
            req = urllib.request.Request(
                download_url,
                headers={'User-Agent': 'Capture_Push-SchoolPluginManager'}
            )
                
            try:
                urllib.request.urlretrieve(download_url, str(zip_path))
            except Exception as direct_error:
                logger.warning(f"直接下载失败: {direct_error}")
                # 使用代理下载
                proxy_url = PROXY_URL_PREFIX + download_url
                logger.info(f"尝试使用代理下载: {proxy_url}")
                req_proxy = urllib.request.Request(
                    proxy_url,
                    headers={'User-Agent': 'Capture_Push-SchoolPluginManager'}
                )
                urllib.request.urlretrieve(proxy_url, str(zip_path))
                
            # 如果提供了SHA256，则验证
            if expected_sha256:
                calculated_sha256 = self._calculate_file_hash(str(zip_path))
                if calculated_sha256.lower() != expected_sha256.lower():
                    logger.error(f"插件包校验失败! 期望: {expected_sha256}, 实际: {calculated_sha256}")
                    return False
                else:
                    logger.info(f"插件包校验成功")
            else:
                logger.warning(f"缺少SHA256校验和，跳过校验")
                
            # 创建时间戳目录
            import time
            timestamp = str(int(time.time()))
            final_plugin_dir = self.plugins_dir / school_code
                
            # 备份当前插件（如果存在）
            if final_plugin_dir.exists():
                backup_dir = self.plugins_dir / f"backup_{school_code}_{int(time.time())}"
                import shutil
                shutil.move(str(final_plugin_dir), str(backup_dir))
                logger.info(f"已备份原插件到: {backup_dir}")
                
            # 解压插件到目标目录
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(str(final_plugin_dir))
                
            # 写入版本信息
            version_file = final_plugin_dir / "version.txt"
            version_file.write_text(plugin_info.get('plugin_version', 'unknown'), encoding='utf-8')
                
            logger.info(f"插件 {school_code} 安装成功")
            return True
                
        except Exception as e:
            logger.error(f"下载并安装插件失败: {e}")
            return False
    
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
    
    def load_plugin(self, school_code: str):
        """
        动态加载指定院校的插件
            
        Args:
            school_code: 院校代码
            
        Returns:
            插件模块，如果加载失败则返回 None
        """
        try:
            # 首先尝试从插件目录加载
            plugin_dir = self.plugins_dir / school_code
            plugin_init_file = plugin_dir / "__init__.py"
                
            if plugin_init_file.exists():
                # 为了支持相对导入，需要将插件目录添加到 sys.path
                import sys
                plugin_dir_str = str(plugin_dir)
                if plugin_dir_str not in sys.path:
                    sys.path.insert(0, plugin_dir_str)
                spec = importlib.util.spec_from_file_location(
                    f"plugins_school_{school_code}", 
                    str(plugin_init_file)
                )
                module = importlib.util.module_from_spec(spec)
                # 设置模块的 __package__ 属性以支持相对导入
                module.__package__ = f"plugins_school_{school_code}"
                spec.loader.exec_module(module)
                # 移除临时添加的路径
                if plugin_dir_str in sys.path:
                    sys.path.remove(plugin_dir_str)
                return module
                
            # 如果插件目录中没有找到，尝试从原始位置加载
            try:
                return importlib.import_module(f"core.school.{school_code}")
            except ImportError:
                pass
                    
        except Exception as e:
            logger.error(f"加载插件 {school_code} 失败: {e}")
        return None
    
    def get_available_plugins(self) -> Dict[str, str]:
        """
        获取所有可用的插件列表
        
        Returns:
            院校代码到院校名称的映射
        """
        plugins = {}
        
        # 从插件目录获取
        if self.plugins_dir.exists():
            for item in self.plugins_dir.iterdir():
                if item.is_dir() and not item.name.startswith('backup_') and not item.name.startswith('v') and item.name != 'current':
                    init_file = item / "__init__.py"
                    if init_file.exists():
                        try:
                            # 为了支持相对导入，需要将插件目录添加到 sys.path
                            import sys
                            plugin_dir_str = str(item)
                            if plugin_dir_str not in sys.path:
                                sys.path.insert(0, plugin_dir_str)
                            spec = importlib.util.spec_from_file_location(
                                f"plugins_school_{item.name}", 
                                str(init_file)
                            )
                            module = importlib.util.module_from_spec(spec)
                            # 设置模块的 __package__ 属性以支持相对导入
                            module.__package__ = f"plugins_school_{item.name}"
                            spec.loader.exec_module(module)
                            # 移除临时添加的路径
                            if plugin_dir_str in sys.path:
                                sys.path.remove(plugin_dir_str)
                            
                            school_name = getattr(module, "SCHOOL_NAME", item.name)
                            plugins[item.name] = school_name
                        except Exception:
                            continue
        
        return plugins


# 全局插件管理器实例（延迟初始化）
_plugin_manager_instance = None

def get_plugin_manager():
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = SchoolPluginManager()
    return _plugin_manager_instance

plugin_manager = get_plugin_manager()