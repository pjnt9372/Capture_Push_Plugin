# -*- coding: utf-8 -*-
"""
Server酱推送实现
"""
import requests
import configparser
import re
import os

# 导入统一日志模块和配置路径
try:
    from log import init_logger, get_config_path
    from config_manager import load_config
except ImportError:
    from core.log import init_logger, get_config_path
    from core.config_manager import load_config

# 延迟初始化日志（在第一次调用时初始化）
_logger = None
_config_path = None


def _get_logger():
    """Lazy initialization of logger"""
    global _logger, _config_path
    if _logger is None:
        _logger = init_logger('serverchan_sender')
        _config_path = get_config_path()
    return _logger


def _get_config_path():
    """Get config path"""
    global _config_path
    if _config_path is None:
        _get_logger()  # 这会同时初始化 config_path
    return _config_path


def sc_send(sendkey, title, desp='', options=None):
    """
    Server酱消息发送函数
    
    Args:
        sendkey: Server酱的SendKey
        title: 消息标题
        desp: 消息内容
        options: 其他选项
        
    Returns:
        dict: API响应结果
    """
    if options is None:
        options = {}
    
    # 判断 sendkey 是否以 'sctp' 开头，并提取数字构造 URL
    if sendkey.startswith('sctp'):
        match = re.match(r'sctp(\d+)t', sendkey)
        if match:
            num = match.group(1)
            url = f'https://{num}.push.ft07.com/send/{sendkey}.send'
        else:
            raise ValueError('Invalid sendkey format for sctp')
    else:
        url = f'https://sctapi.ftqq.com/{sendkey}.send'
    
    params = {
        'title': title,
        'desp': desp,
        **options
    }
    headers = {
        'Content-Type': 'application/json;charset=utf-8'
    }
    
    response = requests.post(url, json=params, headers=headers)
    result = response.json()
    return result


class ServerChanSender:
    """Server酱推送实现"""

    def send(self, subject, content):
        """
        发送Server酱消息
        
        Args:
            subject: 消息主题
            content: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        logger = _get_logger()
        cfg = load_config()

        try:
            sendkey = cfg.get("serverchan", "sendkey", fallback="").strip()
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.error(f"Server酱配置缺失: {e}")
            print(f"❌ Server酱配置缺失，请检查配置文件")
            return False

        if not sendkey:
            logger.error("Server酱 SendKey 为空")
            print(f"❌ Server酱 SendKey 不能为空")
            return False

        logger.debug(f"准备发送Server酱消息: {subject}")

        try:
            logger.info(f"正在向Server酱发送消息: {subject}")
            result = sc_send(sendkey, subject, content)
            
            # 检查API返回结果
            if 'error' in result and result['error'] != 'success':
                logger.error(f"Server酱消息发送失败: {result}")
                return False
            elif 'data' in result or result.get('error') == 'success':
                logger.info("Server酱消息发送成功")
                return True
            else:
                logger.warning(f"Server酱消息发送结果未知: {result}")
                return False
                
        except Exception as e:
            logger.error(f"调用Server酱接口发生异常: {e}")
            return False