import sys
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFormLayout, QMessageBox, QCheckBox, QSpinBox, QHBoxLayout, 
    QGroupBox, QRadioButton, QButtonGroup, QTabWidget, QComboBox, 
    QDateEdit, QApplication
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import Qt, QDate, QUrl

# 动态获取基础目录和配置路径
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from log import get_config_path, get_log_file_path
except ImportError:
    from core.log import get_config_path, get_log_file_path

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

def get_app_version():
    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"

APP_VERSION = get_app_version()

class ConfigWindow(QWidget):
    """主配置窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push · 设置")
        self.resize(500, 650)
        
        # 放大全局字体以确保看清
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_FILE, encoding="utf-8")

        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_basic_tab(), "基本配置")
        self.tabs.addTab(self.create_push_tab(), "推送设置")
        self.tabs.addTab(self.create_about_tab(), "关于")
        layout.addWidget(self.tabs)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        
        self.view_grades_btn = QPushButton("查看成绩")
        self.view_grades_btn.clicked.connect(self.show_grades_viewer)
        
        self.view_schedule_btn = QPushButton("查看课表")
        self.view_schedule_btn.clicked.connect(self.show_schedule_viewer)
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_config)
        
        btn_layout.addWidget(self.view_grades_btn)
        btn_layout.addWidget(self.view_schedule_btn)
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

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.first_monday = QDateEdit()
        self.first_monday.setCalendarPopup(True)
        self.first_monday.setDisplayFormat("yyyy-MM-dd")

        form.addRow("选择院校", self.school_combo)
        form.addRow("学号", self.username)
        form.addRow("密码", self.password)
        form.addRow("第一周周一", self.first_monday)
        layout.addLayout(form)

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

        layout.addStretch()
        return tab

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
        
        self.push_button_group.addButton(self.push_none_radio, 0)
        self.push_button_group.addButton(self.push_email_radio, 1)
        self.push_button_group.addButton(self.push_feishu_radio, 2)
        
        method_layout.addWidget(self.push_none_radio)
        method_layout.addWidget(self.push_email_radio)
        method_layout.addWidget(self.push_feishu_radio)
        layout.addWidget(method_group)

        # 邮件配置
        email_group = QGroupBox("邮件配置")
        email_form = QFormLayout(email_group)
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
        layout.addWidget(email_group)

        # 飞书配置
        feishu_group = QGroupBox("飞书机器人配置")
        feishu_form = QFormLayout(feishu_group)
        self.feishu_webhook = QLineEdit()
        self.feishu_secret = QLineEdit()
        self.feishu_secret.setEchoMode(QLineEdit.Password)  # 密钥字段设为密码模式
        feishu_form.addRow("Webhook URL", self.feishu_webhook)
        feishu_form.addRow("密钥 (启用签名校验)", self.feishu_secret)
        layout.addWidget(feishu_group)

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
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(update_btn)
        btn_row.addWidget(crash_report_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        layout.addSpacing(20)
        layout.addWidget(author_label)
        layout.addStretch()

        return tab

    def load_config(self):
        # 院校
        school_code = self.cfg.get("account", "school_code", fallback="10546")
        index = self.school_combo.findData(school_code)
        if index >= 0:
            self.school_combo.setCurrentIndex(index)

        # 账号
        self.username.setText(self.cfg.get("account", "username", fallback=""))
        self.password.setText(self.cfg.get("account", "password", fallback=""))
        
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

        # 推送方式
        method = self.cfg.get("push", "method", fallback="none").lower()
        if method == "email": self.push_email_radio.setChecked(True)
        elif method == "feishu": self.push_feishu_radio.setChecked(True)
        else: self.push_none_radio.setChecked(True)

        # 详细配置
        self.smtp.setText(self.cfg.get("email", "smtp", fallback=""))
        self.port.setText(self.cfg.get("email", "port", fallback=""))
        self.sender.setText(self.cfg.get("email", "sender", fallback=""))
        self.receiver.setText(self.cfg.get("email", "receiver", fallback=""))
        self.auth.setText(self.cfg.get("email", "auth", fallback=""))
        self.feishu_webhook.setText(self.cfg.get("feishu", "webhook_url", fallback=""))
        self.feishu_secret.setText(self.cfg.get("feishu", "secret", fallback=""))

    def save_config(self):
        # 检查 Outlook
        sender = self.sender.text().strip().lower()
        if any(sender.endswith(d) for d in ["outlook.com", "hotmail.com", "live.com", "msn.com"]):
            QMessageBox.critical(self, "不支持的邮箱", "Outlook/Hotmail 等微软邮箱由于强制 OAuth2 认证，目前无法使用基本认证发送邮件，请更换发件人邮箱。")
            return

        # 写入内存
        if "account" not in self.cfg: self.cfg["account"] = {}
        self.cfg["account"]["school_code"] = self.school_combo.currentData()
        self.cfg["account"]["username"] = self.username.text()
        self.cfg["account"]["password"] = self.password.text()

        if "semester" not in self.cfg: self.cfg["semester"] = {}
        self.cfg["semester"]["first_monday"] = self.first_monday.date().toString("yyyy-MM-dd")

        if "loop_getCourseGrades" not in self.cfg: self.cfg["loop_getCourseGrades"] = {}
        self.cfg["loop_getCourseGrades"]["enabled"] = str(self.loop_grade_enabled.isChecked())
        self.cfg["loop_getCourseGrades"]["time"] = str(self.loop_grade_interval.value())

        if "loop_getCourseSchedule" not in self.cfg: self.cfg["loop_getCourseSchedule"] = {}
        self.cfg["loop_getCourseSchedule"]["enabled"] = str(self.loop_schedule_enabled.isChecked())
        self.cfg["loop_getCourseSchedule"]["time"] = str(self.loop_schedule_interval.value())

        if "schedule_push" not in self.cfg:
            self.cfg["schedule_push"] = {}
        self.cfg["schedule_push"]["today_8am"] = str(self.push_today_enabled.isChecked())
        self.cfg["schedule_push"]["tomorrow_9pm"] = str(self.push_tomorrow_enabled.isChecked())
        self.cfg["schedule_push"]["next_week_sunday"] = str(self.push_next_week_enabled.isChecked())

        if "push" not in self.cfg: self.cfg["push"] = {}
        if self.push_email_radio.isChecked(): self.cfg["push"]["method"] = "email"
        elif self.push_feishu_radio.isChecked(): self.cfg["push"]["method"] = "feishu"
        else: self.cfg["push"]["method"] = "none"

        if "email" not in self.cfg: self.cfg["email"] = {}
        self.cfg["email"]["smtp"] = self.smtp.text()
        self.cfg["email"]["port"] = self.port.text()
        self.cfg["email"]["sender"] = self.sender.text()
        self.cfg["email"]["receiver"] = self.receiver.text()
        self.cfg["email"]["auth"] = self.auth.text()

        if "feishu" not in self.cfg: self.cfg["feishu"] = {}
        self.cfg["feishu"]["webhook_url"] = self.feishu_webhook.text()
        self.cfg["feishu"]["secret"] = self.feishu_secret.text()

        # 物理保存
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                self.cfg.write(f)
            QMessageBox.information(self, "保存成功", "配置已成功保存到本地。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错：\n{str(e)}")

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
            from PySide6.QtWidgets import QProgressDialog
            
            progress = QProgressDialog("正在检查更新...", "取消", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            QApplication.processEvents()
            
            updater = Updater()
            result = updater.check_update()
            
            progress.close()
            
            if result:
                version, data = result
                reply = QMessageBox.question(
                    self,
                    "发现新版本",
                    f"当前版本: {updater.current_version}\n"
                    f"最新版本: {version}\n\n"
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
        """发送崩溃报告"""
        reply = QMessageBox.question(
            self,
            "崩溃上报",
            "是否要打包所有日志文件并生成崩溃报告？\n\n报告将保存在您的桌面或 AppData 目录中。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from core.log import pack_logs
                report_path = pack_logs()
                if report_path:
                    QMessageBox.information(self, "成功", f"崩溃报告已生成：\n{report_path}")
                else:
                    QMessageBox.warning(self, "失败", "日志文件打包失败，请检查程序是否具有写入权限。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成报告时发生异常：\n{str(e)}")

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
