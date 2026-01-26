# -*- coding: utf-8 -*-
import os
import json
import argparse
import datetime
import configparser
import sys
from pathlib import Path

# 添加项目根目录到 sys.path（确保能找到 core 模块）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.push import send_grade_mail, send_schedule_mail, send_today_schedule_mail, send_full_schedule_mail
from core.school import get_school_module
from core.config_manager import load_config

# 导入统一配置路径管理（AppData 目录）
from core.log import get_config_path, get_log_file_path, init_logger, pack_logs

# 初始化日志
logger = init_logger('go')
logger.info("go.py 启动")
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"sys.path: {sys.path[:3]}...")

# 使用统一的配置路径管理（AppData 目录，如果失败直接崩溃）
CONFIG_FILE = str(get_config_path())
logger.info(f"CONFIG_FILE: {CONFIG_FILE}")

# 获取 AppData 目录（用于存放 state 文件）
APPDATA_DIR = get_log_file_path('go').parent
STATE_DIR = APPDATA_DIR / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

GRADE_STATE_FILE = STATE_DIR / "last_grades.json"
SCHEDULE_STATE_FILE = STATE_DIR / "last_schedule_day.txt"
MANUAL_SCHEDULE_FILE = APPDATA_DIR / "manual_schedule.json"


# ---------- 院校相关 ----------
def get_current_school_module():
    """根据配置获取当前院校模块"""
    cfg = load_config()
    school_code = cfg.get("account", "school_code", fallback="10546")
    module = get_school_module(school_code)
    if not module:
        logger.error(f"找不到院校模块: {school_code}，回退到默认 10546")
        module = get_school_module("10546")
    return module


# ---------- 成绩相关 ----------
def load_last_grades():
    if not GRADE_STATE_FILE.exists():
        return {}
    with open(GRADE_STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_last_grades(grades_dict):
    with open(GRADE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(grades_dict, f, ensure_ascii=False, indent=2)


def diff_grades(old, new):
    changed = {}
    for course, score in new.items():
        if course not in old:
            changed[course] = f"新成绩：{score}"
        elif old[course] != score:
            changed[course] = f"{old[course]} → {score}"
    return changed


def fetch_and_push_grades(push=False, force_update=False, push_all=False):
    """获取并推送成绩
    
    Args:
        push: 是否推送成绩到邮箱
        force_update: 是否强制从网络更新（忽略循环检测）
        push_all: 是否推送所有成绩（忽略变化检测）
    """
    logger.info(f"fetch_and_push_grades 被调用: push={push}, force_update={force_update}, push_all={push_all}")
    try:
        cfg = load_config()
        username = cfg.get("account", "username")
        password = cfg.get("account", "password")
        logger.info(f"账号配置: username={username[:2]}***")

        school_mod = get_current_school_module()
        grades = school_mod.fetch_grades(username, password, force_update)
        if not grades:
            logger.error("成绩获取失败")
            print("❌ 成绩获取失败")
            return

        logger.info(f"获取到 {len(grades)} 条成绩记录")
        new_map = {g["课程名称"]: g["成绩"] for g in grades}
        old_map = load_last_grades()
        changed = diff_grades(old_map, new_map)

        # 如果要求推送
        if push:
            logger.debug(f"进入推送逻辑: push_all={push_all}, 成绩数量={len(new_map)}, 变化数量={len(changed)}")
            if push_all:
                # 推送所有成绩
                logger.info(f"推送所有成绩（{len(new_map)} 条）")
                logger.debug(f"推送的所有成绩: {list(new_map.items())}")
                all_grades = {course: f"成绩：{score}" for course, score in new_map.items()}
                logger.debug(f"格式化后的成绩: {all_grades}")
                send_grade_mail(all_grades)
                print(f"✅ 已推送所有成绩（{len(new_map)} 条）")
            elif changed:
                # 只推送变化的成绩
                logger.info(f"推送 {len(changed)} 条变化的成绩")
                logger.debug(f"变化的成绩: {changed}")
                send_grade_mail(changed)
                print(f"✅ 已推送 {len(changed)} 条变化的成绩")
            else:
                logger.info("成绩无变化，不推送")
                print("ℹ️ 成绩无变化，未推送")

        save_last_grades(new_map)

        # 如果不是推送模式，显示变化情况
        if not push:
            if changed:
                logger.info("成绩有更新")
                print("✅ 成绩有更新")
            else:
                logger.info("成绩无变化")
                print("ℹ️ 成绩无变化")
    except Exception as e:
        logger.error(f"fetch_and_push_grades 异常: {e}", exc_info=True)
        raise


# ---------- 课表相关 ----------
def load_last_schedule_day():
    if not SCHEDULE_STATE_FILE.exists():
        return None
    with open(SCHEDULE_STATE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def save_last_schedule_day(day_str):
    with open(SCHEDULE_STATE_FILE, "w", encoding="utf-8") as f:
        f.write(day_str)


def calc_week_and_weekday(first_monday):
    today = datetime.date.today()
    delta = (today - first_monday).days
    logger.debug(f"日期计算: today={today}, first_monday={first_monday}, delta={delta}")
    if delta < 0:
        return None, None
    week = delta // 7 + 1
    weekday = delta % 7 + 1  # 周一=1
    return week, weekday


def load_manual_schedule():
    """加载手动修改的课表数据"""
    if not MANUAL_SCHEDULE_FILE.exists():
        return {}
    try:
        with open(MANUAL_SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def fetch_and_push_today_schedule(force_update=False):
    """获取并推送今日课表"""
    logger.info(f"fetch_and_push_today_schedule 被调用: force_update={force_update}")
    try:
        cfg = load_config()
        username = cfg.get("account", "username")
        password = cfg.get("account", "password")
        first_monday_str = cfg.get("semester", "first_monday", fallback="").strip()
        if not first_monday_str:
            logger.warning("配置文件中未设置第一周周一 (first_monday)")
            return
            
        first_monday = datetime.datetime.strptime(
            first_monday_str, "%Y-%m-%d"
        ).date()

        today = datetime.date.today()
        week, weekday = calc_week_and_weekday(first_monday)
        
        if weekday is None:
            logger.warning("未到开学日期，跳过推送")
            return

        logger.info(f"推送今日课表: 第{week}周 周{weekday}")
        
        # 检查是否已推送（按日期记录）
        state_file = STATE_DIR / "last_push_today.txt"
        today_str = today.strftime("%Y-%m-%d")
        if not force_update and state_file.exists():
            with open(state_file, "r") as f:
                if f.read().strip() == today_str:
                    logger.info("今日课表已推送，跳过")
                    return

        school_mod = get_current_school_module()
        schedule = school_mod.fetch_course_schedule(username, password, force_update)
        if not schedule:
            logger.error("课表获取失败")
            return

        # 合并手动修改的课表
        manual_data = load_manual_schedule()
        # 记录被手动覆盖的格点 (weekday, period)
        manual_occupied = set()
        manual_courses = []
        
        for key, data in manual_data.items():
            col, start = map(int, key.split("-"))
            name = data.get("课程名称", "")
            if not name: continue
            
            row_span = data.get("row_span", 1)
            # 手动课程默认出现在所有周，或者你可以根据需要添加周次逻辑
            manual_courses.append({
                "星期": col,
                "开始小节": start,
                "结束小节": start + row_span - 1,
                "课程名称": name,
                "教师": data.get("教师", ""),
                "教室": data.get("教室", ""),
                "周次列表": ["全学期"]
            })
            for p in range(start, start + row_span):
                manual_occupied.add((col, p))

        # 过滤并合并
        filtered = []
        # 先加手动的（如果符合星期）
        for mc in manual_courses:
            if mc["星期"] == weekday:
                filtered.append(mc)
        
        # 再加解析的（如果不冲突）
        for c in schedule:
            if c["星期"] == weekday and (week in c["周次列表"] or "全学期" in c["周次列表"]):
                # 检查是否被手动覆盖
                is_covered = False
                for p in range(c["开始小节"], c["结束小节"] + 1):
                    if (weekday, p) in manual_occupied:
                        is_covered = True
                        break
                if not is_covered:
                    filtered.append(c)

        send_today_schedule_mail(filtered, week, weekday)
        
        with open(state_file, "w") as f:
            f.write(today_str)
        logger.info("今日课表推送完成")
    except Exception as e:
        logger.error(f"fetch_and_push_today_schedule 异常: {e}", exc_info=True)

def fetch_and_push_tomorrow_schedule(force_update=False):
    """获取并推送明日课表"""
    logger.info(f"fetch_and_push_tomorrow_schedule 被调用: force_update={force_update}")
    try:
        cfg = load_config()
        username = cfg.get("account", "username")
        password = cfg.get("account", "password")
        first_monday_str = cfg.get("semester", "first_monday", fallback="").strip()
        if not first_monday_str:
            logger.warning("配置文件中未设置第一周周一 (first_monday)")
            return
            
        first_monday = datetime.datetime.strptime(
            first_monday_str, "%Y-%m-%d"
        ).date()

        today = datetime.date.today()
        # 获取今天的周次和星期
        week, weekday = calc_week_and_weekday(first_monday)
        
        if weekday is None:
            logger.warning("未到开学日期，跳过推送")
            return

        # 计算明天的星期（如果是周日，则明天是周一）
        tomorrow_weekday = weekday + 1
        if tomorrow_weekday > 7:  # 如果明天是下一周的周一
            tomorrow_weekday = 1
            # 如果今天是周日，则推送下周一的课表
            if weekday == 7:  
                target_week = week + 1
            else:  # 如果今天是周六，明天是周日，仍属于本周
                target_week = week
        else:  # 明天仍在本周
            target_week = week

        logger.info(f"推送明日课表: 第{target_week}周 周{tomorrow_weekday}")
        
        # 检查是否已推送
        state_file = STATE_DIR / "last_push_tomorrow.txt"
        # 使用目标日期而非实际明天日期，确保同一天多次运行不会重复推送
        target_date_str = (first_monday + datetime.timedelta(weeks=target_week-1, days=tomorrow_weekday-1)).strftime("%Y-%m-%d")
        if not force_update and state_file.exists():
            with open(state_file, "r") as f:
                if f.read().strip() == target_date_str:
                    logger.info("明日课表已推送，跳过")
                    return

        school_mod = get_current_school_module()
        schedule = school_mod.fetch_course_schedule(username, password, force_update)
        if not schedule:
            logger.error("课表获取失败")
            return

        # 合并手动修改的课表
        manual_data = load_manual_schedule()
        manual_occupied = set()
        manual_courses = []
        
        for key, data in manual_data.items():
            col, start = map(int, key.split("-"))
            name = data.get("课程名称", "")
            if not name: continue
            row_span = data.get("row_span", 1)
            manual_courses.append({
                "星期": col,
                "开始小节": start,
                "结束小节": start + row_span - 1,
                "课程名称": name,
                "教师": data.get("教师", ""),
                "教室": data.get("教室", ""),
                "周次列表": ["全学期"]
            })
            for p in range(start, start + row_span):
                manual_occupied.add((col, p))

        # 过滤并合并
        filtered = []
        for mc in manual_courses:
            if mc["星期"] == tomorrow_weekday and (target_week in mc["周次列表"] or "全学期" in mc["周次列表"]):
                filtered.append(mc)
        
        for c in schedule:
            if c["星期"] == tomorrow_weekday and (target_week in c["周次列表"] or "全学期" in c["周次列表"]):
                is_covered = False
                for p in range(c["开始小节"], c["结束小节"] + 1):
                    if (tomorrow_weekday, p) in manual_occupied:
                        is_covered = True
                        break
                if not is_covered:
                    filtered.append(c)

        send_schedule_mail(filtered, target_week, tomorrow_weekday)
        
        with open(state_file, "w") as f:
            f.write(target_date_str)
        logger.info("明日课表推送完成")
    except Exception as e:
        logger.error(f"fetch_and_push_tomorrow_schedule 异常: {e}", exc_info=True)

def fetch_and_push_next_week_schedule(force_update=False):
    """获取并推送下周全周课表"""
    logger.info(f"fetch_and_push_next_week_schedule 被调用: force_update={force_update}")
    try:
        cfg = load_config()
        username = cfg.get("account", "username")
        password = cfg.get("account", "password")
        first_monday_str = cfg.get("semester", "first_monday", fallback="").strip()
        if not first_monday_str:
            logger.warning("配置文件中未设置第一周周一 (first_monday)")
            return
            
        first_monday = datetime.datetime.strptime(
            first_monday_str, "%Y-%m-%d"
        ).date()

        # 计算下周周一的周次
        next_monday = datetime.date.today() + datetime.timedelta(days=(7 - datetime.date.today().weekday()))
        delta = (next_monday - first_monday).days
        if delta < 0:
            logger.warning("下周未到开学日期，跳过推送")
            return
        next_week = delta // 7 + 1

        logger.info(f"推送下周课表: 第{next_week}周")
        
        # 检查是否已推送
        state_file = STATE_DIR / "last_push_next_week.txt"
        week_str = f"week_{next_week}"
        if not force_update and state_file.exists():
            with open(state_file, "r") as f:
                if f.read().strip() == week_str:
                    logger.info(f"第 {next_week} 周课表已推送，跳过")
                    return

        school_mod = get_current_school_module()
        schedule = school_mod.fetch_course_schedule(username, password, force_update)
        if not schedule:
            logger.error("课表获取失败")
            return

        # 加载手动修改
        manual_data = load_manual_schedule()
        manual_courses = []
        manual_occupied = set() # (weekday, period)
        
        for key, data in manual_data.items():
            col, start = map(int, key.split("-"))
            name = data.get("课程名称", "")
            if not name: continue
            row_span = data.get("row_span", 1)
            mc = {
                "星期": col,
                "开始小节": start,
                "结束小节": start + row_span - 1,
                "课程名称": name,
                "教师": data.get("教师", ""),
                "教室": data.get("教室", ""),
                "周次列表": ["全学期"]
            }
            manual_courses.append(mc)
            for p in range(start, start + row_span):
                manual_occupied.add((col, p))

        # 按天分组
        full_schedule = []
        for d in range(1, 8):
            day_list = []
            # 手动课程
            for mc in manual_courses:
                if mc["星期"] == d:
                    day_list.append(mc)
            
            # 解析课程
            for c in schedule:
                if c["星期"] == d and (next_week in c["周次列表"] or "全学期" in c["周次列表"]):
                    is_covered = False
                    for p in range(c["开始小节"], c["结束小节"] + 1):
                        if (d, p) in manual_occupied:
                            is_covered = True
                            break
                    if not is_covered:
                        day_list.append(c)
            
            if day_list:
                # 排序
                day_list.sort(key=lambda x: x["开始小节"])
                full_schedule.append(day_list)

        if full_schedule:
            send_full_schedule_mail(full_schedule, next_week)
            with open(state_file, "w") as f:
                f.write(week_str)
            logger.info("下周课表推送完成")
        else:
            logger.info("下周无课，不推送")

    except Exception as e:
        logger.error(f"fetch_and_push_next_week_schedule 异常: {e}", exc_info=True)


def fetch_and_push_full_semester_schedule(force_update=False):
    """获取并推送完整学期课表"""
    logger.info(f"fetch_and_push_full_semester_schedule 被调用: force_update={force_update}")
    try:
        cfg = load_config()
        username = cfg.get("account", "username")
        password = cfg.get("account", "password")
        first_monday_str = cfg.get("semester", "first_monday", fallback="").strip()
        if not first_monday_str:
            logger.warning("配置文件中未设置第一周周一 (first_monday)")
            return
            
        first_monday = datetime.datetime.strptime(
            first_monday_str, "%Y-%m-%d"
        ).date()

        # 计算当前学期的最大周数
        today = datetime.date.today()
        max_weeks = 25  # 假设最多25周
        
        logger.info(f"推送完整学期课表")
        
        school_mod = get_current_school_module()
        schedule = school_mod.fetch_course_schedule(username, password, force_update)
        if not schedule:
            logger.error("课表获取失败")
            return

        # 加载手动修改
        manual_data = load_manual_schedule()
        manual_courses = []
        manual_occupied = set() # (weekday, period)
        
        for key, data in manual_data.items():
            col, start = map(int, key.split("-"))
            name = data.get("课程名称", "")
            if not name: continue
            row_span = data.get("row_span", 1)
            mc = {
                "星期": col,
                "开始小节": start,
                "结束小节": start + row_span - 1,
                "课程名称": name,
                "教师": data.get("教师", ""),
                "教室": data.get("教室", ""),
                "周次列表": ["全学期"]
            }
            manual_courses.append(mc)
            for p in range(start, start + row_span):
                manual_occupied.add((col, p))

        # 按周和天分组
        semester_schedule = {}
        for week in range(1, max_weeks + 1):
            # 检查这一周是否在学期范围内
            week_start = first_monday + datetime.timedelta(weeks=week-1)
            if week_start < first_monday:
                continue
            
            # 检查这一周是否在学期范围内（不超过当前日期之后很远）
            week_end = week_start + datetime.timedelta(days=6)
            if today.year == week_start.year and today.month == 12 and week_start.month == 1:
                # 跨年处理，如果是12月但周开始是1月，说明跨年了
                pass
            elif week_start > today + datetime.timedelta(weeks=4):  # 超出未来4周则跳过
                continue

            semester_schedule[week] = []
            for d in range(1, 8):
                day_list = []
                # 手动课程
                for mc in manual_courses:
                    if mc["星期"] == d:
                        day_list.append(mc)
                
                # 解析课程
                for c in schedule:
                    if c["星期"] == d and (str(week) in [str(w) for w in c["周次列表"]] or "全学期" in c["周次列表"]):
                        is_covered = False
                        for p in range(c["开始小节"], c["结束小节"] + 1):
                            if (d, p) in manual_occupied:
                                is_covered = True
                                break
                        if not is_covered:
                            day_list.append(c)
                
                if day_list:
                    # 排序
                    day_list.sort(key=lambda x: x["开始小节"])
                    semester_schedule[week].append(day_list)

        # 过滤掉空周
        semester_schedule = {week: days for week, days in semester_schedule.items() if days}

        if semester_schedule:
            # 将学期课表转换为适合推送的格式
            formatted_schedule = []
            week_counts = []
            for week_num in sorted(semester_schedule.keys()):
                week_days = semester_schedule[week_num]
                # 将每周的天数课程列表展开成单个天数课程列表
                for day_list in week_days:
                    formatted_schedule.append(day_list)
                week_counts.append(week_num)
            
            if formatted_schedule:
                send_full_schedule_mail(formatted_schedule, len(week_counts))
                logger.info(f"完整学期课表推送完成，共{len(week_counts)}周")
            else:
                logger.info("完整学期无课，不推送")
        else:
            logger.info("完整学期无课，不推送")

    except Exception as e:
        logger.error(f"fetch_and_push_full_semester_schedule 异常: {e}", exc_info=True)

# ---------- CLI ----------
def main():
    logger.info(f"main() 被调用，参数: {sys.argv}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-grade", action="store_true", help="获取成绩（不推送）")
    parser.add_argument("--push-grade", action="store_true", help="推送变化的成绩")
    parser.add_argument("--push-all-grades", action="store_true", help="推送所有成绩（无论是否有变化）")
    parser.add_argument("--fetch-schedule", action="store_true", help="获取课表（不推送）")
    parser.add_argument("--push-schedule", action="store_true", help="推送课表 (兼容旧参数)")
    parser.add_argument("--push-today", action="store_true", help="推送今日课表")
    parser.add_argument("--push-tomorrow", action="store_true", help="推送明日课表")
    parser.add_argument("--push-next-week", action="store_true", help="推送下周全周课表")
    parser.add_argument("--push-full-schedule", action="store_true", help="推送完整学期课表")
    parser.add_argument("--pack-logs", action="store_true", help="打包日志文件用于日志上报")
    parser.add_argument("--check-update", action="store_true", help="检查软件更新")
    parser.add_argument("--force", action="store_true", help="强制从网络更新,忽略循环检测")
    args = parser.parse_args()
    
    logger.info(f"解析后的参数: fetch_grade={args.fetch_grade}, push_grade={args.push_grade}, "
                f"push_all_grades={args.push_all_grades}, "
                f"fetch_schedule={args.fetch_schedule}, push_schedule={args.push_schedule}, force={args.force}")

    if args.fetch_grade:
        logger.info("执行: fetch_and_push_grades(push=False)")
        fetch_and_push_grades(push=False, force_update=args.force)
    if args.push_grade:
        logger.info("执行: fetch_and_push_grades(push=True, push_all=False)")
        fetch_and_push_grades(push=True, force_update=args.force, push_all=False)
    if args.push_all_grades:
        logger.info("执行: fetch_and_push_grades(push=True, push_all=True)")
        fetch_and_push_grades(push=True, force_update=args.force, push_all=True)
    if args.fetch_schedule:
        logger.info("执行: fetch_course_schedule")
        cfg = load_config()
        school_mod = get_current_school_module()
        school_mod.fetch_course_schedule(cfg.get("account", "username"), cfg.get("account", "password"), force_update=args.force)
    if args.push_schedule:
        logger.info("执行: fetch_and_push_today_schedule(兼容模式)")
        fetch_and_push_today_schedule(force_update=args.force)
    if args.push_today:
        logger.info("执行: fetch_and_push_today_schedule")
        fetch_and_push_today_schedule(force_update=args.force)
    if args.push_tomorrow:
        logger.info("执行: fetch_and_push_tomorrow_schedule")
        fetch_and_push_tomorrow_schedule(force_update=args.force)
    if args.push_next_week:
        logger.info("执行: fetch_and_push_next_week_schedule")
        fetch_and_push_next_week_schedule(force_update=args.force)
    if args.push_full_schedule:
        logger.info("执行: fetch_and_push_full_semester_schedule")
        fetch_and_push_full_semester_schedule(force_update=args.force)
    if args.pack_logs:
        logger.info("执行: pack_logs")
        report_path = pack_logs()
        if report_path:
            print(f"✅ 日志报告已生成: {report_path}")
        else:
            print("❌ 日志报告生成失败")
    if args.check_update:
        logger.info("执行: check_update")
        from core.updater import Updater
        updater = Updater()
        result = updater.check_update()
        if result:
            version, data = result
            print(f"发现新版本: {version}")
            print(f"当前版本: {updater.current_version}")
            # 返回更新信息给调用者（GUI）
            import json
            print("UPDATE_INFO:" + json.dumps({"version": version, "has_update": True}, ensure_ascii=False))
        else:
            print("当前已是最新版本")
            import json
            print("UPDATE_INFO:" + json.dumps({"has_update": False}, ensure_ascii=False))
    
    logger.info("main() 执行完成")


if __name__ == "__main__":
    main()
