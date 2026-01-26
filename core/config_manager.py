# -*- coding: utf-8 -*-
import configparser
import io
import os
from pathlib import Path
from core.log import get_config_path
from core.utils import dpapi

def load_config():
    """读取并自动解密配置文件"""
    config_path = str(get_config_path())
    cfg = configparser.ConfigParser()
    
    if not os.path.exists(config_path):
        return cfg

    try:
        # 读取二进制内容
        with open(config_path, 'rb') as f:
            raw_data = f.read()
        
        # 尝试解密
        try:
            content = dpapi.decrypt(raw_data)
            cfg.read_string(content)
        except Exception:
            # 如果解密失败，说明是明文或损坏，尝试以 utf-8 读取
            content = raw_data.decode('utf-8')
            cfg.read_string(content)
    except Exception as e:
        # 兜底：直接使用 configparser 读取（可能还是会失败，但这是最后尝试）
        cfg.read(config_path, encoding='utf-8')
    
    return cfg

def save_config(cfg):
    """保存并加密配置文件"""
    config_path = str(get_config_path())
    
    # 将配置写入字符串流
    output = io.StringIO()
    cfg.write(output)
    content = output.getvalue()
    
    # 使用 DPAPI 加密
    encrypted_data = dpapi.encrypt(content)
    
    # 写入二进制文件
    with open(config_path, 'wb') as f:
        f.write(encrypted_data)
