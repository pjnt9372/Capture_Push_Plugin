# -*- coding: utf-8 -*-
import requests
import json
import configparser
import hashlib
import base64
import hmac
import time
from pathlib import Path

try:
    from log import init_logger, get_config_path
    from config_manager import load_config
except ImportError:
    from core.log import init_logger, get_config_path
    from core.config_manager import load_config

# 延迟初始化
_logger = None
_config_path = None

def gen_sign(timestamp, secret):
    """生成飞书机器人签名校验所需的签名"""
    # 拼接timestamp和secret
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    # 对结果进行base64处理
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def _get_logger():
    global _logger, _config_path
    if _logger is None:
        _logger = init_logger('feishu_sender')
        _config_path = get_config_path()
    return _logger

def _get_config_path():
    global _config_path
    if _config_path is None:
        _get_logger()
    return _config_path

class FeishuSender:
    """飞书机器人推送实现"""
    
    def send(self, subject, content):
        logger = _get_logger()
        cfg = load_config()
        
        try:
            webhook_url = cfg.get("feishu", "webhook_url", fallback="").strip()
            secret = cfg.get("feishu", "secret", fallback="").strip()
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.error("配置文件中缺少 [feishu] 配置节或 webhook_url")
            return False

        if not webhook_url:
            logger.error("飞书 Webhook 地址为空")
            return False

        # 飞书消息格式
        # 考虑到 subject 和 content，我们合并为文本发送
        message_text = f"{subject}\n\n{content}"
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": message_text
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # 如果配置了密钥，则添加签名参数
        if secret:
            timestamp = str(int(time.time()))
            logger.debug(f"生成签名 - 时间戳: {timestamp}, 秘钥长度: {len(secret)}")
            sign = gen_sign(timestamp, secret)
            logger.debug(f"生成的签名: {sign}")
            # 将时间戳和签名作为查询参数添加到webhook URL
            separator = '&' if '?' in webhook_url else '?'
            webhook_url_with_params = f"{webhook_url}{separator}timestamp={timestamp}&sign={sign}"
        else:
            webhook_url_with_params = webhook_url

        try:
            logger.info(f"正在向飞书发送消息: {subject}")
            response = requests.post(
                webhook_url_with_params, 
                data=json.dumps(payload), 
                headers=headers,
                timeout=10
            )
            result = response.json()
            
            if result.get("code") == 0:
                logger.info("飞书消息发送成功")
                return True
            else:
                error_msg = result.get('msg', '')
                logger.error(f"飞书消息发送失败: {error_msg}")
                # 特别处理签名验证失败的错误
                if "sign match fail" in error_msg or "timestamp is not within one hour" in error_msg:
                    logger.error("可能是时间戳过期或签名计算错误，请检查系统时间和密钥配置")
                return False
                
        except Exception as e:
            logger.error(f"调用飞书接口发生异常: {e}")
            return False
