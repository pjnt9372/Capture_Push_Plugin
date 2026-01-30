# -*- coding: utf-8 -*-
"""
Windows身份驗證工具模塊
用於處理Windows Hello驗證等功能
"""

import os
import sys
import subprocess
import ctypes
from pathlib import Path

# 導入日誌模塊
try:
    from log import init_logger
except ImportError:
    from core.log import init_logger

# 初始化日誌記錄器
logger = init_logger("windows_auth")

# Windows API 常量和函數
try:
    # 尝试导入Windows Hello相关的库
    import win32security
    import win32api
    import win32con
    HAS_WIN32API = True
except ImportError:
    logger.warning("win32api模块不可用，将使用备用验证方法")
    HAS_WIN32API = False

try:
    # 尝试导入Windows Runtime API (用于Windows Hello)
    import asyncio
    from winrt.windows.security.credentials import UserConsentVerifier
    from winrt.windows.security.credentials.ui import AuthenticationProtocol, CredentialPicker
    HAS_WINRT = True
except ImportError:
    logger.warning("winrt模块不可用，将使用备用验证方法")
    HAS_WINRT = False


def verify_with_windows_hello():
    """
    通过Windows Hello或Windows安全中心验证用户身份
    """
    logger.debug("開始Windows Hello驗證")
    
    # 优先尝试使用Windows Runtime API进行生物识别验证
    if HAS_WINRT:
        try:
            # 获取认证状态
            availability = UserConsentVerifier.check_availability_async().get()
            
            if availability.name == "AVAILABLE":
                # 请求用户进行生物识别验证
                result = UserConsentVerifier.request_consent_async(
                    "请通过生物识别或PIN验证您的身份以导出配置"
                ).get()
                
                # UserConsentVerificationResult枚举值:
                # VERIFIED = 0, DEVICE_NOT_PRESENT = 1, NOT_ENROLLED = 2, 
                # CANCELED = 3, UNKNOWN_DEVICE = 4
                if result == 0:  # VERIFIED
                    logger.debug("Windows Hello生物识别验证成功")
                    return True
                elif result == 1:  # DEVICE_NOT_PRESENT
                    logger.debug("设备不支持生物识别验证")
                elif result == 2:  # NOT_ENROLLED
                    logger.debug("设备未注册生物识别")
                elif result == 3:  # CANCELED
                    logger.debug("用户取消了验证")
                    
        except Exception as e:
            logger.warning(f"Windows Hello验证失败: {e}")
    
    # 尝试使用CredUI API进行Windows安全中心验证
    try:
        import ctypes
        from ctypes import wintypes
        import getpass
        
        # 加载 DLL
        credui = ctypes.WinDLL('credui.dll')
        ole32 = ctypes.WinDLL('ole32.dll')
        
        # 定义结构体和常量
        CREDUIWIN_GENERIC = 0x1
        CREDUIWIN_CHECKBOX = 0x2
        CREDUIWIN_AUTHPACKAGE_ONLY = 0x10
        CREDUIWIN_IN_CRED_ONLY = 0x20
        CREDUIWIN_ENUMERATE_CURRENT_USER = 0x200
        CREDUIWIN_SECURE_PROMPT = 0x1000
        
        class CREDUI_INFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hwndParent", wintypes.HWND),
                ("pszMessageText", wintypes.LPCWSTR),
                ("pszCaptionText", wintypes.LPCWSTR),
                ("hbmBanner", wintypes.HBITMAP)
            ]
        
        # 准备函数：CredPackAuthenticationBufferW (修复 Error 87 的关键)
        # 该函数将用户名打包成 API 能识别的二进制格式
        CredPackAuthenticationBufferW = credui.CredPackAuthenticationBufferW
        CredPackAuthenticationBufferW.argtypes = [
            wintypes.DWORD,     # dwFlags
            wintypes.LPCWSTR,   # pszUserName
            wintypes.LPCWSTR,   # pszPassword
            ctypes.c_void_p,    # pPackedCredentials
            ctypes.POINTER(wintypes.DWORD) # pcbPackedCredentials
        ]
        CredPackAuthenticationBufferW.restype = wintypes.BOOL

        # 准备函数：CredUIPromptForWindowsCredentialsW
        CredUIPromptForWindowsCredentialsW = credui.CredUIPromptForWindowsCredentialsW
        CredUIPromptForWindowsCredentialsW.argtypes = [
            ctypes.POINTER(CREDUI_INFO),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.ULONG),
            wintypes.LPCVOID,       # pvInAuthBuffer (这里不能是 None)
            wintypes.ULONG,         # ulInAuthBufferSize
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.ULONG),
            ctypes.POINTER(wintypes.BOOL),
            wintypes.DWORD
        ]
        CredUIPromptForWindowsCredentialsW.restype = wintypes.DWORD

        # ================= 步骤 A: 打包当前用户的凭据缓冲区 =================
        current_user = getpass.getuser()
        
        # 第一次调用获取所需的缓冲区大小
        packed_size = wintypes.DWORD(0)
        CredPackAuthenticationBufferW(0, current_user, "", None, ctypes.byref(packed_size))
        
        # 分配缓冲区
        in_auth_buffer = (ctypes.c_byte * packed_size.value)()
        
        # 第二次调用执行打包
        if not CredPackAuthenticationBufferW(0, current_user, "", in_auth_buffer, ctypes.byref(packed_size)):
            logger.debug(f"凭据打包失败，错误码: {ctypes.GetLastError()}")
        else:
            # ================= 步骤 B: 调起验证窗口 =================
            cred_info = CREDUI_INFO()
            cred_info.cbSize = ctypes.sizeof(CREDUI_INFO)
            cred_info.hwndParent = 0  # 使用0表示无父窗口
            cred_info.pszMessageText = ctypes.c_wchar_p(f"Capture Push 配置导出保护\n请验证身份以导出明文配置。")
            cred_info.pszCaptionText = ctypes.c_wchar_p("身份验证")
            cred_info.hbmBanner = None

            auth_package = wintypes.ULONG(0)
            out_buf = ctypes.c_void_p(0)
            out_size = wintypes.ULONG(0)
            save_cred = wintypes.BOOL(False)
            
            # 组合 Flags: 
            # AUTHPACKAGE_ONLY: 限制使用系统验证包
            # IN_CRED_ONLY: 验证我们传入的 in_auth_buffer，而不是让用户输入新用户名
            flags = CREDUIWIN_AUTHPACKAGE_ONLY | CREDUIWIN_IN_CRED_ONLY
            
            logger.debug(f"调起 Windows 安全中心验证, 用户: {current_user}, Flags: {hex(flags)}")

            result = CredUIPromptForWindowsCredentialsW(
                ctypes.byref(cred_info),
                0,
                ctypes.byref(auth_package),
                in_auth_buffer,         # 传入刚才打包好的缓冲区 <--- 修复点
                packed_size.value,      # 传入缓冲区大小 <--- 修复点
                ctypes.byref(out_buf),
                ctypes.byref(out_size),
                ctypes.byref(save_cred),
                flags
            )
            
            # ================= 步骤 C: 处理结果 =================
            if result == 0:  # ERROR_SUCCESS
                logger.debug("Windows 安全中心验证通过")
                if out_buf.value:
                    ole32.CoTaskMemFree(out_buf)
                return True
            elif result == 1223: # ERROR_CANCELLED
                logger.debug("用户取消了验证")
                return False
            else:
                logger.debug(f"Windows 安全中心验证失败, 代码: {result}")
                
    except Exception as e:
        logger.warning(f"Windows 安全中心验证发生未捕获异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 如果Windows Runtime不可用，尝试使用Win32 API的其他方法
    if HAS_WIN32API:
        try:
            # 使用win32api的MessageBox作为替代验证方法
            result = win32api.MessageBox(
                0,
                "为了安全验证，请确认您是要导出配置的本人用户",
                "身份验证",
                win32con.MB_YESNO | win32con.MB_ICONQUESTION
            )
            
            if result == 6:  # YES
                logger.debug("用户确认身份验证")
                return True
            else:
                logger.debug("用户取消了身份验证")
                return False
                
        except Exception as e:
            logger.warning(f"Win32 API验证失败: {e}")
    
    # 如果上述方法都不可用，返回False表示Windows Hello不可用
    logger.debug("Windows Hello验证不可用，将返回False以触发备用验证")
    return False


def verify_user_credentials():
    """
    驗證當前用戶的身份 - 优先使用Windows Hello，失败后返回False以启用备用验证
    """
    logger.debug("開始驗證當前用戶身份")
    
    # 首先尝试Windows Hello验证
    hello_verified = verify_with_windows_hello()
    
    if hello_verified:
        logger.debug("Windows Hello身份驗證成功")
        return True
    else:
        logger.debug("Windows Hello驗證失敗或不可用，将触发备用验证")
        # 返回False以触发备用验证方法（如教务系统密码验证）
        return False


def is_current_user_admin():
    """
    檢查當前用戶是否為管理員
    """
    logger.debug("檢查當前用戶是否為管理員")
    try:
        result = ctypes.windll.shell32.IsUserAnAdmin()
        logger.debug(f"管理員權限檢查結果: {result}")
        return result
    except Exception as e:
        logger.warning(f"檢查管理員權限時發生錯誤: {e}")
        return False


def get_current_username():
    """
    獲取當前登錄的用戶名
    """
    logger.debug("獲取當前登錄的用戶名")
    try:
        import getpass
        username = getpass.getuser()
        logger.debug(f"當前用戶名: {username}")
        return username
    except Exception as e:
        logger.warning(f"獲取用戶名時發生錯誤: {e}")
        return "Unknown"