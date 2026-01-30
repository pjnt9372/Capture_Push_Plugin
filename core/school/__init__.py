# -*- coding: utf-8 -*-
import importlib
import pkgutil
import os
from core.plugins.school_plugin_manager import get_plugin_manager

# 使用延迟加载的插件管理器
plugin_manager = get_plugin_manager()
from core.log import init_logger

logger = init_logger("SchoolModule")


# 学校模块映射表，用于注册新院校
SCHOOL_MODULES = {
    "12345": "core.school.12345",  # 示例：占位符院校（默认）
}


def get_available_schools():
    """获取所有可用的院校列表"""
    schools = {}
    
    # 从配置文件获取插件设置
    from core.config_manager import load_config
    config = load_config()
    if config.has_section('plugins'):
        auto_check_update = config.get('plugins', {}).get('auto_check_update', False)
    else:
        auto_check_update = False
    
    # 如果启用了自动检查更新，则检查插件更新
    if auto_check_update:
        logger.info("自动检查插件更新已启用")
        # 这里可以添加自动检查插件更新的逻辑，比如遍历所有插件并检查更新
    
    # 从插件管理器获取插件院校
    plugin_schools = plugin_manager.get_available_plugins()
    schools.update(plugin_schools)
    
    # 遍历当前包下的子包（传统方式，作为后备）
    package_path = os.path.dirname(__file__)
    for _, name, is_pkg in pkgutil.iter_modules([package_path]):
        if is_pkg and name not in schools:  # 避免重复
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
    # 首先尝试从插件管理器加载
    plugin_module = plugin_manager.load_plugin(school_code)
    if plugin_module:
        return plugin_module
    
    # 如果插件管理器没有找到，则尝试从映射表中获取
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