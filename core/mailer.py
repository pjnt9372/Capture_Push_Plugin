# -*- coding: utf-8 -*-
import smtplib
import configparser
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod


def load_mail_cfg():
    cfg = configparser.ConfigParser()
    import os
    import sys
    from pathlib import Path
    # 使用可执行文件所在目录或脚本所在目录作为基础路径
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe运行
        base_dir = Path(sys._MEIPASS)
    else:
        # 如果是正常脚本运行
        base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config.ini"
    cfg.read(str(config_path), encoding="utf-8")
    return cfg


class NotificationSender(ABC):
    """通知发送器抽象基类，用于扩展各种推送方式"""
    
    @abstractmethod
    def send(self, subject, content):
        pass


class EmailSender(NotificationSender):
    """邮件推送实现"""
    
    def send(self, subject, html):
        cfg = load_mail_cfg()
        smtp = cfg.get("email", "smtp")
        port = cfg.getint("email", "port")
        sender = cfg.get("email", "sender")
        receiver = cfg.get("email", "receiver")
        auth = cfg.get("email", "auth")

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = Header(subject, "utf-8")

        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            server = smtplib.SMTP_SSL(smtp, port)
            server.login(sender, auth)
            server.sendmail(sender, [receiver], msg.as_string())
            server.quit()
            print(f"✅ 邮件发送成功: {subject}")
            return True
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False


class NotificationManager:
    """通知管理器，支持多种推送方式"""
    
    def __init__(self):
        self.senders = {}
        # 默认注册邮件推送
        self.register_sender("email", EmailSender())
    
    def register_sender(self, name, sender):
        """注册新的推送方式"""
        self.senders[name] = sender
    
    def get_sender(self, name):
        """获取指定推送方式"""
        return self.senders.get(name)
    
    def send_notification(self, sender_name, subject, content):
        """发送通知"""
        sender = self.get_sender(sender_name)
        if sender:
            return sender.send(subject, content)
        else:
            print(f"❌ 未找到名为 {sender_name} 的推送方式")
            return False
    
    def get_available_senders(self):
        """获取可用的推送方式列表"""
        return list(self.senders.keys())


# 全局通知管理器实例
notification_manager = NotificationManager()


def send_notification(sender_name, subject, content):
    """通用通知发送函数"""
    return notification_manager.send_notification(sender_name, subject, content)


def send_grade_mail(changed):
    rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in changed.items()
    )
    html = f"""
    <h3>📈 成绩更新提醒</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程</th><th>变化</th></tr>
      {rows}
    </table>
    """
    send_notification("email", "成绩有更新", html)


def send_all_grades(grades):
    """发送全部成绩"""
    rows = "".join(
        f"<tr><td>{g['课程名称']}</td><td>{g['成绩']}</td><td>{g['学期']}</td></tr>"
        for g in grades
    )
    html = f"""
    <h3>📊 全部成绩列表</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程名称</th><th>成绩</th><th>学期</th></tr>
      {rows}
    </table>
    """
    send_notification("email", "全部成绩", html)


def send_schedule_mail(courses, week, weekday):
    rows = "".join(
        f"<tr><td>{c['课程名称']}</td><td>{c['开始小节']}-{c['结束小节']}</td><td>{c['教室']}</td></tr>"
        for c in courses
    )
    html = f"""
    <h3>📚 第 {week} 周 · 周{weekday} 课表</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程</th><th>节次</th><th>教室</th></tr>
      {rows}
    </table>
    """
    send_notification("email", "明日课表提醒", html)


def send_today_schedule(courses, week, weekday):
    """发送当天课表"""
    rows = "".join(
        f"<tr><td>{c['课程名称']}</td><td>{c['开始小节']}-{c['结束小节']}</td><td>{c['教室']}</td></tr>"
        for c in courses
    )
    html = f"""
    <h3>📅 第 {week} 周 · 今日课表（周{weekday}）</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程</th><th>节次</th><th>教室</th></tr>
      {rows}
    </table>
    """
    send_notification("email", "今日课表", html)


def send_full_schedule(courses, week_count):
    """发送本学期全部课表"""
    rows = []
    for day_courses in courses:
        for course in day_courses:
            rows.append(f"<tr><td>{course['课程名称']}</td><td>周{course['星期']}</td><td>{course['开始小节']}-{course['结束小节']}</td><td>{course['教室']}</td></tr>")
    
    html = f"""
    <h3>📖 本学期完整课表（共{week_count}周）</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程名称</th><th>星期</th><th>节次</th><th>教室</th></tr>
      {''.join(rows)}
    </table>
    """
    send_notification("email", "本学期完整课表", html)