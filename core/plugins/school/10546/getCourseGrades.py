# -*- coding: utf-8 -*-
"""
成绩获取模块 - 衡阳师范学院
用于从教务系统获取学生成绩信息
"""

def fetch_grades(username, password, force_update=False):
    """
    获取学生成绩
    
    Args:
        username: 用户名
        password: 密码
        force_update: 是否强制更新
    
    Returns:
        成绩数据字典
    """
    # 这里是示例实现，实际插件应该实现真实的获取逻辑
    print(f"模拟获取 {username} 的成绩信息...")
    
    # 模拟成绩数据
    grades_data = {
        "student_info": {
            "name": "张三",
            "student_id": username,
            "college": "计算机科学与工程学院",
            "major": "计算机科学与技术",
            "grade": "2021级"
        },
        "grades": [
            {
                "course_name": "高等数学",
                "credit": 4.0,
                "score": "85",
                "grade_point": 3.5,
                "semester": "2021-2022-1",
                "exam_type": "考试"
            },
            {
                "course_name": "大学英语",
                "credit": 3.0,
                "score": "78",
                "grade_point": 3.0,
                "semester": "2021-2022-1",
                "exam_type": "考试"
            },
            {
                "course_name": "程序设计基础",
                "credit": 3.0,
                "score": "92",
                "grade_point": 4.0,
                "semester": "2021-2022-1",
                "exam_type": "考试"
            }
        ],
        "gpa": 3.5
    }
    
    return grades_data


def parse_grades(raw_data):
    """
    解析原始成绩数据
    
    Args:
        raw_data: 原始数据
    
    Returns:
        解析后的成绩数据
    """
    # 在真实插件中，这里会解析从教务系统获取的原始HTML/JSON数据
    # 这里只是返回模拟的数据
    return raw_data