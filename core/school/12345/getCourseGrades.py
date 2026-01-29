def fetch_grades(username, password, force_update=False):
    """
    获取成绩数据
    Args:
        username: 用户名
        password: 密码
        force_update: 是否强制更新
    
    Returns:
        list: 成绩数据列表，每项为包含课程信息的字典
    """
    # 登录逻辑...
    session = login(username, password)
    if not session:
        return None
    
    # 获取成绩页面
    grades_html = get_grade_html(session, force_update)
    if not grades_html:
        return None
    
    # 解析成绩
    return parse_grades(grades_html)

def parse_grades(html):
    """
    解析成绩HTML
    Args:
        html: 包含成绩信息的HTML内容
    
    Returns:
        list: 解析后的成绩数据列表
    """
    # 使用BeautifulSoup或其他工具解析HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    grades = []
    # 解析逻辑...
    # 每个成绩项应包含以下字段：
    grade_item = {
        "学期": "2023-2024-1",
        "课程名称": "高等数学",
        "成绩": "95",
        "学分": "4",
        "课程属性": "必修",
        "课程编号": "MATH101"
    }
    grades.append(grade_item)
    
    return grades