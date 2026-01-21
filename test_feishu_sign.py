#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试飞书机器人签名校验功能
"""
import time
import hashlib
import base64
import hmac

def gen_sign(timestamp, secret):
    """生成飞书机器人签名校验所需的签名"""
    # 拼接timestamp和secret
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    # 对结果进行base64处理
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign

def test_signature():
    """测试签名生成函数"""
    # 使用示例数据测试
    timestamp = str(int(time.time()))  # 当前时间戳
    secret = "your_secret_key"  # 示例密钥
    
    print(f"时间戳: {timestamp}")
    print(f"密钥: {secret}")
    
    signature = gen_sign(timestamp, secret)
    print(f"生成的签名: {signature}")
    
    # 测试使用飞书官方文档中的示例数据验证
    # 假设时间戳是1599360473，密钥是test
    example_timestamp = "1599360473"
    example_secret = "test"
    example_signature = gen_sign(example_timestamp, example_secret)
    print(f"\n示例验证:")
    print(f"时间戳: {example_timestamp}")
    print(f"密钥: {example_secret}")
    print(f"生成的签名: {example_signature}")

if __name__ == "__main__":
    test_signature()