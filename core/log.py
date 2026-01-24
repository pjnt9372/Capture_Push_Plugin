# -*- coding: utf-8 -*-
"""
统一日志管理模块
提供项目级别的日志配置和初始化功能
支持脚本形式在用户处运行，配置和日志统一使用 AppData 目录
"""
import logging
import logging.config
import logging.handlers
import sys
import os
import configparser
import datetime
import shutil
from pathlib import Path


def pack_logs():
    """
    将 AppData 中的日志目录打包成一个文本文件。
    返回打包文件的路径。
    """
    try:
        localappdata = os.environ.get('LOCALAPPDATA')
        if not localappdata:
            raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
        
        log_dir = Path(localappdata) / 'Capture_Push'
        if not log_dir.exists():
            raise FileNotFoundError(f"日志目录不存在: {log_dir}")
        
        # 确定输出文件名和路径
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"capture_push_crash_report_{timestamp}.txt"
        archive_path = log_dir / archive_name

        with open(archive_path, 'w', encoding='utf-8') as archive_file:
            archive_file.write(f"Capture_Push 崩溃报告 - 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            archive_file.write("=" * 80 + "\n\n")

            # 遍历日志目录，查找所有 .log 文件
            for log_file_path in log_dir.glob("*.log"):
                if log_file_path == archive_path:  # 跳过当前正在写的归档文件
                    continue
                archive_file.write(f"文件: {log_file_path.name}\n")
                archive_file.write("-" * 40 + "\n")
                try:
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        archive_file.write(f.read())
                except Exception as e:
                    archive_file.write(f"读取文件失败: {e}\n")
                archive_file.write("\n" + "-" * 40 + "\n\n")

        return str(archive_path)
    except Exception as e:
        print(f"打包日志失败: {e}")
        return None


def get_config_path():
    """
    获取配置文件路径（AppData 目录）
    
    Returns:
        Path: 配置文件路径对象
    
    Raises:
        RuntimeError: 如果无法获取 AppData 目录
        FileNotFoundError: 如果配置文件不存在
    """
    # 获取 AppData 目录
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
    
    config_path = Path(localappdata) / 'Capture_Push' / 'config.ini'
    
    # 配置文件必须存在
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    return config_path


def cleanup_old_logs(log_dir, max_total_size_mb=50, max_days=7):
    """
    清理旧日志文件，按大小和天数限制清理。
    
    Args:
        log_dir: 日志目录路径
        max_total_size_mb: 最大大小限制(MB)
        max_days: 最大保留天数
    """
    try:
        import time
        
        # 计算7天前的时间戳
        seven_days_ago = time.time() - (max_days * 24 * 60 * 60)
        
        # 按大小清理的文件
        size_cleanup_files = []
        # 按天数清理的文件
        day_cleanup_files = []
        
        for f in log_dir.glob("*.log*"):
            if f.is_file():
                stat_info = f.stat()
                mtime = stat_info.st_mtime
                size = stat_info.st_size
                
                # 检查是否超过7天
                if mtime < seven_days_ago:
                    day_cleanup_files.append((f, mtime, size))
                else:
                    size_cleanup_files.append((f, mtime, size))
        
        # 首先删除超过7天的文件
        for file_info in day_cleanup_files:
            expired_file, _, _ = file_info
            try:
                expired_file.unlink()
                print(f"[*] 已自动删除超过{max_days}天的日志: {expired_file.name}")
            except Exception as e:
                print(f"[!] 无法删除过期日志文件 {expired_file.name}: {e}")
        
        # 对剩余文件按大小进行清理
        log_files = size_cleanup_files
        # 按修改时间从旧到新排序
        log_files.sort(key=lambda x: x[1])
        
        total_size = sum(f[2] for f in log_files)
        max_total_size = max_total_size_mb * 1024 * 1024
        
        while total_size > max_total_size and log_files:
            oldest_file, _, size = log_files.pop(0)
            try:
                oldest_file.unlink()
                total_size -= size
                print(f"[*] 已自动删除过旧日志: {oldest_file.name}")
            except Exception as e:
                print(f"[!] 无法删除日志文件 {oldest_file.name}: {e}")
                
    except Exception as e:
        print(f"[!] 清理日志目录失败: {e}")


def get_log_file_path(module_name=None):
    """
    获取日志文件路径（AppData 目录）。
    现在统一使用当前日期作为文件名。
    """
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
    
    appdata_dir = Path(localappdata) / 'Capture_Push'
    appdata_dir.mkdir(parents=True, exist_ok=True)
    
    # 统一使用日期命名
    today = datetime.date.today().strftime("%Y-%m-%d")
    return appdata_dir / f'{today}.log'


def init_logger(module_name):
    """
    初始化日志系统（AppData 目录）
    
    Args:
        module_name: 模块名称，将显示在日志条目中
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    config_path = get_config_path()
    log_file_path = get_log_file_path()
    appdata_dir = log_file_path.parent
    
    # 1. 自动清理旧日志
    cleanup_old_logs(appdata_dir)
    
    # 2. 读取配置文件获取日志级别
    config = configparser.ConfigParser()
    config.read(str(config_path), encoding='utf-8')
    log_level_str = config.get('logging', 'level', fallback='DEBUG')
    log_level = getattr(logging, log_level_str.upper(), logging.DEBUG)
    
    # 3. 配置 Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 避免重复添加处理器（针对同进程内多次调用）
    has_console = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    has_file = any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file_path.absolute()) for h in root_logger.handlers)
    
    # 统一的格式化器：包含模块名 (%(name)s)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    if not has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)
    
    if not has_file:
        # 清除所有旧的文件处理器（如果有的话）
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)
        
        # 添加新的统一文件处理器
        # 单个文件上限 10MB，保留多个备份（总大小由 cleanup_old_logs 控制）
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file_path), 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=20,         # 保留足够多的滚动文件，清理逻辑在 cleanup_old_logs 中
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # 返回子 logger
    logger = logging.getLogger(module_name)
    logger.info(f"🚀 模块日志初始化: {module_name} -> {log_file_path.name}")
    
    return logger


def get_logger(module_name=None):
    """
    获取日志记录器
    
    Args:
        module_name: 模块名称，如果为 None 则返回 root logger
        
    Returns:
        logging.Logger: 日志记录器
    """
    if module_name:
        return logging.getLogger(module_name)
    return logging.getLogger()
