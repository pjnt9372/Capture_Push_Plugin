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
from pathlib import Path


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


def get_log_file_path(module_name):
    """
    获取日志文件路径（AppData 目录）
    
    Args:
        module_name: 模块名称，用于生成日志文件名
        
    Returns:
        Path: 日志文件路径对象
        
    Raises:
        RuntimeError: 如果无法获取 AppData 目录
    """
    localappdata = os.environ.get('LOCALAPPDATA')
    if not localappdata:
        raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
    
    appdata_dir = Path(localappdata) / 'Capture_Push'
    
    # 确保目录存在
    appdata_dir.mkdir(parents=True, exist_ok=True)
    
    return appdata_dir / f'{module_name}.log'


def init_logger(module_name):
    """
    初始化日志系统（AppData 目录）
    
    Args:
        module_name: 模块名称，用于生成日志文件名（如 'push', 'getCourseGrades'）
        
    Returns:
        logging.Logger: 配置好的日志记录器
        
    Raises:
        FileNotFoundError: 配置文件不存在
        RuntimeError: 无法获取环境变量或初始化失败
    """
    config_path = get_config_path()
    log_file_path = get_log_file_path(module_name)
    
    # 读取配置文件获取日志级别
    config = configparser.ConfigParser()
    config.read(str(config_path), encoding='utf-8')
    log_level_str = config.get('logging', 'level', fallback='DEBUG')
    log_level = getattr(logging, log_level_str.upper(), logging.DEBUG)
    
    # 获取 root logger
    root_logger = logging.getLogger()
    
    # 移除所有现有的处理器
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
        root_logger.removeHandler(handler)
    
    # 设置日志级别
    root_logger.setLevel(log_level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # 添加新的文件处理器到 AppData 目录（强制 UTF-8 编码）
    # 使用 RotatingFileHandler 限制单个日志文件大小为 1MB，最多保留 5 个备份文件
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file_path), 
        maxBytes=1024*1024,  # 1MB
        backupCount=5,      # 最多保留 5 个备份文件
        encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # 记录初始化信息
    root_logger.info(f"✅ 日志系统初始化成功: {module_name}")
    root_logger.info(f"📝 日志文件: {log_file_path}")
    root_logger.info(f"⚙️ 配置文件: {config_path}")
    root_logger.info(f"📋 日志级别: {log_level_str}")
    
    return root_logger


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
