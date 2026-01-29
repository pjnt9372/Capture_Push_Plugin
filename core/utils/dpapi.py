# -*- coding: utf-8 -*-
import ctypes
import ctypes.wintypes

# 导入日志模块
try:
    from log import init_logger
except ImportError:
    from core.log import init_logger

# 初始化日志记录器
logger = init_logger("dpapi")

# 定义 DATA_BLOB 结构体
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char))
    ]

def encrypt(data: str) -> bytes:
    """使用 Windows DPAPI 加密字符串"""
    logger.debug("开始加密数据")
    if not data:
        logger.debug("数据为空，返回空字节")
        return b""
    
    # 将字符串编码为字节
    data_bytes = data.encode('utf-8')
    logger.debug(f"准备加密 {len(data_bytes)} 字节的数据")
    
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
        logger.debug(f"加密成功，获得 {len(result)} 字节的加密数据")
        # 释放 DPAPI 分配的内存
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return result
    else:
        logger.error("DPAPI 加密失败")
        raise ctypes.WinError()

def decrypt(encrypted_data: bytes) -> str:
    """使用 Windows DPAPI 解密数据"""
    logger.debug("开始解密数据")
    if not encrypted_data:
        logger.debug("加密数据为空，返回空字符串")
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
        logger.debug(f"解密成功，获得 {len(result)} 字符的解密数据")
        # 释放 DPAPI 分配的内存
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return result
    else:
        logger.error("DPAPI 解密失败")
        raise ctypes.WinError()

def encrypt_file(file_path: str):
    """加密整个文件"""
    logger.info(f"开始加密文件: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    logger.debug(f"读取文件内容 {len(content)} 字符")
    encrypted = encrypt(content)
    with open(file_path, 'wb') as f:
        f.write(encrypted)
    logger.info(f"文件加密完成: {file_path}")

def decrypt_file_to_str(file_path: str) -> str:
    """读取并解密文件内容到字符串"""
    logger.info(f"开始解密文件: {file_path}")
    with open(file_path, 'rb') as f:
        encrypted = f.read()
    logger.debug(f"读取加密文件 {len(encrypted)} 字节")
    try:
        # 尝试解密
        result = decrypt(encrypted)
        logger.debug(f"文件解密成功")
        return result
    except Exception:
        logger.warning(f"解密失败，尝试作为明文读取: {file_path}")
        # 如果解密失败（可能是未加密文件），尝试直接读取为文本
        try:
            result = encrypted.decode('utf-8')
            logger.info(f"以明文格式读取文件成功: {file_path}")
            return result
        except UnicodeDecodeError:
            logger.error(f"文件读取失败: {file_path}")
            # 彻底失败，返回空或重新抛出异常
            raise
