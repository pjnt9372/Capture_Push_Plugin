# -*- coding: utf-8 -*-
"""
课表获取模块 - 衡阳师范学院
用于从教务系统获取学生课表信息
"""

def fetch_course_schedule(username, password, force_update=False):
    """
    获取学生课表
    
    Args:
        username: 用户名
        password: 密码
        force_update: 是否强制更新
    
    Returns:
        课表数据字典
    """
    # 这里是示例实现，实际插件应该实现真实的获取逻辑
    print(f"模拟获取 {username} 的课表信息...")
    
    # 模拟课表数据
    schedule_data = {
        "student_info": {
            "name": "张三",
            "student_id": username,
            "college": "计算机科学与工程学院",
            "major": "计算机科学与技术",
            "grade": "2021级"
        },
        "schedule": [
            {
                "course_name": "高等数学",
                "teacher": "李教授",
                "classroom": "教学楼A101",
                "week_day": 1,  # 星期一
                "period_start": 1,
                "period_end": 2,
                "weeks": "1-16周",
                "semester": "2021-2022-1"
            },
            {
                "course_name": "大学英语",
                "teacher": "王老师",
                "classroom": "教学楼B205",
                "week_day": 1,  # 星期一
                "period_start": 3,
                "period_end": 4,
                "weeks": "1-16周",
                "semester": "2021-2022-1"
            },
            {
                "course_name": "程序设计基础",
                "teacher": "赵老师",
                "classroom": "实验楼C301",
                "week_day": 2,  # 星期二
                "period_start": 1,
                "period_end": 3,
                "weeks": "1-16周",
                "semester": "2021-2022-1"
            }
        ]
    }
    
    return schedule_data


def parse_schedule(raw_data):
    """
    解析原始课表数据
    
    Args:
        raw_data: 原始数据
    
    Returns:
        解析后的课表数据
    """
    # 在真实插件中，这里会解析从教务系统获取的原始HTML/JSON数据
    # 这里只是返回模拟的数据
    return raw_data