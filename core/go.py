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

from core.getCourseGrades import fetch_grades
from core.getCourseSchedule import fetch_course_schedule
from core.push import send_grade_mail, send_schedule_mail

# 导入统一配置路径管理（AppData 目录）
from core.log import get_config_path, get_log_file_path, init_logger

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


# ---------- 配置 ----------
def load_config():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    return cfg


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
    logger.info(f"fetch_and_push_grades 开始: push={push}, force_update={force_update}, push_all={push_all}")
    try:
        cfg = load_config()
        username = cfg.get("account", "username")
        password = cfg.get("account", "password")
        logger.info(f"账号配置: username={username[:2]}***")

        grades = fetch_grades(username, password, force_update)
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
    if delta < 0:
        return None, None
    week = delta // 7 + 1
    weekday = delta % 7 + 1  # 周一=1
    return week, weekday


def fetch_and_push_schedule(push=False, force_update=False):
    """获取并推送课表
    
    Args:
        push: 是否推送课表到邮箱
        force_update: 是否强制从网络更新（忽略循环检测）
    """
    cfg = load_config()
    username = cfg.get("account", "username")
    password = cfg.get("account", "password")

    first_monday = datetime.datetime.strptime(
        cfg.get("semester", "first_monday"), "%Y-%m-%d"
    ).date()

    week, weekday = calc_week_and_weekday(first_monday)
    if weekday is None or weekday == 1:
        print("ℹ️ 今天不推送课表")
        return

    target_weekday = weekday - 1
    today_str = f"week{week}_day{target_weekday}"

    if load_last_schedule_day() == today_str:
        print("ℹ️ 课表已推送，跳过")
        return

    schedule = fetch_course_schedule(username, password, force_update)
    if not schedule:
        print("❌ 课表获取失败")
        return

    filtered = [
        c for c in schedule
        if c["星期"] == target_weekday and
        (week in c["周次列表"] or not c["周次列表"] or c["周次列表"] == ["全学期"])
    ]

    if push and filtered:
        send_schedule_mail(filtered, week, target_weekday)

    save_last_schedule_day(today_str)
    print("✅ 课表推送完成")


# ---------- CLI ----------
def main():
    logger.info(f"main() 被调用，参数: {sys.argv}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-grade", action="store_true", help="获取成绩（不推送）")
    parser.add_argument("--push-grade", action="store_true", help="推送变化的成绩")
    parser.add_argument("--push-all-grades", action="store_true", help="推送所有成绩（无论是否有变化）")
    parser.add_argument("--fetch-schedule", action="store_true", help="获取课表（不推送）")
    parser.add_argument("--push-schedule", action="store_true", help="推送课表")
    parser.add_argument("--force", action="store_true", help="强制从网络更新，忽略循环检测")
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
        logger.info("执行: fetch_and_push_schedule(push=False)")
        fetch_and_push_schedule(push=False, force_update=args.force)
    if args.push_schedule:
        logger.info("执行: fetch_and_push_schedule(push=True)")
        fetch_and_push_schedule(push=True, force_update=args.force)
    
    logger.info("main() 执行完成")


if __name__ == "__main__":
    main()
