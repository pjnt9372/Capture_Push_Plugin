# -*- coding: utf-8 -*-
"""
统一日志管理模块
提供项目级别的日志配置和初始化功能
"""
import logging
import logging.config
import configparser
import sys
import os
from pathlib import Path


def get_config_path():
    """
    获取配置文件路径
    
    Returns:
        Path: 配置文件路径对象
    """
    if getattr(sys, 'frozen', False):
        # 打包后的exe运行，从 AppData 目录读取配置
        appdata_dir = Path(os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', '.'))) / 'GradeTracker'
        appdata_dir.mkdir(parents=True, exist_ok=True)
        config_path = appdata_dir / 'config.ini'
        
        # 如果 AppData 目录中没有 config.ini，则从原始位置复制一份
        if not config_path.exists():
            import shutil
            original_base = Path(sys._MEIPASS)
            original_config = original_base / 'config.ini'
            if original_config.exists():
                shutil.copy2(original_config, config_path)
    else:
        # 正常脚本运行
        base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / 'config.ini'
    
    return config_path


def get_log_file_path(module_name):
    """
    获取日志文件路径
    
    Args:
        module_name: 模块名称，用于生成日志文件名
        
    Returns:
        Path: 日志文件路径对象
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境，使用 AppData\Local\GradeTracker
        appdata_dir = Path(os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', '.'))) / 'GradeTracker'
        appdata_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = appdata_dir / f'{module_name}.log'
    else:
        # 开发环境，使用项目根目录
        base_dir = Path(__file__).resolve().parent.parent
        log_file_path = base_dir / f'{module_name}.log'
    
    return log_file_path


def init_logger(module_name):
    """
    初始化日志系统
    
    Args:
        module_name: 模块名称，用于生成日志文件名（如 'push', 'getCourseGrades'）
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    config_path = get_config_path()
    log_file_path = get_log_file_path(module_name)
    
    try:
        # 尝试从 config.ini 加载日志配置
        logging.config.fileConfig(str(config_path))
        
        # 获取 root logger
        root_logger = logging.getLogger()
        
        # 移除原有的 FileHandler，替换为指向用户可写目录的 FileHandler
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)
        
        # 添加新的文件处理器到用户可写目录
        file_handler = logging.FileHandler(str(log_file_path), encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        
        logger = root_logger
        logger.info(f"✅ 成功从 config.ini 加载日志配置")
        logger.info(f"📝 日志文件路径: {log_file_path}")
        
    except (configparser.Error, Exception) as e:
        # 配置文件有问题，使用默认配置
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
            handlers=[
                logging.StreamHandler(),  # 控制台输出
                logging.FileHandler(str(log_file_path), encoding='utf-8')  # 文件输出
            ]
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️ 无法加载 config.ini 日志配置，使用默认配置: {e}")
        logger.info(f"📝 日志文件路径: {log_file_path}")
    
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
