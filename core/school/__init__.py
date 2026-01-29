# -*- coding: utf-8 -*-
import importlib
import pkgutil
import os


# 学校模块映射表，用于注册新院校
SCHOOL_MODULES = {
    "12345": "core.school.12345",  # 示例：占位符院校（默认）
}


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
    # 首先尝试从映射表中获取
    if school_code in SCHOOL_MODULES:
        try:
            module_path = SCHOOL_MODULES[school_code]
            return importlib.import_module(module_path)
        except Exception:
            pass
    # 如果映射表中没有，则尝试动态导入
    try:
        return importlib.import_module(f".{school_code}", __package__)
    except Exception:
        return None