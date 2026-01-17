# -*- coding: utf-8 -*-
import importlib
import pkgutil
import os

def get_available_schools():
    """获取所有可用的院校列表"""
    schools = {}
    # 遍历当前包下的子包
    package_path = os.path.dirname(__file__)
    for _, name, is_pkg in pkgutil.iter_modules([package_path]):
        if is_pkg:
            try:
                # 动态导入子包
                module = importlib.import_module(f".{name}", __package__)
                school_name = getattr(module, "SCHOOL_NAME", name)
                schools[name] = school_name
            except Exception:
                continue
    return schools

def get_school_module(school_code):
    """获取指定院校的模块"""
    try:
        return importlib.import_module(f".{school_code}", __package__)
    except Exception:
        return None
