# -*- coding: utf-8 -*-
import os
import json
import argparse
import datetime
import configparser
import sys
from pathlib import Path

from core.getCourseGrades import fetch_grades
from core.getCourseSchedule import fetch_course_schedule
from core.push import send_grade_mail, send_schedule_mail

# 导入统一配置路径管理（AppData 目录）
from core.log import get_config_path

# 使用统一的配置路径管理（AppData 目录，如果失败直接崩溃）
CONFIG_FILE = str(get_config_path())

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
os.makedirs(STATE_DIR, exist_ok=True)

GRADE_STATE_FILE = os.path.join(STATE_DIR, "last_grades.json")
SCHEDULE_STATE_FILE = os.path.join(STATE_DIR, "last_schedule_day.txt")


# ---------- 配置 ----------
def load_config():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    return cfg


# ---------- 成绩相关 ----------
def load_last_grades():
    if not os.path.exists(GRADE_STATE_FILE):
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


def fetch_and_push_grades(push=False, force_update=False):
    """获取并推送成绩
    
    Args:
        push: 是否推送成绩到邮箱
        force_update: 是否强制从网络更新（忽略循环检测）
    """
    cfg = load_config()
    username = cfg.get("account", "username")
    password = cfg.get("account", "password")

    grades = fetch_grades(username, password, force_update)
    if not grades:
        print("❌ 成绩获取失败")
        return

    new_map = {g["课程名称"]: g["成绩"] for g in grades}
    old_map = load_last_grades()
    changed = diff_grades(old_map, new_map)

    if push and changed:
        send_grade_mail(changed)

    save_last_grades(new_map)

    if changed:
        print("✅ 成绩有更新")
    else:
        print("ℹ️ 成绩无变化")


# ---------- 课表相关 ----------
def load_last_schedule_day():
    if not os.path.exists(SCHEDULE_STATE_FILE):
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-grade", action="store_true", help="获取成绩（不推送）")
    parser.add_argument("--push-grade", action="store_true", help="推送成绩")
    parser.add_argument("--fetch-schedule", action="store_true", help="获取课表（不推送）")
    parser.add_argument("--push-schedule", action="store_true", help="推送课表")
    parser.add_argument("--force", action="store_true", help="强制从网络更新，忽略循环检测")
    args = parser.parse_args()

    if args.fetch_grade:
        fetch_and_push_grades(push=False, force_update=args.force)
    if args.push_grade:
        fetch_and_push_grades(push=True, force_update=args.force)
    if args.fetch_schedule:
        fetch_and_push_schedule(push=False, force_update=args.force)
    if args.push_schedule:
        fetch_and_push_schedule(push=True, force_update=args.force)


if __name__ == "__main__":
    main()
