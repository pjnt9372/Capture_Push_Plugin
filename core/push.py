# -*- coding: utf-8 -*-
import smtplib
import configparser
import sys
from pathlib import Path
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod

# 导入统一日志模块（AppData 目录）
from log import init_logger, get_config_path

# 初始化日志（如果失败直接崩溃）
logger = init_logger('push')

# 获取配置文件路径（AppData 目录，如果失败直接崩溃）
CONFIG_PATH = get_config_path()


def load_mail_cfg():
    """加载邮件配置"""
    cfg = configparser.ConfigParser()
    logger.info(f"加载配置文件: {CONFIG_PATH}")
    cfg.read(str(CONFIG_PATH), encoding="utf-8")
    return cfg


class NotificationSender(ABC):
    """通知发送器抽象基类，用于扩展各种推送方式"""
    
    @abstractmethod
    def send(self, subject, content):
        pass


class EmailSender(NotificationSender):
    """邮件推送实现"""
    
    def send(self, subject, html):
        logger.info(f"开始发送邮件: {subject}")
        cfg = load_mail_cfg()
        smtp = cfg.get("email", "smtp")
        port = cfg.getint("email", "port")
        sender = cfg.get("email", "sender")
        receiver = cfg.get("email", "receiver")
        auth = cfg.get("email", "auth")
        
        logger.debug(f"SMTP服务器: {smtp}:{port}, 发件人: {sender}, 收件人: {receiver}")

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = Header(subject, "utf-8")

        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            logger.debug(f"连接到 SMTP 服务器: {smtp}:{port}")
            server = smtplib.SMTP_SSL(smtp, port)
            logger.debug("正在登录...")
            server.login(sender, auth)
            logger.debug("正在发送邮件...")
            server.sendmail(sender, [receiver], msg.as_string())
            server.quit()
            logger.info(f"✅ 邮件发送成功: {subject}")
            print(f"✅ 邮件发送成功: {subject}")
            return True
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {e}", exc_info=True)
            print(f"❌ 邮件发送失败: {e}")
            return False


class NotificationManager:
    """通知管理器，支持多种推送方式"""
    
    def __init__(self):
        self.senders = {}
        # 默认注册邮件推送
        logger.info("初始化通知管理器")
        self.register_sender("email", EmailSender())
    
    def register_sender(self, name, sender):
        """注册新的推送方式"""
        logger.info(f"注册推送方式: {name}")
        self.senders[name] = sender
    
    def get_sender(self, name):
        """获取指定推送方式"""
        return self.senders.get(name)
    
    def send_notification(self, sender_name, subject, content):
        """发送通知"""
        logger.info(f"使用 {sender_name} 发送通知: {subject}")
        sender = self.get_sender(sender_name)
        if sender:
            return sender.send(subject, content)
        else:
            logger.error(f"❌ 未找到名为 {sender_name} 的推送方式")
            print(f"❌ 未找到名为 {sender_name} 的推送方式")
            return False
    
    def get_available_senders(self):
        """获取可用的推送方式列表"""
        return list(self.senders.keys())


# 全局通知管理器实例
notification_manager = NotificationManager()


def send_notification(sender_name, subject, content):
    """通用通知发送函数"""
    logger.debug(f"调用 send_notification: sender={sender_name}, subject={subject}")
    return notification_manager.send_notification(sender_name, subject, content)


def send_grade_mail(changed):
    logger.info(f"准备发送成绩更新邮件，变化数: {len(changed)}")
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
    logger.info(f"准备发送全部成绩，课程数: {len(grades)}")
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
    logger.info(f"准备发送课表邮件，第{week}周 周{weekday}，课程数: {len(courses)}")
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
    logger.info(f"准备发送今日课表，第{week}周 周{weekday}，课程数: {len(courses)}")
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
    logger.info(f"准备发送全部课表，总周数: {week_count}")
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