# -*- coding: utf-8 -*-
"""
学校插件模板
这是一个示例插件，展示了插件的基本结构
"""

SCHOOL_NAME = "示例学校12345"  # 学校名称
PLUGIN_VERSION = "1.0.0"      # 插件版本

def get_course_grades(session, params):
    """
    获取成绩信息
    :param session: 登录后的会话对象
    :param params: 额外参数
    :return: 成绩数据或错误信息
    """
    # 实现获取成绩的具体逻辑
    pass

def get_course_schedule(session, week_offset=0):
    """
    获取课表信息
    :param session: 登录后的会话对象
    :param week_offset: 周偏移量，0表示本周，正数表示未来周次，负数表示过去周次
    :return: 课表数据或错误信息
    """
    # 实现获取课表的具体逻辑
    pass