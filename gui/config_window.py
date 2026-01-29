import sys
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFormLayout, QMessageBox, QCheckBox, QSpinBox, QHBoxLayout, 
    QGroupBox, QRadioButton, QButtonGroup, QTabWidget, QComboBox, 
    QDateEdit, QApplication, QToolButton, QTimeEdit, QScrollArea,QFileDialog,
    QGridLayout
)
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtCore import Qt, QDate, QUrl, QSize, QTime

# 导入日志模块
try:
    from log import init_logger
except ImportError:
    from core.log import init_logger

# 初始化日志记录器
logger = init_logger("config_window")

# 动态获取基础目录和配置路径
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from log import get_config_path, get_log_file_path
    from config_manager import load_config, save_config as save_config_manager, ConfigDecodingError
except ImportError:
    from core.log import get_config_path, get_log_file_path
    from core.config_manager import load_config, save_config as save_config_manager, ConfigDecodingError

try:
    from school import get_available_schools
except ImportError:
    from core.school import get_available_schools

# 导入子窗口
try:
    from grades_window import GradesViewerWindow
    from schedule_window import ScheduleViewerWindow
except ImportError:
    from gui.grades_window import GradesViewerWindow
    from gui.schedule_window import ScheduleViewerWindow

CONFIG_FILE = str(get_config_path())
GITHUB_URL = "https://github.com/pjnt9372/Capture_Push"


class CollapsibleBox(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)

        self.title = title
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标题栏
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet(
            "QToolButton {\n"
            "    border: none;\n"
            "    background: #f0f0f0;\n"
            "    border-radius: 4px;\n"
            "    padding: 6px;\n"
            "    font-weight: bold;\n"
            "    text-align: left;\n"
            "}\n" 
            "QToolButton::pressed {\n"
            "    background: #e0e0e0;\n"
            "}"
        )
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        
        # 内容区域
        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        
        # 布局
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        
        # 信号连接
        self.toggle_button.clicked.connect(self.on_pressed)
    
    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if not checked else Qt.RightArrow)
        
        if checked:
            self.content_area.setMaximumHeight(16777215)  # 设置为最大高度以展开
        else:
            self.content_area.setMaximumHeight(0)  # 设置为0以折叠


def get_app_version():
    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"

APP_VERSION = get_app_version()

class ConfigWindow(QWidget):
    """主配置窗口"""
    def __init__(self):
        logger.info("配置窗口初始化开始")
        super().__init__()
        self.setWindowTitle("Capture_Push · 设置")
        self.resize(500, 650)
        
        # 设置窗口图标
        try:
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent
            icon_path = BASE_DIR / "resources" / "app_icon.ico"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception as e:
            logger.error(f"无法设置窗口图标: {e}")
            print(f"无法设置窗口图标: {e}")
        
        # 放大全局字体以确保看清
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

        try:
            logger.info("正在加载配置")
            self.cfg = load_config()
            logger.info("配置加载成功")
        except ConfigDecodingError as e:
            logger.error(f"配置文件解码失败: {e}")
            # 显示配置文件解码错误的UI提示
            QMessageBox.critical(
                self,
                "配置文件错误",
                f"配置文件解码失败：\n{str(e)}\n\n建议重新配置（前往配置工具关于界面清除配置文件）或联系作者。",
                QMessageBox.Ok
            )
            # 创建一个空的配置对象作为备用
            self.cfg = configparser.ConfigParser()
        except Exception as e:
            logger.error(f"加载配置时发生未知错误: {e}")
            # 显示其他配置加载错误的UI提示
            QMessageBox.critical(
                self,
                "配置加载错误",
                f"加载配置时发生未知错误：\n{str(e)}\n\n建议重新配置（前往配置工具关于界面清除配置文件）或联系作者。",
                QMessageBox.Ok
            )
            # 创建一个空的配置对象作为备用
            self.cfg = configparser.ConfigParser()

        logger.info("正在初始化UI")
        self.init_ui()
        logger.info("正在加载配置到UI")
        self.load_config()
        logger.info("配置窗口初始化完成")

    def create_collapsible_group(self, title, group_name):
        """创建可折叠的配置组"""
        collapsible = CollapsibleBox(title)
        return collapsible

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_home_tab(), "首页")
        self.tabs.addTab(self.create_basic_tab(), "基本配置")
        self.tabs.addTab(self.create_software_settings_tab(), "软件设置")
        self.tabs.addTab(self.create_school_time_tab(), "学校时间设置")
        self.tabs.addTab(self.create_push_tab(), "推送设置")
        self.tabs.addTab(self.create_about_tab(), "关于")
        layout.addWidget(self.tabs)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_config)
        
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

    def create_basic_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.school_combo = QComboBox()
        self.available_schools = get_available_schools()
        for code, name in self.available_schools.items():
            self.school_combo.addItem(name, code)
        
        # 设置默认选中占位符学校
        placeholder_index = self.school_combo.findData("12345")
        if placeholder_index >= 0:
            self.school_combo.setCurrentIndex(placeholder_index)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("选择院校", self.school_combo)
        form.addRow("学号", self.username)
        form.addRow("密码", self.password)
        layout.addLayout(form)

        layout.addStretch()

        layout.addStretch()
        return tab

    def create_school_time_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        form = QFormLayout()
        
        self.first_monday = QDateEdit()
        self.first_monday.setCalendarPopup(True)
        self.first_monday.setDisplayFormat("yyyy-MM-dd")
        form.addRow("第一周周一", self.first_monday)
        
        self.morning_count = QSpinBox()
        self.morning_count.setRange(0, 10)
        self.morning_count.valueChanged.connect(self.update_class_time_inputs)
        form.addRow("上午几节课", self.morning_count)
        
        self.afternoon_count = QSpinBox()
        self.afternoon_count.setRange(0, 10)
        self.afternoon_count.valueChanged.connect(self.update_class_time_inputs)
        form.addRow("下午几节课", self.afternoon_count)
        
        self.evening_count = QSpinBox()
        self.evening_count.setRange(0, 10)
        self.evening_count.valueChanged.connect(self.update_class_time_inputs)
        form.addRow("晚上几节课", self.evening_count)
        
        self.class_duration = QSpinBox()
        self.class_duration.setRange(1, 120)
        self.class_duration.setSuffix(" 分钟")
        self.class_duration.valueChanged.connect(self.recalculate_class_times)
        form.addRow("一节课时长", self.class_duration)
        
        self.first_class_start = QTimeEdit()
        self.first_class_start.setDisplayFormat("HH:mm")
        self.first_class_start.timeChanged.connect(self.recalculate_class_times)
        form.addRow("第一节课开始时间", self.first_class_start)
        
        layout.addLayout(form)
        
        layout.addWidget(QLabel("各节课开始时间 (可手动修改):"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.class_times_container = QWidget()
        self.class_times_layout = QVBoxLayout(self.class_times_container)
        scroll.setWidget(self.class_times_container)
        layout.addWidget(scroll)
        
        self.class_time_edits = []
        
        return tab

    def update_class_time_inputs(self):
        # 彻底清除旧的布局内容
        while self.class_times_layout.count():
            item = self.class_times_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归清除子布局
                self._clear_layout(item.layout())
        
        self.class_time_edits = []
        
        total = self.morning_count.value() + self.afternoon_count.value() + self.evening_count.value()
        for i in range(total):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"第 {i+1} 节:"))
            edit = QLineEdit()
            row.addWidget(edit)
            self.class_time_edits.append(edit)
            self.class_times_layout.addLayout(row)
        
        self.recalculate_class_times()

    def _clear_layout(self, layout):
        """递归清除布局及其子项"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    def recalculate_class_times(self):
        if not hasattr(self, 'class_time_edits') or not self.class_time_edits:
            return
            
        start_time = self.first_class_start.time()
        duration = self.class_duration.value()
        
        # 简单推算：假设每节课之间没有休息时间（或者用户可以在推算后手动微调）
        # 实际学校通常有课间休息，所以这只是一个基准
        for i, edit in enumerate(self.class_time_edits):
            current_time = start_time.addSecs(i * duration * 60)
            if not edit.text(): # 只在为空时自动填充，避免覆盖手动修改？
                # 实际上用户可能想重置，所以如果是由 spinbox 触发的，可能应该覆盖
                pass
            edit.setText(current_time.toString("HH:mm"))

    def create_push_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 推送方式
        method_group = QGroupBox("推送方式 (单选)")
        method_layout = QVBoxLayout(method_group)
        self.push_button_group = QButtonGroup(self)
        
        self.push_none_radio = QRadioButton("不启用推送")
        self.push_email_radio = QRadioButton("邮件推送")
        self.push_feishu_radio = QRadioButton("飞书机器人推送")
        self.push_serverchan_radio = QRadioButton("Server酱推送")
        
        self.push_button_group.addButton(self.push_none_radio, 0)
        self.push_button_group.addButton(self.push_email_radio, 1)
        self.push_button_group.addButton(self.push_feishu_radio, 2)
        self.push_button_group.addButton(self.push_serverchan_radio, 3)
        
        method_layout.addWidget(self.push_none_radio)
        method_layout.addWidget(self.push_email_radio)
        method_layout.addWidget(self.push_feishu_radio)
        method_layout.addWidget(self.push_serverchan_radio)
        layout.addWidget(method_group)

        # 邮件配置（可折叠）
        self.email_collapsible = self.create_collapsible_group("邮件配置", "email_group")
        email_form = QFormLayout(self.email_collapsible.content_area)
        self.smtp = QLineEdit()
        self.port = QLineEdit()
        self.sender = QLineEdit()
        self.receiver = QLineEdit()
        self.auth = QLineEdit()
        self.auth.setEchoMode(QLineEdit.Password)
        email_form.addRow("SMTP服务器", self.smtp)
        email_form.addRow("端口", self.port)
        email_form.addRow("发件邮箱", self.sender)
        email_form.addRow("收件邮箱", self.receiver)
        email_form.addRow("授权码", self.auth)
        layout.addWidget(self.email_collapsible)

        # 飞书配置（可折叠）
        self.feishu_collapsible = self.create_collapsible_group("飞书机器人配置", "feishu_group")
        feishu_form = QFormLayout(self.feishu_collapsible.content_area)
        self.feishu_webhook = QLineEdit()
        self.feishu_webhook.setEchoMode(QLineEdit.Password)
        self.feishu_secret = QLineEdit()
        self.feishu_secret.setEchoMode(QLineEdit.Password)  # 密钥字段设为密码模式
        feishu_form.addRow("Webhook URL", self.feishu_webhook)
        feishu_form.addRow("密钥 (启用签名校验)", self.feishu_secret)
        layout.addWidget(self.feishu_collapsible)

        # Server酱配置（可折叠）
        self.serverchan_collapsible = self.create_collapsible_group("Server酱配置", "serverchan_group")
        serverchan_form = QFormLayout(self.serverchan_collapsible.content_area)
        self.serverchan_sendkey = QLineEdit()
        self.serverchan_sendkey.setEchoMode(QLineEdit.Normal)  # SendKey不需要隐藏
        serverchan_form.addRow("SendKey", self.serverchan_sendkey)
        layout.addWidget(self.serverchan_collapsible)

        # 连接推送方式选择的信号，以便自动展开对应的配置组
        self.push_button_group.buttonClicked.connect(self.on_push_method_changed_no_save)

        layout.addStretch()
        return tab

    def create_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # Logo/标题
        title_label = QLabel("Capture_Push")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4;")
        title_label.setAlignment(Qt.AlignCenter)
        
        version_label = QLabel(f"版本: {APP_VERSION}")
        version_label.setStyleSheet("font-size: 14px; color: #666666;")
        version_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel("课程成绩与课表自动追踪推送系统")
        desc_label.setStyleSheet("font-size: 14px;")
        desc_label.setAlignment(Qt.AlignCenter)

        # GitHub 链接
        github_btn = QPushButton("GitHub 项目主页")
        github_btn.setCursor(Qt.PointingHandCursor)
        github_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #0078d4;
                text-decoration: underline;
                background: transparent;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #005a9e;
            }
        """)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        
        # 检查更新按钮
        update_btn = QPushButton("检查更新")
        update_btn.setCursor(Qt.PointingHandCursor)
        update_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #0078d4;
                color: #0078d4;
                padding: 5px 15px;
                border-radius: 3px;
                background: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #0078d4;
                color: white;
            }
        """)
        update_btn.clicked.connect(self.check_for_updates)
        
        # 崩溃上报按钮
        crash_report_btn = QPushButton("崩溃上报")
        crash_report_btn.setCursor(Qt.PointingHandCursor)
        crash_report_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d83b01;
                color: #d83b01;
                padding: 5px 15px;
                border-radius: 3px;
                background: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #d83b01;
                color: white;
            }
        """)
        crash_report_btn.clicked.connect(self.send_crash_report)

        # 配置导出按钮
        export_config_btn = QPushButton("导出明文配置")
        export_config_btn.setCursor(Qt.PointingHandCursor)
        export_config_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #0078d4;
                color: #0078d4;
                padding: 5px 15px;
                border-radius: 3px;
                background: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #0078d4;
                color: white;
            }
        """)
        export_config_btn.clicked.connect(self.export_plaintext_config)

        # 清除配置按钮
        clear_config_btn = QPushButton("清除现有配置")
        clear_config_btn.setCursor(Qt.PointingHandCursor)
        clear_config_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ff6b6b;
                color: #ff6b6b;
                padding: 5px 15px;
                border-radius: 3px;
                background: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #ff6b6b;
                color: white;
            }
        """)
        clear_config_btn.clicked.connect(self.clear_config)

        # 修复安装按钮
        repair_btn = QPushButton("修复安装")
        repair_btn.setCursor(Qt.PointingHandCursor)
        repair_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #28a745;
                color: #28a745;
                padding: 5px 15px;
                border-radius: 3px;
                background: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #28a745;
                color: white;
            }
        """)
        repair_btn.clicked.connect(self.repair_installation)

        # 调整日志级别和运行模式按钮
        adjust_log_run_btn = QPushButton("调整日志/运行模式")
        adjust_log_run_btn.setCursor(Qt.PointingHandCursor)
        adjust_log_run_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #28a745;
                color: #28a745;
                padding: 5px 15px;
                border-radius: 3px;
                background: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #28a745;
                color: white;
            }
        """)
        adjust_log_run_btn.clicked.connect(self.adjust_logging_and_run_model)

        # 其他信息
        author_label = QLabel("开发者: pjnt9372")
        author_label.setStyleSheet("font-size: 12px; color: #999999;")
        author_label.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addWidget(desc_label)
        layout.addWidget(github_btn)
        layout.addSpacing(10)
        
        # 创建按钮网格布局
        button_grid = QGridLayout()
        button_grid.setSpacing(10)
        
        # 第一行按钮
        button_grid.addWidget(update_btn, 0, 0)
        button_grid.addWidget(crash_report_btn, 0, 1)
        
        # 第二行按钮
        button_grid.addWidget(export_config_btn, 1, 0)
        button_grid.addWidget(clear_config_btn, 1, 1)
        
        # 第三行按钮
        button_grid.addWidget(repair_btn, 2, 0)
        button_grid.addWidget(adjust_log_run_btn, 2, 1)
        
        # 设置列的伸缩因子，使按钮居中
        button_grid.setColumnStretch(0, 1)
        button_grid.setColumnStretch(1, 1)
        
        layout.addLayout(button_grid)
        
        layout.addSpacing(20)
        layout.addWidget(author_label)
        layout.addStretch()

        return tab

    def load_config(self):
        # 院校 - 总是默认显示占位符，让用户手动选择
        placeholder_index = self.school_combo.findData("12345")
        if placeholder_index >= 0:
            self.school_combo.setCurrentIndex(placeholder_index)
        
        # 但仍需加载其他账户信息
        self.username.setText(self.cfg.get("account", "username", fallback=""))
        self.password.setText(self.cfg.get("account", "password", fallback=""))
        
        # 学校时间设置
        self.morning_count.setValue(self.cfg.getint("school_time", "morning_count", fallback=4))
        self.afternoon_count.setValue(self.cfg.getint("school_time", "afternoon_count", fallback=4))
        self.evening_count.setValue(self.cfg.getint("school_time", "evening_count", fallback=2))
        self.class_duration.setValue(self.cfg.getint("school_time", "class_duration", fallback=45))
        
        start_time_str = self.cfg.get("school_time", "first_class_start", fallback="08:30")
        self.first_class_start.setTime(QTime.fromString(start_time_str, "HH:mm"))
        
        # 加载具体的各节课时间
        self.update_class_time_inputs()
        class_times_str = self.cfg.get("school_time", "class_times", fallback="")
        if class_times_str:
            times = class_times_str.split(",")
            for i, t in enumerate(times):
                if i < len(self.class_time_edits):
                    self.class_time_edits[i].setText(t.strip())
        
        date_str = self.cfg.get("semester", "first_monday", fallback="")
        if date_str:
            self.first_monday.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        else:
            self.first_monday.setDate(QDate.currentDate())

        # 循环
        self.loop_grade_enabled.setChecked(self.cfg.getboolean("loop_getCourseGrades", "enabled", fallback=True))
        self.loop_grade_interval.setValue(self.cfg.getint("loop_getCourseGrades", "time", fallback=21600))
        self.loop_schedule_enabled.setChecked(self.cfg.getboolean("loop_getCourseSchedule", "enabled", fallback=False))
        self.loop_schedule_interval.setValue(self.cfg.getint("loop_getCourseSchedule", "time", fallback=604800))

        # 定时推送
        if "schedule_push" not in self.cfg:
            self.cfg["schedule_push"] = {}
        self.push_today_enabled.setChecked(self.cfg.getboolean("schedule_push", "today_8am", fallback=False))
        self.push_tomorrow_enabled.setChecked(self.cfg.getboolean("schedule_push", "tomorrow_9pm", fallback=False))
        self.push_next_week_enabled.setChecked(self.cfg.getboolean("schedule_push", "next_week_sunday", fallback=False))
        
        # 自启动设置
        if "software_settings" not in self.cfg:
            self.cfg["software_settings"] = {}
        self.autostart_enabled.setChecked(self.cfg.getboolean("software_settings", "autostart_tray", fallback=False))

        # 推送方式
        method = self.cfg.get("push", "method", fallback="none").lower()
        if method == "email": self.push_email_radio.setChecked(True)
        elif method == "feishu": self.push_feishu_radio.setChecked(True)
        elif method == "serverchan": self.push_serverchan_radio.setChecked(True)
        else: self.push_none_radio.setChecked(True)

        # 详细配置
        self.smtp.setText(self.cfg.get("email", "smtp", fallback=""))
        self.port.setText(self.cfg.get("email", "port", fallback=""))
        self.sender.setText(self.cfg.get("email", "sender", fallback=""))
        self.receiver.setText(self.cfg.get("email", "receiver", fallback=""))
        self.auth.setText(self.cfg.get("email", "auth", fallback=""))
        self.feishu_webhook.setText(self.cfg.get("feishu", "webhook_url", fallback=""))
        self.feishu_secret.setText(self.cfg.get("feishu", "secret", fallback=""))
        self.serverchan_sendkey.setText(self.cfg.get("serverchan", "sendkey", fallback=""))
        
        # 根据当前配置展开对应的配置组（不自动保存）
        self.on_push_method_changed(auto_save=False)

    def save_config(self):
        logger.info("开始保存配置")
        # 检查 Outlook
        sender = self.sender.text().strip().lower()
        if any(sender.endswith(d) for d in ["outlook.com", "hotmail.com", "live.com", "msn.com"]):
            logger.warning(f"检测到不支持的邮箱类型: {sender}")
            QMessageBox.critical(self, "不支持的邮箱", "Outlook/Hotmail 等微软邮箱由于强制 OAuth2 认证，目前无法使用基本认证发送邮件，请更换发件人邮箱。")
            logger.info("配置保存被取消")
            return

        # 写入内存
        if "account" not in self.cfg: self.cfg["account"] = {}
        self.cfg["account"]["school_code"] = self.school_combo.currentData()
        self.cfg["account"]["username"] = self.username.text()
        self.cfg["account"]["password"] = self.password.text()

        if "school_time" not in self.cfg: self.cfg["school_time"] = {}
        self.cfg["school_time"]["morning_count"] = str(self.morning_count.value())
        self.cfg["school_time"]["afternoon_count"] = str(self.afternoon_count.value())
        self.cfg["school_time"]["evening_count"] = str(self.evening_count.value())
        self.cfg["school_time"]["class_duration"] = str(self.class_duration.value())
        self.cfg["school_time"]["first_class_start"] = self.first_class_start.time().toString("HH:mm")
        logger.debug(f"已保存学校时间配置: morning={self.morning_count.value()}, afternoon={self.afternoon_count.value()}, evening={self.evening_count.value()}")
        
        class_times = [edit.text() for edit in self.class_time_edits]
        self.cfg["school_time"]["class_times"] = ",".join(class_times)
        logger.debug(f"已保存课时时间配置: {len(class_times)} 个时间段")

        if "semester" not in self.cfg: self.cfg["semester"] = {}
        self.cfg["semester"]["first_monday"] = self.first_monday.date().toString("yyyy-MM-dd")
        logger.debug(f"已保存学期配置: first_monday={self.first_monday.date().toString('yyyy-MM-dd')}")

        if "loop_getCourseGrades" not in self.cfg: self.cfg["loop_getCourseGrades"] = {}
        self.cfg["loop_getCourseGrades"]["enabled"] = str(self.loop_grade_enabled.isChecked())
        self.cfg["loop_getCourseGrades"]["time"] = str(self.loop_grade_interval.value())
        logger.debug(f"已保存成绩循环配置: enabled={self.loop_grade_enabled.isChecked()}, interval={self.loop_grade_interval.value()}")

        if "loop_getCourseSchedule" not in self.cfg: self.cfg["loop_getCourseSchedule"] = {}
        self.cfg["loop_getCourseSchedule"]["enabled"] = str(self.loop_schedule_enabled.isChecked())
        self.cfg["loop_getCourseSchedule"]["time"] = str(self.loop_schedule_interval.value())
        logger.debug(f"已保存课表循环配置: enabled={self.loop_schedule_enabled.isChecked()}, interval={self.loop_schedule_interval.value()}")

        if "schedule_push" not in self.cfg:
            self.cfg["schedule_push"] = {}
        self.cfg["schedule_push"]["today_8am"] = str(self.push_today_enabled.isChecked())
        self.cfg["schedule_push"]["tomorrow_9pm"] = str(self.push_tomorrow_enabled.isChecked())
        self.cfg["schedule_push"]["next_week_sunday"] = str(self.push_next_week_enabled.isChecked())
        logger.debug(f"已保存定时推送配置: today_8am={self.push_today_enabled.isChecked()}, tomorrow_9pm={self.push_tomorrow_enabled.isChecked()}, next_week_sunday={self.push_next_week_enabled.isChecked()}")

        if "push" not in self.cfg: self.cfg["push"] = {}
        if self.push_email_radio.isChecked(): self.cfg["push"]["method"] = "email"
        elif self.push_feishu_radio.isChecked(): self.cfg["push"]["method"] = "feishu"
        elif self.push_serverchan_radio.isChecked(): self.cfg["push"]["method"] = "serverchan"
        else: self.cfg["push"]["method"] = "none"
        logger.debug(f"已保存推送方式: {self.cfg['push']['method']}")

        if "email" not in self.cfg: self.cfg["email"] = {}
        self.cfg["email"]["smtp"] = self.smtp.text()
        self.cfg["email"]["port"] = self.port.text()
        self.cfg["email"]["sender"] = self.sender.text()
        self.cfg["email"]["receiver"] = self.receiver.text()
        self.cfg["email"]["auth"] = self.auth.text()
        logger.debug(f"已保存邮件配置: smtp={self.smtp.text()}, sender={self.sender.text()}")

        if "feishu" not in self.cfg: self.cfg["feishu"] = {}
        self.cfg["feishu"]["webhook_url"] = self.feishu_webhook.text()
        self.cfg["feishu"]["secret"] = self.feishu_secret.text()
        logger.debug(f"已保存飞书配置: webhook_url={'***' if self.feishu_webhook.text() else 'empty'}, secret={'***' if self.feishu_secret.text() else 'empty'}")

        if "serverchan" not in self.cfg: self.cfg["serverchan"] = {}
        self.cfg["serverchan"]["sendkey"] = self.serverchan_sendkey.text()
        logger.debug(f"已保存Server酱配置: sendkey={'***' if self.serverchan_sendkey.text() else 'empty'}")
        
        # 自启动设置
        autostart = self.autostart_enabled.isChecked()
        if "software_settings" not in self.cfg:
            self.cfg["software_settings"] = {}
        self.cfg["software_settings"]["autostart_tray"] = str(autostart)
        logger.debug(f"已保存自启动配置: autostart={autostart}")
        
        # 同步更新系统自启动设置
        logger.info("正在更新系统自启动设置")
        self._update_autostart_registry(autostart)
        
        # 物理保存
        logger.info("正在保存配置文件")
        self._save_config_to_file()
        logger.info("配置保存完成")

    def _update_autostart_registry(self, enabled):
        """更新 Windows 注册表自启动项"""
        import winreg
        import sys
        import os
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Capture_Push_Tray"
        
        # 确定托盘程序路径
        # 在打包后的环境中，托盘程序通常位于应用根目录
        executable_path = os.path.abspath(sys.argv[0])
        app_root = os.path.dirname(os.path.dirname(executable_path)) if "gui" in executable_path else os.path.dirname(executable_path)
        tray_exe = os.path.join(app_root, "Capture_Push_tray.exe")
        
        # 如果当前目录下没找到，尝试在父目录查找（开发环境适配）
        if not os.path.exists(tray_exe):
            tray_exe = os.path.join(os.path.dirname(app_root), "Capture_Push_tray.exe")

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                # 只有在托盘程序文件存在时才设置，避免注册表引用失效路径
                if os.path.exists(tray_exe):
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{tray_exe}"')
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass # 如果本来就不存在，忽略错误
            winreg.CloseKey(key)
        except Exception as e:
            # 记录错误但不阻塞主配置保存流程
            print(f"更新自启动注册表失败: {e}")

    def export_plaintext_config(self):
        """ 导出明文配置（需先验证 Windows Hello） """
        logger.info("发起配置导出请求，正在调起 Windows Hello 验证...")
        
        # 1. 首先进行 Windows Hello 验证
        if not self.verify_windows_hello():
            logger.warning("Windows 身份验证未通过或已取消，无法导出配置。")
            QMessageBox.warning(self, "验证取消", "Windows 身份验证未通过或已取消，无法导出配置。")
            logger.info("Windows 身份验证未通过或已取消。")
            return

        logger.info("Windows 身份验证成功。")

        # 2. 验证通过，执行导出逻辑
        try:
            # 兼容性导入
            try:
                from core.config_manager import load_config
            except ImportError:
                from config_manager import load_config

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "导出明文配置", 
                "config_plaintext.ini", 
                "INI Files (*.ini);;All Files (*)"
            )
            
            if not file_path:
                logger.info("用户取消了文件保存")
                return

            # 加载当前加密配置字典
            current_config = load_config()
            
            # 创建新的 ConfigParser 来保存明文
            plaintext_cfg = configparser.ConfigParser()
            
            # 遍历并填入数据
            for section, options in current_config.items():
                # 修复 'DEFAULT' 导致的 Invalid section name 错误
                if section.upper() == 'DEFAULT':
                    # DEFAULT 节在 ConfigParser 中是内置的，直接写入 options
                    for key, value in options.items():
                        plaintext_cfg.set('DEFAULT', key, str(value))
                else:
                    # 普通节：如果不存在则创建
                    if not plaintext_cfg.has_section(section):
                        plaintext_cfg.add_section(section)
                    for key, value in options.items():
                        plaintext_cfg.set(section, key, str(value))
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                plaintext_cfg.write(f)
                
            logger.info(f"配置成功导出至: {file_path}")
            QMessageBox.information(self, "成功", f"明文配置已导出至：\n{file_path}\n\n请注意：此文件包含明文密码，请妥善保管！")

        except Exception as e:
            logger.error(f"导出过程中发生错误: {e}")
            QMessageBox.critical(self, "导出失败", f"导出过程中发生错误：\n{str(e)}")
            logger.error(f"导出明文配置失败: {e}")
            import traceback
            traceback.print_exc()

    def verify_windows_hello(self):
        """ 调用 Windows CredUI 触发 PIN/生物识别验证 - 修正 Error 87 版 """
        import ctypes
        from ctypes import wintypes
        import getpass
        
        try:
            # 1. 加载 DLL
            credui = ctypes.WinDLL('credui.dll')
            ole32 = ctypes.WinDLL('ole32.dll')
            
            # 2. 定义结构体和常量
            CREDUIWIN_GENERIC = 0x1
            CREDUIWIN_CHECKBOX = 0x2
            CREDUIWIN_AUTHPACKAGE_ONLY = 0x10
            CREDUIWIN_IN_CRED_ONLY = 0x20
            CREDUIWIN_ENUMERATE_CURRENT_USER = 0x200
            CREDUIWIN_SECURE_PROMPT = 0x1000
            
            class CREDUI_INFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("hwndParent", wintypes.HWND),
                    ("pszMessageText", wintypes.LPCWSTR),
                    ("pszCaptionText", wintypes.LPCWSTR),
                    ("hbmBanner", wintypes.HBITMAP)
                ]
            
            # 3. 准备函数：CredPackAuthenticationBufferW (修复 Error 87 的关键)
            # 该函数将用户名打包成 API 能识别的二进制格式
            CredPackAuthenticationBufferW = credui.CredPackAuthenticationBufferW
            CredPackAuthenticationBufferW.argtypes = [
                wintypes.DWORD,     # dwFlags
                wintypes.LPCWSTR,   # pszUserName
                wintypes.LPCWSTR,   # pszPassword
                ctypes.c_void_p,    # pPackedCredentials
                ctypes.POINTER(wintypes.DWORD) # pcbPackedCredentials
            ]
            CredPackAuthenticationBufferW.restype = wintypes.BOOL

            # 4. 准备函数：CredUIPromptForWindowsCredentialsW
            CredUIPromptForWindowsCredentialsW = credui.CredUIPromptForWindowsCredentialsW
            CredUIPromptForWindowsCredentialsW.argtypes = [
                ctypes.POINTER(CREDUI_INFO),
                wintypes.DWORD,
                ctypes.POINTER(wintypes.ULONG),
                wintypes.LPCVOID,       # pvInAuthBuffer (这里不能是 None)
                wintypes.ULONG,         # ulInAuthBufferSize
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(wintypes.ULONG),
                ctypes.POINTER(wintypes.BOOL),
                wintypes.DWORD
            ]
            CredUIPromptForWindowsCredentialsW.restype = wintypes.DWORD

            # ================= 步骤 A: 打包当前用户的凭据缓冲区 =================
            current_user = getpass.getuser()
            
            # 第一次调用获取所需的缓冲区大小
            packed_size = wintypes.DWORD(0)
            CredPackAuthenticationBufferW(0, current_user, "", None, ctypes.byref(packed_size))
            
            # 分配缓冲区
            in_auth_buffer = (ctypes.c_byte * packed_size.value)()
            
            # 第二次调用执行打包
            if not CredPackAuthenticationBufferW(0, current_user, "", in_auth_buffer, ctypes.byref(packed_size)):
                print(f"!!! 凭据打包失败，错误码: {ctypes.GetLastError()}")
                return False

            # ================= 步骤 B: 调起验证窗口 =================
            
            # 获取窗口句柄
            try:
                hwnd_parent = int(self.winId())
            except Exception:
                hwnd_parent = 0
            
            cred_info = CREDUI_INFO()
            cred_info.cbSize = ctypes.sizeof(CREDUI_INFO)
            cred_info.hwndParent = hwnd_parent
            cred_info.pszMessageText = ctypes.c_wchar_p(f"Capture Push 配置导出保护\n请验证身份以导出明文配置。")
            cred_info.pszCaptionText = ctypes.c_wchar_p("身份验证")
            cred_info.hbmBanner = None

            auth_package = wintypes.ULONG(0)
            out_buf = ctypes.c_void_p(0)
            out_size = wintypes.ULONG(0)
            save_cred = wintypes.BOOL(False)
            
            # 组合 Flags: 
            # AUTHPACKAGE_ONLY: 限制使用系统验证包
            # IN_CRED_ONLY: 验证我们传入的 in_auth_buffer，而不是让用户输入新用户名
            flags = CREDUIWIN_AUTHPACKAGE_ONLY | CREDUIWIN_IN_CRED_ONLY
            
            print(f"DEBUG: 调起 Windows Hello, 用户: {current_user}, Flags: {hex(flags)}")

            result = CredUIPromptForWindowsCredentialsW(
                ctypes.byref(cred_info),
                0,
                ctypes.byref(auth_package),
                in_auth_buffer,         # 传入刚才打包好的缓冲区 <--- 修复点
                packed_size.value,      # 传入缓冲区大小 <--- 修复点
                ctypes.byref(out_buf),
                ctypes.byref(out_size),
                ctypes.byref(save_cred),
                flags
            )
            
            # ================= 步骤 C: 处理结果 =================
            if result == 0:  # ERROR_SUCCESS
                print(">>> Windows Hello 验证通过")
                if out_buf.value:
                    ole32.CoTaskMemFree(out_buf)
                return True
            elif result == 1223: # ERROR_CANCELLED
                print(">>> 用户取消了验证")
                return False
            else:
                print(f"!!! Windows Hello 验证失败, 代码: {result}")
                return False
                
        except Exception as e:
            print(f"!!! Windows Hello 验证发生未捕获异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def clear_config(self):
        """清除现有配置"""
        reply = QMessageBox.question(
            self, "确认清除", 
            "您确定要清除所有配置信息吗？此操作不可恢复。\n\n清除后需要重新配置所有信息。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 获取配置文件路径
                config_path = Path(CONFIG_FILE)
                
                # 创建一个空配置
                empty_cfg = configparser.ConfigParser()
                
                # 添加基本配置节
                empty_cfg["logging"] = {"level": "INFO"}
                empty_cfg["run_model"] = {"model": "BUILD"}
                empty_cfg["account"] = {"school_code": "12345", "username": "", "password": ""}
                empty_cfg["push"] = {"method": "none"}
                
                # 使用配置管理器保存配置（自动加密）
                from core.config_manager import save_config
                save_config(empty_cfg)
                
                # 重新加载配置
                self.cfg = load_config()
                self.load_config()
                
                QMessageBox.information(self, "清除成功", "配置已清除，请重新配置各项信息。")
            except Exception as e:
                QMessageBox.critical(self, "清除失败", f"清除配置文件时出错：\n{str(e)}")

    def repair_installation(self):
        """修复安装功能"""
        reply = QMessageBox.question(
            self, "修复安装", 
            "是否执行修复安装？此操作将重新验证安装包完整性并重新安装。\n\n" +
            "修复安装将：\n" +
            "1. 检查本地保存的安装包\n" +
            "2. 验证安装包的完整性\n" +
            "3. 执行静默修复安装\n\n" +
            "注意：此操作将重启应用程序。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from core.updater import Updater
                
                updater = Updater()
                # 使用轻量级安装包进行修复
                success = updater.repair_installation(use_lite=True)
                
                if success:
                    QMessageBox.information(self, "修复成功", "修复安装已完成，应用程序将退出，请重新启动。")
                    QApplication.quit()
                else:
                    QMessageBox.critical(self, "修复失败", "修复安装未能成功完成，请检查日志或重新下载安装包。")
            except Exception as e:
                QMessageBox.critical(self, "修复错误", f"执行修复安装时出现错误：\n{str(e)}")

    def adjust_logging_and_run_model(self):
        """调整日志级别和运行模式"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
        
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("调整日志级别和运行模式")
        dialog.resize(400, 150)
        
        layout = QVBoxLayout(dialog)
        
        # 日志级别选择
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("日志级别:"))
        log_combo = QComboBox()
        log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        
        # 从当前配置加载值
        current_log_level = self.cfg.get("logging", "level", fallback="INFO")
        log_combo.setCurrentText(current_log_level)
        
        log_layout.addWidget(log_combo)
        layout.addLayout(log_layout)
        
        # 运行模式选择
        run_layout = QHBoxLayout()
        run_layout.addWidget(QLabel("运行模式:"))
        run_combo = QComboBox()
        run_combo.addItems(["DEV", "BUILD"])
        
        # 从当前配置加载值
        current_run_model = self.cfg.get("run_model", "model", fallback="BUILD")
        run_combo.setCurrentText(current_run_model)
        
        run_layout.addWidget(run_combo)
        layout.addLayout(run_layout)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # 显示对话框并处理结果
        if dialog.exec() == QDialog.Accepted:
            try:
                # 更新配置
                if "logging" not in self.cfg:
                    self.cfg["logging"] = {}
                if "run_model" not in self.cfg:
                    self.cfg["run_model"] = {}
                    
                self.cfg["logging"]["level"] = log_combo.currentText()
                self.cfg["run_model"]["model"] = run_combo.currentText()
                
                # 保存配置
                from core.config_manager import save_config
                save_config(self.cfg)
                
                # 重新加载配置以确保更改生效
                self.cfg = load_config()
                
                QMessageBox.information(self, "修改成功", 
                                      f"日志级别已设置为 {log_combo.currentText()}，\n运行模式已设置为 {run_combo.currentText()}")
            except Exception as e:
                QMessageBox.critical(self, "修改失败", f"保存配置时出错：\n{str(e)}")

    def on_push_method_changed(self, auto_save=False):
        """根据推送方式选择展开对应的配置组
        
        Args:
            auto_save: 是否自动保存配置，默认为False
        """
        # 默认折叠所有配置组
        self.email_collapsible.toggle_button.setChecked(False)
        self.feishu_collapsible.toggle_button.setChecked(False)
        self.serverchan_collapsible.toggle_button.setChecked(False)
        
        # 展开当前选中的推送方式对应的配置组
        if self.push_email_radio.isChecked():
            self.email_collapsible.toggle_button.setChecked(True)
        elif self.push_feishu_radio.isChecked():
            self.feishu_collapsible.toggle_button.setChecked(True)
        elif self.push_serverchan_radio.isChecked():
            self.serverchan_collapsible.toggle_button.setChecked(True)
        
        # 只有在auto_save为True时才保存配置
        if auto_save:
            self._save_config_to_file()

    def on_push_method_changed_no_save(self):
        """仅根据推送方式选择展开对应的配置组，不自动保存配置"""
        # 默认折叠所有配置组
        self.email_collapsible.toggle_button.setChecked(False)
        self.feishu_collapsible.toggle_button.setChecked(False)
        self.serverchan_collapsible.toggle_button.setChecked(False)
        
        # 展开当前选中的推送方式对应的配置组
        if self.push_email_radio.isChecked():
            self.email_collapsible.toggle_button.setChecked(True)
        elif self.push_feishu_radio.isChecked():
            self.feishu_collapsible.toggle_button.setChecked(True)
        elif self.push_serverchan_radio.isChecked():
            self.serverchan_collapsible.toggle_button.setChecked(True)

    def _save_config_to_file(self):
        """将配置保存到文件并加密"""
        try:
            save_config_manager(self.cfg)
            QMessageBox.information(self, "保存成功", "配置已成功保存并加密。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入加密配置文件时出错：\n{str(e)}")

    def show_grades_viewer(self):
        if not hasattr(self, 'grades_win') or not self.grades_win.isVisible():
            self.grades_win = GradesViewerWindow()
            self.grades_win.show()
        else:
            self.grades_win.activateWindow()

    def show_schedule_viewer(self):
        if not hasattr(self, 'sched_win') or not self.sched_win.isVisible():
            self.sched_win = ScheduleViewerWindow()
            self.sched_win.show()
        else:
            self.sched_win.activateWindow()

    def check_for_updates(self):
        """检查软件更新"""
        try:
            from core.updater import Updater
            from PySide6.QtWidgets import QProgressDialog, QCheckBox
            
            # 询问用户是否检查预发布版本
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("检查更新")
            msg_box.setText("是否检查预发布版本？")
            msg_box.setInformativeText(f"当前版本: {get_app_version()}\n预发布版本可能包含实验性功能，稳定性不如正式版。")
            
            yes_btn = msg_box.addButton("只检查正式版", QMessageBox.YesRole)
            beta_btn = msg_box.addButton("检查预发布版", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Cancel)
            
            msg_box.exec_()
            
            clicked_btn = msg_box.clickedButton()
            
            if clicked_btn == msg_box.button(QMessageBox.Cancel):
                return
            
            include_prerelease = clicked_btn == beta_btn
            
            progress = QProgressDialog("正在检查更新...", "取消", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            QApplication.processEvents()
            
            updater = Updater()
            result = updater.check_update(include_prerelease=include_prerelease)
            
            progress.close()
            
            if result:
                version, data = result
                is_prerelease = data.get('prerelease', False)
                reply = QMessageBox.question(
                    self,
                    "发现新版本",
                    f"当前版本: {updater.current_version}\n"
                    f"最新版本: {version}{' (预发布)' if is_prerelease else ''}\n\n"
                    f"是否下载更新？",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    has_python = updater.check_python_env()
                    use_lite = has_python
                    
                    download_progress = QProgressDialog(
                        f"正在下载 {'轻量级' if use_lite else '完整版'}更新包...",
                        "取消",
                        0, 100, self
                    )
                    download_progress.setWindowModality(Qt.WindowModal)
                    download_progress.setMinimumDuration(0)
                    
                    def update_progress(p):
                        download_progress.setValue(int(p))
                        QApplication.processEvents()
                    
                    installer_path = updater.download_update(data, use_lite, update_progress)
                    download_progress.close()
                    
                    if installer_path:
                        reply = QMessageBox.question(
                            self,
                            "下载完成",
                            f"更新包已下载完成！\n\n"
                            f"是否立即安装？\n"
                            f"（安装程序将关闭当前程序）",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if reply == QMessageBox.Yes:
                            if updater.install_update(installer_path, silent=False):
                                QMessageBox.information(self, "提示", "安装程序已启动，当前程序即将退出...")
                                QApplication.quit()
                        else:
                            QMessageBox.information(
                                self,
                                "提示",
                                f"安装包已保存在：\n{installer_path}\n\n"
                                f"您可以稍后手动运行安装。"
                            )
                    else:
                        QMessageBox.warning(self, "下载失败", "更新包下载失败，请稍后重试。")
            else:
                QMessageBox.information(self, "已是最新", f"当前已是最新版本（{updater.current_version}）")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"检查更新时出错：\n{str(e)}")

    def send_crash_report(self):
        """发送日志报告"""
        reply = QMessageBox.question(
            self,
            "日志上报",
            "是否要打包所有日志文件和本机硬件信息并生成日志报告？\n\n"
            "注意：报告将包含以下硬件信息：\n"
            "• 操作系统版本\n"
            "• 处理器型号\n"
            "• 内存大小\n"
            "• 磁盘信息\n"
            "• Windows更新补丁信息（如适用）\n\n"
            "报告将保存在您的桌面。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from core.log import pack_logs
                report_path = pack_logs()
                if report_path:
                    QMessageBox.information(self, "成功", f"日志报告已生成：\n{report_path}")
                else:
                    QMessageBox.warning(self, "失败", "日志文件打包失败，请检查程序是否具有写入权限。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成报告时发生异常：\n{str(e)}")

    def create_software_settings_tab(self):
        """创建软件设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 循环检测配置组
        loop_group = QGroupBox("循环检测配置")
        loop_layout = QVBoxLayout(loop_group)
        
        # 成绩循环
        grade_lay = QHBoxLayout()
        self.loop_grade_enabled = QCheckBox("启用成绩循环检测")
        self.loop_grade_interval = QSpinBox()
        self.loop_grade_interval.setRange(60, 604800)
        self.loop_grade_interval.setSuffix(" 秒")
        grade_lay.addWidget(self.loop_grade_enabled)
        grade_lay.addWidget(QLabel("间隔:"))
        grade_lay.addWidget(self.loop_grade_interval)
        loop_layout.addLayout(grade_lay)
        
        # 课表循环
        sched_lay = QHBoxLayout()
        self.loop_schedule_enabled = QCheckBox("启用课表循环检测")
        self.loop_schedule_interval = QSpinBox()
        self.loop_schedule_interval.setRange(60, 604800)
        self.loop_schedule_interval.setSuffix(" 秒")
        sched_lay.addWidget(self.loop_schedule_enabled)
        sched_lay.addWidget(QLabel("间隔:"))
        sched_lay.addWidget(self.loop_schedule_interval)
        loop_layout.addLayout(sched_lay)
        
        loop_layout.addWidget(QLabel("提示: 1小时=3600秒, 1天=86400秒"))
        layout.addWidget(loop_group)
        
        # 课表定时推送设置
        push_group = QGroupBox("课表定时推送设置")
        push_layout = QVBoxLayout(push_group)
        self.push_today_enabled = QCheckBox("当天 08:00 推送今日课表")
        self.push_tomorrow_enabled = QCheckBox("前一天 21:00 推送次日课表")
        self.push_next_week_enabled = QCheckBox("周日 20:00 推送下周全部课表")
        push_layout.addWidget(self.push_today_enabled)
        push_layout.addWidget(self.push_tomorrow_enabled)
        push_layout.addWidget(self.push_next_week_enabled)
        layout.addWidget(push_group)
        
        # 托盘程序自启动设置
        autostart_group = QGroupBox("托盘程序自启动")
        autostart_layout = QVBoxLayout(autostart_group)
        
        self.autostart_enabled = QCheckBox("开机自启动托盘程序")
        autostart_desc = QLabel("勾选此项将使托盘程序在系统启动时自动运行")
        autostart_desc.setWordWrap(True)
        autostart_layout.addWidget(self.autostart_enabled)
        autostart_layout.addWidget(autostart_desc)
        
        layout.addWidget(autostart_group)
        
        layout.addStretch()
        return tab
    
    def create_home_tab(self):
        """创建首页选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 标题
        title_label = QLabel("Capture_Push 首页")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4; margin: 20px 0 20px 0;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 功能按钮区域
        features_group = QGroupBox("功能")
        features_layout = QVBoxLayout(features_group)
        
        # 刷新成绩按钮
        self.refresh_grades_btn = QPushButton("刷新成绩")
        self.refresh_grades_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
        self.refresh_grades_btn.clicked.connect(self.refresh_grades_wrapper)
        features_layout.addWidget(self.refresh_grades_btn)
        
        # 刷新课表按钮
        self.refresh_schedule_btn = QPushButton("刷新课表")
        self.refresh_schedule_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
        self.refresh_schedule_btn.clicked.connect(self.refresh_schedule_wrapper)
        features_layout.addWidget(self.refresh_schedule_btn)
        
        # 查看成绩按钮
        self.view_grades_btn = QPushButton("查看成绩")
        self.view_grades_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.view_grades_btn.clicked.connect(self.show_grades_viewer_wrapper)
        features_layout.addWidget(self.view_grades_btn)
        
        # 查看课表按钮
        self.view_schedule_btn = QPushButton("查看课表")
        self.view_schedule_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.view_schedule_btn.clicked.connect(self.show_schedule_viewer_wrapper)
        features_layout.addWidget(self.view_schedule_btn)
        
        # 导入明文配置按钮
        self.import_config_btn = QPushButton("导入明文配置")
        self.import_config_btn.setStyleSheet("background-color: #ffc107; color: #212529; font-weight: bold; padding: 10px;")
        self.import_config_btn.clicked.connect(self.import_plaintext_config_wrapper)
        features_layout.addWidget(self.import_config_btn)
        
        layout.addWidget(features_group)
        
        # 添加一些空间
        layout.addStretch()
        
        return tab
    
    def refresh_grades_data(self):
        """刷新成绩数据"""
        try:
            # 导入需要的模块
            from core.go import fetch_and_push_grades
            
            # 调用获取成绩的函数
            fetch_and_push_grades(push=False, force_update=True)
            
            QMessageBox.information(self, "成功", "成绩数据刷新完成")
                
        except ImportError:
            # 如果从 core.go 导入失败，尝试直接从学校模块获取
            from core.config_manager import load_config
            cfg = load_config()
            school_code = cfg.get("account", "school_code", fallback="12345")
            
            from core.school import get_school_module
            school_mod = get_school_module(school_code)
            
            if not school_mod:
                QMessageBox.critical(self, "错误", f"无法获取学校模块：{school_code}")
                return
            
            username = cfg.get("account", "username", fallback="")
            password = cfg.get("account", "password", fallback="")
            
            if not username or not password:
                QMessageBox.warning(self, "警告", "请先在配置中填写账号密码")
                return
            
            # 调用获取成绩的函数
            result = school_mod.fetch_grades(username, password, force_update=True)
            
            if result:
                QMessageBox.information(self, "成功", "成绩数据刷新完成")
            else:
                QMessageBox.warning(self, "警告", "成绩数据刷新失败")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新成绩数据时发生错误：\n{str(e)}")
    
    def refresh_schedule_data(self):
        """刷新课表数据"""
        try:
            # 导入需要的模块
            from core.go import fetch_and_push_today_schedule
            
            # 调用获取课表的函数
            fetch_and_push_today_schedule(force_update=True)
            
            QMessageBox.information(self, "成功", "课表数据刷新完成")
                
        except ImportError:
            # 如果从 core.go 导入失败，尝试直接从学校模块获取
            from core.config_manager import load_config
            cfg = load_config()
            school_code = cfg.get("account", "school_code", fallback="12345")
            
            from core.school import get_school_module
            school_mod = get_school_module(school_code)
            
            if not school_mod:
                QMessageBox.critical(self, "错误", f"无法获取学校模块：{school_code}")
                return
            
            username = cfg.get("account", "username", fallback="")
            password = cfg.get("account", "password", fallback="")
            
            if not username or not password:
                QMessageBox.warning(self, "警告", "请先在配置中填写账号密码")
                return
            
            # 调用获取课表的函数
            result = school_mod.fetch_course_schedule(username, password, force_update=True)
            
            if result:
                QMessageBox.information(self, "成功", "课表数据刷新完成")
            else:
                QMessageBox.warning(self, "警告", "课表数据刷新失败")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新课表数据时发生错误：\n{str(e)}")

    def _set_button_pressed_style(self, button, pressed=True):
        """设置按钮按下样式"""
        if pressed:
            # 按下时的样式 - 添加边框和阴影效果
            button.setStyleSheet(
                "QPushButton { "
                "background-color: #005a9e; "  # 稍深的颜色表示按下状态
                "color: white; "
                "font-weight: bold; "
                "padding: 10px; "
                "border: 2px solid #004a87; "  # 添加边框
                "border-radius: 4px; "
                "box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); "  # 内阴影效果
                "}"
            )
        else:
            # 恢复正常样式
            if button == self.refresh_grades_btn:
                button.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
            elif button == self.refresh_schedule_btn:
                button.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
            elif button == self.view_grades_btn:
                button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
            elif button == self.view_schedule_btn:
                button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
            elif button == self.import_config_btn:
                button.setStyleSheet("background-color: #ffc107; color: #212529; font-weight: bold; padding: 10px;")

    def refresh_grades_wrapper(self):
        """刷新成绩数据的包装方法，带有按钮按下效果"""
        # 设置按钮为按下状态
        self._set_button_pressed_style(self.refresh_grades_btn, pressed=True)
        QApplication.processEvents()  # 立即更新UI
        
        try:
            self.refresh_grades_data()
        finally:
            # 恢复按钮正常状态
            self._set_button_pressed_style(self.refresh_grades_btn, pressed=False)

    def refresh_schedule_wrapper(self):
        """刷新课表数据的包装方法，带有按钮按下效果"""
        # 设置按钮为按下状态
        self._set_button_pressed_style(self.refresh_schedule_btn, pressed=True)
        QApplication.processEvents()  # 立即更新UI
        
        try:
            self.refresh_schedule_data()
        finally:
            # 恢复按钮正常状态
            self._set_button_pressed_style(self.refresh_schedule_btn, pressed=False)

    def show_grades_viewer_wrapper(self):
        """显示成绩查看器的包装方法，带有按钮按下效果"""
        # 设置按钮为按下状态
        self._set_button_pressed_style(self.view_grades_btn, pressed=True)
        QApplication.processEvents()  # 立即更新UI
        
        try:
            self.show_grades_viewer()
        finally:
            # 恢复按钮正常状态
            self._set_button_pressed_style(self.view_grades_btn, pressed=False)

    def show_schedule_viewer_wrapper(self):
        """显示课表查看器的包装方法，带有按钮按下效果"""
        # 设置按钮为按下状态
        self._set_button_pressed_style(self.view_schedule_btn, pressed=True)
        QApplication.processEvents()  # 立即更新UI
        
        try:
            self.show_schedule_viewer()
        finally:
            # 恢复按钮正常状态
            self._set_button_pressed_style(self.view_schedule_btn, pressed=False)

    def import_plaintext_config_wrapper(self):
        """导入明文配置的包装方法，带有按钮按下效果"""
        # 设置按钮为按下状态
        self._set_button_pressed_style(self.import_config_btn, pressed=True)
        QApplication.processEvents()  # 立即更新UI
        
        try:
            self.import_plaintext_config()
        finally:
            # 恢复按钮正常状态
            self._set_button_pressed_style(self.import_config_btn, pressed=False)

    def import_plaintext_config(self):
        """导入明文配置"""
        from PySide6.QtWidgets import QFileDialog
        import configparser
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入明文配置", "", "Configuration Files (*.ini);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            # 读取明文配置
            new_cfg = configparser.ConfigParser()
            new_cfg.read(file_path, encoding='utf-8')
            
            # 将新配置应用到当前配置管理器
            from core.config_manager import config_manager
            
            for section in new_cfg.sections():
                for key, value in new_cfg.items(section):
                    config_manager.set(section, key, value)
            
            # 重新加载UI显示
            self.load_config()
            QMessageBox.information(self, "成功", "明文配置导入成功，请点击【保存配置】以加密保存。")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入配置失败：\n{str(e)}")
    
    def closeEvent(self, event):
        """主窗口关闭事件：检查是否有子窗口未关闭"""
        active_sub_windows = []
        
        # 检查成绩窗口
        if hasattr(self, 'grades_win') and self.grades_win and self.grades_win.isVisible():
            active_sub_windows.append("成绩查看")
            
        # 检查课表窗口
        if hasattr(self, 'sched_win') and self.sched_win and self.sched_win.isVisible():
            active_sub_windows.append("课表查看")
            
        if active_sub_windows:
            win_list = "、".join(active_sub_windows)
            QMessageBox.warning(
                self, 
                "提示", 
                f"请先关闭正在运行的【{win_list}】页面，然后再关闭设置窗口。"
            )
            event.ignore()  # 忽略关闭事件
        else:
            event.accept()  # 允许关闭
