# -*- coding: utf-8 -*-
"""
统一日志管理模块
提供项目级别的日志配置和初始化功能
支持脚本形式在用户处运行，配置和日志统一使用 AppData 目录
"""
import logging
import logging.config
import sys
import os
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
    
    config_path = Path(localappdata) / 'GradeTracker' / 'config.ini'
    
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
    
    appdata_dir = Path(localappdata) / 'GradeTracker'
    
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
        Exception: logging.config.fileConfig 抛出的任何异常
    """
    config_path = get_config_path()
    log_file_path = get_log_file_path(module_name)
    
    # 从 config.ini 加载日志配置（如果失败直接崩溃）
    logging.config.fileConfig(str(config_path), disable_existing_loggers=False)
    
    # 获取 root logger
    root_logger = logging.getLogger()
    
    # 移除所有现有的 FileHandler，避免多进程冲突
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)
    
    # 添加新的文件处理器到 AppData 目录（强制 UTF-8 编码）
    file_handler = logging.FileHandler(str(log_file_path), encoding='utf-8', mode='a')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # 记录初始化信息
    root_logger.info(f"✅ 日志系统初始化成功: {module_name}")
    root_logger.info(f"📝 日志文件: {log_file_path}")
    root_logger.info(f"⚙️ 配置文件: {config_path}")
    
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
