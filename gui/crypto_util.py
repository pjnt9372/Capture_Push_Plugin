# -*- coding: utf-8 -*-
import base64


def encrypt(text):
    """简单加密函数，使用base64编码"""
    if not text:
        return ""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def decrypt(text):
    """简单解密函数，使用base64解码"""
    if not text:
        return ""
    try:
        return base64.b64decode(text.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""
