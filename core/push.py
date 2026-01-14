# -*- coding: utf-8 -*-
"""
消息推送模块
负责消息的格式化封装和发送调度，不包含具体的发送实现
具体的发送实现在 senders 目录下
"""
import configparser
from abc import ABC, abstractmethod

# 导入统一日志模块
try:
    from log import init_logger, get_config_path
except ImportError:
    from core.log import init_logger, get_config_path

# 导入具体的发送器实现
try:
    from senders.email_sender import EmailSender
except ImportError:
    from core.senders.email_sender import EmailSender

# 初始化日志
logger = init_logger('push')


def get_push_method():
    """
    从配置文件读取当前启用的推送方式
    
    Returns:
        str: 推送方式名称，默认为 'none'
    """
    try:
        config_path = get_config_path()
        cfg = configparser.ConfigParser()
        cfg.read(str(config_path), encoding='utf-8')
        method = cfg.get('push', 'method', fallback='none').strip().lower()
        logger.debug(f"读取推送配置: method={method}")
        return method
    except Exception as e:
        logger.error(f"读取推送配置失败: {e}，使用默认值 'none'")
        return 'none'


def is_push_enabled():
    """
    检查是否启用了任何推送方式
    
    Returns:
        bool: 如果推送方式不是 'none' 则返回 True
    """
    method = get_push_method()
    return method != 'none'


class NotificationSender(ABC):
    """通知发送器抽象基类"""
    
    @abstractmethod
    def send(self, subject, content):
        """
        发送通知
        
        Args:
            subject: 消息主题
            content: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        pass


class NotificationManager:
    """通知管理器，支持多种推送方式"""
    
    def __init__(self):
        self.senders = {}
        logger.info("初始化通知管理器")
        # 自动注册所有可用的发送器
        self._register_available_senders()
    
    def _register_available_senders(self):
        """注册所有可用的发送器"""
        # 注册邮件推送
        try:
            self.register_sender("email", EmailSender())
        except Exception as e:
            logger.warning(f"注册邮件发送器失败: {e}")
        
        # 未来可以在这里注册其他发送器
        # try:
        #     from senders.wechat_sender import WeChatSender
        #     self.register_sender("wechat", WeChatSender())
        # except ImportError:
        #     logger.debug("微信发送器未安装")
    
    def register_sender(self, name, sender):
        """注册新的推送方式"""
        logger.info(f"注册推送方式: {name}")
        self.senders[name] = sender
    
    def get_sender(self, name):
        """获取指定推送方式"""
        return self.senders.get(name)
    
    def get_active_sender(self):
        """
        根据配置获取当前活跃的发送器
        
        Returns:
            tuple: (sender_name, sender_instance) 或 (None, None)
        """
        method = get_push_method()
        if method == 'none':
            logger.debug("推送方式为 'none'，未启用推送")
            return None, None
        
        sender = self.get_sender(method)
        if sender:
            logger.debug(f"使用推送方式: {method}")
            return method, sender
        else:
            logger.error(f"配置的推送方式 '{method}' 未注册或不可用")
            return None, None
    
    def send_notification(self, sender_name, subject, content):
        """发送通知"""
        logger.info(f"使用 {sender_name} 发送通知: {subject}")
        sender = self.get_sender(sender_name)
        if sender:
            return sender.send(subject, content)
        else:
            logger.error(f"❗ 未找到名为 {sender_name} 的推送方式")
            print(f"❗ 未找到名为 {sender_name} 的推送方式")
            return False
    
    def send_with_active_sender(self, subject, content):
        """
        使用当前配置的活跃发送器发送通知
        
        Args:
            subject: 消息主题
            content: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        sender_name, sender = self.get_active_sender()
        if sender:
            logger.info(f"使用活跃发送器 '{sender_name}' 发送: {subject}")
            return sender.send(subject, content)
        else:
            logger.debug(f"未启用推送，跳过发送: {subject}")
            return False
    
    def get_available_senders(self):
        """获取可用的推送方式列表"""
        return list(self.senders.keys())


# 全局通知管理器实例
notification_manager = NotificationManager()


def send_notification(sender_name, subject, content):
    """
    通用通知发送函数
    
    Args:
        sender_name: 发送器名称（如 'email'）
        subject: 消息主题
        content: 消息内容（HTML格式）
        
    Returns:
        bool: 发送是否成功
    """
    logger.debug(f"调用 send_notification: sender={sender_name}, subject={subject}")
    return notification_manager.send_notification(sender_name, subject, content)


# ==================== 消息格式化函数 ====================

def format_grade_changes(changed):
    """
    格式化成绩变化消息
    
    Args:
        changed: 字典，key为课程名称，value为变化描述
        
    Returns:
        str: HTML格式的消息内容
    """
    logger.info(f"格式化成绩变化消息，变化数: {len(changed)}")
    logger.debug(f"变化详情: {changed}")
    
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
    logger.debug(f"HTML内容预览: {html[:200]}...")
    return html


def format_all_grades(grades):
    """
    格式化全部成绩消息
    
    Args:
        grades: 成绩列表，每项包含课程名称、成绩、学分、课程属性、学期
        
    Returns:
        str: HTML格式的消息内容
    """
    logger.info(f"格式化全部成绩消息，课程数: {len(grades)}")
    logger.debug(f"成绩详情: {[{'课程名称': g['课程名称'], '成绩': g['成绩'], '学分': g['学分'], '课程属性': g['课程属性']} for g in grades[:3]]}... (显示前3条)")
    
    rows = "".join(
        f"<tr><td>{g['课程名称']}</td><td>{g['成绩']}</td><td>{g['学分']}</td><td>{g['课程属性']}</td><td>{g['学期']}</td></tr>"
        for g in grades
    )
    html = f"""
    <h3>📊 全部成绩列表</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程名称</th><th>成绩</th><th>学分</th><th>课程属性</th><th>学期</th></tr>
      {rows}
    </table>
    """
    logger.debug(f"HTML内容预览: {html[:200]}...")
    return html


def format_schedule(courses, week, weekday, title="课表"):
    """
    格式化课表消息
    
    Args:
        courses: 课程列表，每项包含课程名称、开始小节、结束小节、教室
        week: 周数
        weekday: 星期几
        title: 标题前缀
        
    Returns:
        str: HTML格式的消息内容
    """
    logger.info(f"格式化课表消息，第{week}周 周{weekday}，课程数: {len(courses)}")
    logger.debug(f"课程详情: {[{'课程名称': c['课程名称'], '开始小节': c['开始小节'], '结束小节': c['结束小节'], '教室': c['教室']} for c in courses]}")
    
    rows = "".join(
        f"<tr><td>{c['课程名称']}</td><td>{c['开始小节']}-{c['结束小节']}</td><td>{c['教室']}</td></tr>"
        for c in courses
    )
    html = f"""
    <h3>📚 第 {week} 周 · {title}（周{weekday}）</h3>
    <table border="1" cellspacing="0" cellpadding="6">
      <tr><th>课程</th><th>节次</th><th>教室</th></tr>
      {rows}
    </table>
    """
    logger.debug(f"HTML内容预览: {html[:200]}...")
    return html


def format_full_schedule(courses, week_count):
    """
    格式化完整学期课表消息
    
    Args:
        courses: 课程列表（按天分组）
        week_count: 总周数
        
    Returns:
        str: HTML格式的消息内容
    """
    logger.info(f"格式化完整课表消息，总周数: {week_count}")
    logger.debug(f"课程总数: {sum(len(day_courses) for day_courses in courses) if courses else 0}")
    
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
    logger.debug(f"HTML内容预览: {html[:200]}...")
    return html


# ==================== 便捷发送函数（邮件） ====================

def send_grade_mail(changed):
    """发送成绩变化邮件（使用配置的推送方式）"""
    html = format_grade_changes(changed)
    return notification_manager.send_with_active_sender("成绩有更新", html)


def send_all_grades_mail(grades):
    """发送全部成绩邮件（使用配置的推送方式）"""
    html = format_all_grades(grades)
    return notification_manager.send_with_active_sender("全部成绩", html)


def send_schedule_mail(courses, week, weekday):
    """发送明日课表邮件（使用配置的推送方式）"""
    html = format_schedule(courses, week, weekday, "明日课表")
    return notification_manager.send_with_active_sender("明日课表提醒", html)


def send_today_schedule_mail(courses, week, weekday):
    """发送今日课表邮件（使用配置的推送方式）"""
    html = format_schedule(courses, week, weekday, "今日课表")
    return notification_manager.send_with_active_sender("今日课表", html)


def send_full_schedule_mail(courses, week_count):
    """发送完整学期课表邮件（使用配置的推送方式）"""
    html = format_full_schedule(courses, week_count)
    return notification_manager.send_with_active_sender("本学期完整课表", html)
