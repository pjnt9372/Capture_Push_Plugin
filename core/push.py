# -*- coding: utf-8 -*-
import smtplib
import configparser
import logging
import sys
from pathlib import Path
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod

# ===== 日志初始化 =====
import os
import logging.handlers
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe运行，从 AppData 目录读取配置
    appdata_dir = Path(os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', '.'))) / 'GradeTracker'
    appdata_dir.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH = appdata_dir / 'config.ini'
    
    # 如果 AppData 目录中没有 config.ini，则从原始位置复制一份
    if not CONFIG_PATH.exists():
        import shutil
        original_base = Path(sys._MEIPASS)
        original_config = original_base / 'config.ini'
        if original_config.exists():
            shutil.copy2(original_config, CONFIG_PATH)
else:
    # 如果是正常脚本运行
    BASE_DIR = Path(__file__).resolve().parent.parent
    CONFIG_PATH = BASE_DIR / 'config.ini'

# 确定日志文件路径（使用用户 AppData 目录）
if getattr(sys, 'frozen', False):
    # 打包后的环境，使用 AppData\Local\GradeTracker
    appdata_dir = Path(os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', '.'))) / 'GradeTracker'
    appdata_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = appdata_dir / 'push.log'
else:
    # 开发环境，使用当前目录
    log_file_path = Path('push.log')

try:
    # 先尝试加载 config.ini 中的日志配置
    logging.config.fileConfig(str(CONFIG_PATH))
    
    # 检查是否成功加载了 FileHandler，如果是，则替换其文件路径
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            # 关闭原处理器并移除
            handler.close()
            root_logger.removeHandler(handler)
    
    # 添加新的文件处理器到用户可写目录
    file_handler = logging.FileHandler(str(log_file_path), encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    logger = root_logger
    logger.info(f"成功加载 config.ini 中的日志配置，文件处理器已重定向到: {log_file_path}")
except (configparser.Error, Exception) as e:
    # 配置文件有问题，使用自定义配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # 控制台输出
            logging.FileHandler(str(log_file_path), encoding='utf-8')  # 文件输出到用户目录
        ]
    )
    logger = logging.getLogger(__name__)
    logger.warning(f"未能加载 config.ini 日志配置，使用默认配置到 {log_file_path}: {e}")


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
    
    logger.info(f"加载配置文件: {config_path}")
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