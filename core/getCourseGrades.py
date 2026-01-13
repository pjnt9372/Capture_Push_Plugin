# -*- coding: utf-8 -*-
import requests
import base64
from bs4 import BeautifulSoup
import socket
import configparser
import os
import json
import time

# 导入统一日志模块
from log import init_logger, get_config_path

# 初始化日志
logger = init_logger('getCourseGrades')

# 获取配置文件路径
CONFIG_PATH = str(get_config_path())

# ===== 2. 读取运行模式 =====
def get_run_mode():
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_PATH, encoding='utf-8')
        mode = config.get('run_model', 'model', fallback='BUILD').strip().upper()
        if mode not in ('DEV', 'BUILD'):
            logger.warning(f"未知运行模式 '{mode}'，默认使用 BUILD")
            mode = 'BUILD'
        return mode
    except Exception as e:
        logger.warning(f"读取 run_model 失败，使用默认模式 BUILD: {e}")
        return 'BUILD'

RUN_MODE = get_run_mode()
logger.info(f"当前运行模式: {RUN_MODE}")

# ===== 3. 常量定义 =====
BASE_URL = "https://hysfjw.hynu.edu.cn/jsxsd/"
LOGIN_URL = BASE_URL + "xk/LoginToXk"
GRADE_URL = BASE_URL + "kscj/cjcx_list"

class IPv4Adapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        import urllib3.util.connection as urllib3_conn
        urllib3_conn.allowed_gai_family = lambda: socket.AF_INET
        return super().init_poolmanager(*args, **kwargs)

# ===== 4. 登录函数 =====
def login(username, password):
    hostname = "hysfjw.hynu.edu.cn"
    try:
        ipv4_addr = socket.gethostbyname(hostname)
        logger.info(f"目标服务器 {hostname} 解析到 IPv4 地址: {ipv4_addr}")
    except Exception as e:
        logger.warning(f"解析 {hostname} IPv4 失败: {e}")

    b64_user = base64.b64encode(username.encode("utf-8")).decode("utf-8")
    b64_pwd = base64.b64encode(password.encode("utf-8")).decode("utf-8")
    encoded = f"{b64_user}%%%{b64_pwd}"
    logger.debug(f"生成的 encoded: {encoded}")

    session = requests.Session()
    session.mount('http://', IPv4Adapter())
    session.mount('https://', IPv4Adapter())
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE_URL
    })

    try:
        response = session.post(LOGIN_URL, data={"encoded": encoded}, timeout=10)
        logger.debug(f"登录响应状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"登录请求异常: {e}")
        return None

    if "xsMain_new.htmlx" in response.text or "xsMain.htmlx" in response.text:
        logger.info("登录成功")
        return session
    elif "用户名或密码错误" in response.text:
        logger.error("用户名或密码错误")
    elif "验证码" in response.text:
        logger.warning("检测到验证码，脚本无法处理")
    else:
        logger.error("登录失败，未知原因")
        with open("login_failed_grade.html", "w", encoding="utf-8") as f:
            f.write(response.text)
    return None

# ===== 5. 循环检测配置读取 =====
def get_loop_config():
    """读取循环检测配置"""
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_PATH, encoding='utf-8')
        enabled = config.getboolean('loop_getCourseGrades', 'enabled', fallback=False)
        interval = config.getint('loop_getCourseGrades', 'time', fallback=3600)
        logger.info(f"循环检测配置: enabled={enabled}, interval={interval}秒")
        return enabled, interval
    except Exception as e:
        logger.warning(f"读取循环检测配置失败: {e}，使用默认值")
        return False, 3600

# ===== 6. 检查是否需要更新 =====
def should_update_grades():
    """检查是否需要从网络更新成绩"""
    enabled, interval = get_loop_config()
    
    # 如果循环检测未启用，直接返回True（总是更新）
    if not enabled:
        logger.info("循环检测未启用，将从网络获取最新成绩")
        return True
    
    # 检查本地缓存文件是否存在
    cache_file = "grade.html"
    timestamp_file = "grade_timestamp.txt"
    
    if not os.path.exists(cache_file):
        logger.info("本地成绩缓存不存在，需要从网络获取")
        return True
    
    # 检查时间戳文件
    if not os.path.exists(timestamp_file):
        logger.info("时间戳文件不存在，需要从网络获取")
        return True
    
    try:
        with open(timestamp_file, "r", encoding="utf-8") as f:
            last_update = float(f.read().strip())
        
        current_time = time.time()
        elapsed = current_time - last_update
        
        logger.info(f"距离上次更新已过 {elapsed:.0f} 秒，更新间隔设置为 {interval} 秒")
        
        if elapsed >= interval:
            logger.info("超过更新间隔，需要从网络获取")
            return True
        else:
            logger.info(f"未超过更新间隔，还需 {interval - elapsed:.0f} 秒，使用本地缓存")
            return False
    except Exception as e:
        logger.warning(f"读取时间戳失败: {e}，需要从网络获取")
        return True

# ===== 7. 更新时间戳 =====
def update_timestamp():
    """更新成绩获取时间戳"""
    timestamp_file = "grade_timestamp.txt"
    try:
        with open(timestamp_file, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
        logger.info("时间戳已更新")
    except Exception as e:
        logger.error(f"更新时间戳失败: {e}")

# ===== 8. 获取成绩 HTML =====
def get_grade_html(session, force_update=False):
    """获取成绩HTML，支持循环检测"""
    if RUN_MODE == 'DEV':
        logger.info("[DEV 模式] 从本地文件 'grade.html' 读取成绩数据")
        try:
            with open("grade.html", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("未找到 grade.html，请先在 BUILD 模式运行生成")
            return None
        except Exception as e:
            logger.error(f"读取 grade.html 失败: {e}")
            return None
    
    # 检查是否需要更新
    if not force_update and not should_update_grades():
        logger.info("使用本地缓存的成绩数据")
        try:
            with open("grade.html", "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"读取本地缓存失败: {e}，将从网络获取")
    
    # 从网络获取
    logger.info("开始从网络请求成绩页面")
    headers = {"Referer": BASE_URL + "framework/xsMain.jsp"}
    try:
        response = session.get(GRADE_URL, headers=headers, timeout=10)
        logger.debug(f"成绩请求状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"成绩请求异常: {e}")
        return None

    if "N122101QueryResult" in response.text or "kscj" in response.text:
        logger.info("成功获取成绩数据")
        with open("grade.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        update_timestamp()  # 更新时间戳
        return response.text
    else:
        logger.error("未识别到有效成绩内容")
        with open("grade_failed.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        return None

# ===== 9. 解析成绩 =====
def parse_grades(html):
    logger.info("开始解析成绩表格")
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="dataList")
    if not table:
        logger.error("未找到 <table id='dataList'>")
        return []

    rows = table.find_all("tr")[1:]  # 跳过表头
    grades = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        course = {
            "课程名称": cols[2].get_text(strip=True),
            "学分": cols[3].get_text(strip=True),
            "成绩": cols[4].get_text(strip=True),
            "学期": cols[1].get_text(strip=True),
            "课程属性": cols[5].get_text(strip=True) if len(cols) > 5 else "",
        }
        grades.append(course)

    logger.info(f"成功解析 {len(grades)} 门课程成绩")
    # >>>>>>>>>>>>>>>>>> 关键改进：DEBUG 输出解析结果 <<<<<<<<<<<<<<<<<<
    if grades:
        logger.debug("【成绩解析结果】\n" + json.dumps(grades, ensure_ascii=False, indent=2))
    return grades

# ===== 10. 打印成绩 =====
def print_grades(grades):
    if not grades:
        print("❌ 未获取到成绩")
        return

    print("\n" + "="*80)
    print(f"{'学期':<12} {'课程名称':<25} {'学分':<6} {'成绩':<8} {'课程属性'}")
    print("-"*80)
    for g in grades:
        print(f"{g['学期']:<12} {g['课程名称']:<25} {g['学分']:<6} {g['成绩']:<8} {g['课程属性']}")
    print("="*80)

# ===== 11. 主流程 =====
def fetch_grades(username, password, force_update=False):
    """获取成绩数据
    
    Args:
        username: 学号
        password: 密码
        force_update: 是否强制从网络更新（忽略循环检测）
    """
    if RUN_MODE == 'DEV':
        html = get_grade_html(None, force_update)
        return parse_grades(html) if html else None

    session = login(username, password)
    if not session:
        return None

    html = get_grade_html(session, force_update)
    return parse_grades(html) if html else None

# ===== 12. 主程序入口 =====
def main():
    if RUN_MODE == 'DEV':
        print("【开发模式】从 grade.html 读取成绩")
        grades = fetch_grades("", "")
    else:
        username = input("请输入学号: ").strip()
        password = input("请输入密码: ").strip()
        if not username or not password:
            print("❌ 学号或密码不能为空")
            return
        grades = fetch_grades(username, password)

    if grades is not None:
        print_grades(grades)
        print("✅ 成绩解析完成")
    else:
        print("❌ 成绩获取或解析失败")

if __name__ == "__main__":
    main()