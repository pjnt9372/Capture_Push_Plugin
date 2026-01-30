# -*- coding: utf-8 -*-
"""
衡阳师范学院插件模块
"""

from getCourseGrades import fetch_grades, parse_grades
from getCourseSchedule import fetch_course_schedule, parse_schedule

SCHOOL_NAME = "衡阳师范学院"
SCHOOL_CODE = "10546"
PLUGIN_VERSION = "1.0.0"

__all__ = ['fetch_grades', 'parse_grades', 'fetch_course_schedule', 'parse_schedule', 
           'SCHOOL_NAME', 'SCHOOL_CODE', 'PLUGIN_VERSION']