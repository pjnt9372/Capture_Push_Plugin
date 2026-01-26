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
    from config_manager import load_config
except ImportError:
    from core.log import init_logger, get_config_path
    from core.config_manager import load_config

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
        cfg = load_config()
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
        
        # 注册飞书推送
        try:
            from core.senders.feishu_sender import FeishuSender
            self.register_sender("feishu", FeishuSender())
        except Exception as e:
            logger.warning(f"注册飞书发送器失败: {e}")
        
        # 注册Server酱推送
        try:
            from core.senders.serverchan_sender import ServerChanSender
            self.register_sender("serverchan", ServerChanSender())
        except Exception as e:
            logger.warning(f"注册Server酱发送器失败: {e}")
    
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
    格式化成绩变化消息（纯文本）
    
    Args:
        changed: 字典，key为课程名称，value为变化描述
        
    Returns:
        str: 纯文本格式的消息内容
    """
    logger.info(f"格式化成绩变化消息，变化数: {len(changed)}")
    
    lines = ["📈 成绩更新提醒", "-" * 20]
    for k, v in changed.items():
        lines.append(f"课程: {k}")
        lines.append(f"变化: {v}")
        lines.append("-" * 10)
    
    content = "\n".join(lines)
    logger.debug(f"文本内容预览: {content[:200]}...")
    return content


def format_all_grades(grades):
    """
    格式化全部成绩消息（纯文本）
    
    Args:
        grades: 成绩列表，每项包含课程名称、成绩、学分、课程属性、学期
        
    Returns:
        str: 纯文本格式的消息内容
    """
    logger.info(f"格式化全部成绩消息，课程数: {len(grades)}")
    
    lines = ["📊 全部成绩列表", "=" * 20]
    for g in grades:
        lines.append(f"课程: {g['课程名称']}")
        lines.append(f"成绩: {g['成绩']} | 学分: {g['学分']}")
        lines.append(f"属性: {g['课程属性']} | 学期: {g['学期']}")
        lines.append("-" * 15)
    
    content = "\n".join(lines)
    logger.debug(f"文本内容预览: {content[:200]}...")
    return content


def format_schedule(courses, week, weekday, title="课表"):
    """
    格式化课表消息（纯文本）
    
    Args:
        courses: 课程列表，每项包含课程名称、开始小节、结束小节、教室
        week: 周数
        weekday: 星期几
        title: 标题前缀
        
    Returns:
        str: 纯文本格式的消息内容
    """
    logger.info(f"格式化课表消息，第{week}周 周{weekday}，课程数: {len(courses)}")
    
    lines = [f"📚 第 {week} 周 · {title}（周{weekday}）", "=" * 25]
    if not courses:
        lines.append("今天没有课哦，好好休息吧！")
    else:
        for c in courses:
            lines.append(f"课程: {c['课程名称']}")
            lines.append(f"节次: {c['开始小节']}-{c['结束小节']} 节")
            lines.append(f"教室: {c['教室']}")
            lines.append("-" * 15)
    
    content = "\n".join(lines)
    logger.debug(f"文本内容预览: {content[:200]}...")
    return content


def format_full_schedule(courses, week_count):
    """
    格式化完整学期课表消息（纯文本）
    
    Args:
        courses: 课程列表（按天分组）
        week_count: 总周数
        
    Returns:
        str: 纯文本格式的消息内容
    """
    logger.info(f"格式化完整课表消息，总周数: {week_count}")
    
    # 按课程名称分组，收集所有时间和地点信息
    course_details = {}
    for day_courses in courses:
        if not day_courses:
            continue
        for course in day_courses:
            course_name = course['课程名称']
            if course_name not in course_details:
                course_details[course_name] = []
            
            # 获取周次信息
            weeks_list = course['周次列表']
            if isinstance(weeks_list, list) and weeks_list:
                if weeks_list == ["全学期"]:
                    week_range = "全学期"
                else:
                    # 将周次列表按数字排序
                    sorted_weeks = sorted([w for w in weeks_list if isinstance(w, int)], key=int)
                    if len(sorted_weeks) == 1:
                        week_range = f"{sorted_weeks[0]}"
                    else:
                        # 找出连续区间
                        week_ranges = []
                        start = sorted_weeks[0]
                        end = sorted_weeks[0]
                        
                        for i in range(1, len(sorted_weeks)):
                            if sorted_weeks[i] == end + 1:
                                end = sorted_weeks[i]
                            else:
                                if start == end:
                                    week_ranges.append(f"{start}")
                                else:
                                    week_ranges.append(f"{start}-{end}")
                                start = end = sorted_weeks[i]
                        
                        if start == end:
                            week_ranges.append(f"{start}")
                        else:
                            week_ranges.append(f"{start}-{end}")
                        
                        week_range = "、".join(week_ranges)
            else:
                week_range = "?"
            
            # 添加时间和地点信息
            time_location = {
                'week_range': week_range,
                'weekday': course['星期'],
                'start_period': course['开始小节'],
                'end_period': course['结束小节'],
                'classroom': course['教室']
            }
            
            # 检查是否已有相同的时间地点信息，避免重复
            if time_location not in course_details[course_name]:
                course_details[course_name].append(time_location)
    
    lines = [f"📖 本学期完整课表（共{week_count}周）", "=" * 25]
    
    # 按课程名称排序输出
    for course_name in sorted(course_details.keys()):
        time_locations = course_details[course_name]
        
        # 按时间和地点排序
        sorted_times = sorted(time_locations, key=lambda x: (x['week_range'], x['weekday'], x['start_period']))
        
        # 格式化时间和地点信息
        time_place_info = []
        for tl in sorted_times:
            time_place_info.append(f"第{tl['week_range']}周，周{tl['weekday']}，第{tl['start_period']}-{tl['end_period']}节课；地点：{tl['classroom']}")
        
        # 合并同一课程的所有时间地点信息
        time_place_str = "；".join(time_place_info)
        lines.append(f"课程名称：{course_name}（{time_place_str}）")
    
    content = "\n".join(lines)
    logger.debug(f"文本内容预览: {content[:200]}...")
    return content


# ==================== 便捷发送函数（邮件） ====================

def send_grade_mail(changed):
    """发送成绩变化通知"""
    text = format_grade_changes(changed)
    return notification_manager.send_with_active_sender("成绩有更新", text)


def send_all_grades_mail(grades):
    """发送全部成绩通知"""
    text = format_all_grades(grades)
    return notification_manager.send_with_active_sender("全部成绩", text)


def send_schedule_mail(courses, week, weekday):
    """发送明日课表通知"""
    text = format_schedule(courses, week, weekday, "明日课表")
    return notification_manager.send_with_active_sender("明日课表提醒", text)


def send_today_schedule_mail(courses, week, weekday):
    """发送今日课表通知"""
    text = format_schedule(courses, week, weekday, "今日课表")
    return notification_manager.send_with_active_sender("今日课表", text)


def send_full_schedule_mail(courses, week_count):
    """发送完整学期课表通知"""
    text = format_full_schedule(courses, week_count)
    return notification_manager.send_with_active_sender("本学期完整课表", text)
