def fetch_course_schedule(username, password, force_update=False):
    """
    获取课表数据
    Args:
        username: 用户名
        password: 密码
        force_update: 是否强制更新
    
    Returns:
        list: 课表数据列表，每项为包含课程信息的字典
    """
    # 登录逻辑...
    session = login(username, password)
    if not session:
        return None
    
    # 获取课表页面
    schedule_html = get_schedule_html(session, force_update)
    if not schedule_html:
        return None
    
    # 解析课表
    return parse_schedule(schedule_html)

def parse_schedule(html):
    """
    解析课表HTML
    Args:
        html: 包含课表信息的HTML内容
    
    Returns:
        list: 解析后的课表数据列表
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    schedule = []
    # 解析逻辑...
    # 每个课程项应包含以下字段：
    course_item = {
        "星期": 1,  # 1-7，分别代表周一到周日
        "开始小节": 1,  # 第几节课开始
        "结束小节": 2,  # 第几节课结束
        "课程名称": "高等数学",
        "教室": "教学楼101",
        "教师": "张老师",
        "周次列表": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]  # 1-20周，或 ["全学期"]
    }
    schedule.append(course_item)
    
    return schedule