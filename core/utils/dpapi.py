# -*- coding: utf-8 -*-
import ctypes
import ctypes.wintypes

# 定义 DATA_BLOB 结构体
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char))
    ]

def encrypt(data: str) -> bytes:
    """使用 Windows DPAPI 加密字符串"""
    if not data:
        return b""
    
    # 将字符串编码为字节
    data_bytes = data.encode('utf-8')
    
    # 准备输入 BLOB
    blob_in = DATA_BLOB(
        len(data_bytes), 
        ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_char))
    )
    # 准备输出 BLOB
    blob_out = DATA_BLOB()
    
    # 调用 CryptProtectData
    # 参数: (pDataIn, szDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
    if ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        "Capture_Push Configuration Data",  # 数据描述
        None,                               # 熵（可选，增加安全性）
        None,                               # 保留项
        None,                               # 提示结构体
        0,                                  # 标志位
        ctypes.byref(blob_out)
    ):
        # 获取加密后的数据
        result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        # 释放 DPAPI 分配的内存
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return result
    else:
        raise ctypes.WinError()

def decrypt(encrypted_data: bytes) -> str:
    """使用 Windows DPAPI 解密数据"""
    if not encrypted_data:
        return ""
    
    # 准备输入 BLOB
    blob_in = DATA_BLOB(
        len(encrypted_data), 
        ctypes.cast(ctypes.create_string_buffer(encrypted_data), ctypes.POINTER(ctypes.c_char))
    )
    # 准备输出 BLOB
    blob_out = DATA_BLOB()
    
    # 调用 CryptUnprotectData
    # 参数: (pDataIn, ppszDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
    if ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,           # 不获取数据描述
        None,           # 熵
        None,           # 保留项
        None,           # 提示结构体
        0,              # 标志位
        ctypes.byref(blob_out)
    ):
        # 获取解密后的数据并解码为字符串
        result = ctypes.string_at(blob_out.pbData, blob_out.cbData).decode('utf-8')
        # 释放 DPAPI 分配的内存
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return result
    else:
        raise ctypes.WinError()

def encrypt_file(file_path: str):
    """加密整个文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    encrypted = encrypt(content)
    with open(file_path, 'wb') as f:
        f.write(encrypted)

def decrypt_file_to_str(file_path: str) -> str:
    """读取并解密文件内容到字符串"""
    with open(file_path, 'rb') as f:
        encrypted = f.read()
    try:
        # 尝试解密
        return decrypt(encrypted)
    except Exception:
        # 如果解密失败（可能是未加密文件），尝试直接读取为文本
        try:
            return encrypted.decode('utf-8')
        except UnicodeDecodeError:
            # 彻底失败，返回空或重新抛出异常
            raise
