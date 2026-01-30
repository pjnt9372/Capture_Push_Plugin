# -*- coding: utf-8 -*-
"""
注册表操作工具模块
用于处理Windows注册表中的自启动项设置
"""

import os
import sys
import winreg
from pathlib import Path


def get_tray_exe_path():
    """
    获取托盘程序的完整路径
    根据开发环境（父目录查找）和打包环境（同级目录）双重路径策略探测
    """
    # 获取当前工作目录下的托盘程序路径
    current_dir = Path.cwd()
    tray_exe = current_dir / "Capture_Push_tray.exe"
    
    # 如果在当前目录没找到，尝试从可执行文件所在目录查找
    if not tray_exe.exists():
        exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent.parent
        tray_exe = exe_dir / "Capture_Push_tray.exe"
        
        # 如果还是没找到，尝试在上一级目录查找（开发环境）
        if not tray_exe.exists():
            parent_dir = exe_dir.parent if exe_dir.name == 'core' else exe_dir
            tray_exe = parent_dir / "Capture_Push_tray.exe"
    
    # 检查托盘程序是否存在
    if not tray_exe.exists():
        raise FileNotFoundError(f"托盘程序不存在: {tray_exe}")
    
    return str(tray_exe.resolve())


def is_autostart_enabled():
    """
    检查是否已启用自启动
    
    Returns:
        bool: 如果已启用自启动则返回True，否则返回False
    """
    try:
        # 从HKCU（当前用户）的Run键检查，与安装包设置的位置一致
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            try:
                value, reg_type = winreg.QueryValueEx(key, "Capture_Push_Tray")
                tray_exe_path = get_tray_exe_path()
                # 检查注册表中的路径是否与实际路径匹配
                return value.strip('"') == tray_exe_path
            except FileNotFoundError:
                # 键值不存在
                return False
    except Exception as e:
        print(f"检查自启动状态时发生错误: {e}")
        return False


def set_autostart(enabled: bool):
    """
    设置托盘程序的开机自启动
    
    Args:
        enabled (bool): True为启用自启动，False为禁用自启动
    """
    try:
        tray_exe_path = get_tray_exe_path()
        
        # 托盘自启动注册表写入前必须校验exe路径存在
        tray_path = Path(tray_exe_path)
        if not tray_path.exists():
            raise FileNotFoundError(f"托盘程序路径不存在: {tray_exe_path}")
        
        # 打开注册表项（当前用户的Run项），与安装包设置的位置一致
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            if enabled:
                # 启用自启动：添加键值
                winreg.SetValueEx(key, "Capture_Push_Tray", 0, winreg.REG_SZ, f'"{tray_exe_path}"')
                print(f"已设置自启动，程序路径: {tray_exe_path}")
            else:
                # 禁用自启动：删除键值
                try:
                    winreg.DeleteValue(key, "Capture_Push_Tray")
                    print("已禁用自启动")
                except FileNotFoundError:
                    # 键值不存在，无需删除
                    print("自启动未启用，无需禁用")
                    
    except PermissionError:
        raise PermissionError("没有权限修改注册表")
    except Exception as e:
        raise Exception(f"设置自启动时发生错误: {e}")


def set_autostart_system_wide(enabled: bool):
    """
    设置系统范围内的自启动（所有用户）
    注意：这通常需要管理员权限
    
    Args:
        enabled (bool): True为启用自启动，False为禁用自启动
    """
    try:
        tray_exe_path = get_tray_exe_path()
        
        # 托盘自启动注册表写入前必须校验exe路径存在
        tray_path = Path(tray_exe_path)
        if not tray_path.exists():
            raise FileNotFoundError(f"托盘程序路径不存在: {tray_exe_path}")
        
        # 打开注册表项（所有用户的Run项）
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        # 使用适当的访问标志，包括64位视图访问
        access_flags = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        # 如果是64位系统，可能需要同时设置32位和64位视图
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, access_flags) as key:
                if enabled:
                    winreg.SetValueEx(key, "Capture_Push_Tray", 0, winreg.REG_SZ, f'"{tray_exe_path}"')
                    print(f"已设置系统级自启动，程序路径: {tray_exe_path}")
                else:
                    try:
                        winreg.DeleteValue(key, "Capture_Push_Tray")
                        print("已禁用系统级自启动")
                    except FileNotFoundError:
                        print("系统级自启动未启用，无需禁用")
        except PermissionError:
            raise PermissionError("没有权限修改系统注册表")
    except Exception as e:
        raise Exception(f"设置系统级自启动时发生错误: {e}")


if __name__ == "__main__":
    # 测试代码
    print("托盘程序路径:", get_tray_exe_path())
    print("当前自启动状态:", is_autostart_enabled())
    
    # 示例：切换自启动状态
    # current_status = is_autostart_enabled()
    # set_autostart(not current_status)
    # print("切换后自启动状态:", is_autostart_enabled())