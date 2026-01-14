import sys
import os
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox,
    QCheckBox, QSpinBox, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QTabWidget
)

# 添加父目录到 sys.path（确保能找到 core 模块）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 导入统一配置路径管理
from core.log import get_config_path

# 使用统一的配置路径管理（AppData 目录）
CONFIG_FILE = str(get_config_path())

class ConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push · 设置")
        self.resize(450, 600)

        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_FILE, encoding="utf-8")

        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout()

        # 创建标签页控件
        self.tabs = QTabWidget()
        
        # 创建各个页面
        self.basic_tab = self.create_basic_tab()
        self.push_tab = self.create_push_tab()
        
        # 添加标签页
        self.tabs.addTab(self.basic_tab, "基本配置")
        self.tabs.addTab(self.push_tab, "推送设置")
        
        layout.addWidget(self.tabs)

        # 保存按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_btn)
        
        self.setLayout(layout)

    def create_basic_tab(self):
        """创建基本配置页面"""
        tab = QWidget()
        layout = QVBoxLayout()
        form = QFormLayout()

        # 账号配置
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        # 学期配置
        self.first_monday = QLineEdit()

        form.addRow("学号", self.username)
        form.addRow("密码", self.password)
        form.addRow("第一周周一 (YYYY-MM-DD)", self.first_monday)

        layout.addLayout(form)

        # 循环检测配置区域
        loop_group = QGroupBox("循环检测配置")
        loop_layout = QVBoxLayout()

        # 成绩循环检测
        grade_layout = QHBoxLayout()
        self.loop_grade_enabled = QCheckBox("启用成绩循环检测")
        grade_layout.addWidget(self.loop_grade_enabled)
        
        grade_interval_layout = QHBoxLayout()
        grade_interval_layout.addWidget(QLabel("更新间隔:"))
        self.loop_grade_interval = QSpinBox()
        self.loop_grade_interval.setRange(60, 604800)  # 60秒到1周
        self.loop_grade_interval.setSingleStep(60)
        self.loop_grade_interval.setSuffix(" 秒")
        grade_interval_layout.addWidget(self.loop_grade_interval)
        grade_interval_layout.addStretch()
        
        loop_layout.addLayout(grade_layout)
        loop_layout.addLayout(grade_interval_layout)

        # 课表循环检测
        schedule_layout = QHBoxLayout()
        self.loop_schedule_enabled = QCheckBox("启用课表循环检测")
        schedule_layout.addWidget(self.loop_schedule_enabled)
        
        schedule_interval_layout = QHBoxLayout()
        schedule_interval_layout.addWidget(QLabel("更新间隔:"))
        self.loop_schedule_interval = QSpinBox()
        self.loop_schedule_interval.setRange(60, 604800)  # 60秒到1周
        self.loop_schedule_interval.setSingleStep(60)
        self.loop_schedule_interval.setSuffix(" 秒")
        schedule_interval_layout.addWidget(self.loop_schedule_interval)
        schedule_interval_layout.addStretch()
        
        loop_layout.addLayout(schedule_layout)
        loop_layout.addLayout(schedule_interval_layout)

        # 添加常用时间间隔提示
        hint_label = QLabel(
            "常用时间间隔: 1小时=3600秒, 6小时=21600秒, "
            "1天=86400秒, 1周=604800秒"
        )
        hint_label.setStyleSheet("color: gray; font-size: 10px;")
        loop_layout.addWidget(hint_label)

        loop_group.setLayout(loop_layout)
        layout.addWidget(loop_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_push_tab(self):
        """创建推送设置页面"""
        tab = QWidget()
        layout = QVBoxLayout()

        # 推送方式配置区域
        push_group = QGroupBox("推送方式配置")
        push_layout = QVBoxLayout()

        # 创建互斥的单选按钮组
        self.push_button_group = QButtonGroup()
        
        # 不启用推送
        self.push_none_radio = QRadioButton("不启用推送")
        self.push_button_group.addButton(self.push_none_radio, 0)
        push_layout.addWidget(self.push_none_radio)
        
        # 邮件推送
        self.push_email_radio = QRadioButton("邮件推送")
        self.push_button_group.addButton(self.push_email_radio, 1)
        push_layout.addWidget(self.push_email_radio)

        # 飞书推送
        self.push_feishu_radio = QRadioButton("飞书机器人推送")
        self.push_button_group.addButton(self.push_feishu_radio, 3)
        push_layout.addWidget(self.push_feishu_radio)
        
        # 添加提示信息
        push_hint = QLabel(
            "提示: 只能同时启用一种推送方式。"
        )
        push_hint.setStyleSheet("color: gray; font-size: 10px;")
        push_layout.addWidget(push_hint)

        push_group.setLayout(push_layout)
        layout.addWidget(push_group)

        # 邮件配置区域
        email_group = QGroupBox("邮件推送配置")
        email_form = QFormLayout()
        
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
        email_form.addRow("邮箱授权码", self.auth)
        
        email_group.setLayout(email_form)
        layout.addWidget(email_group)

        # 飞书推送配置区域
        feishu_group = QGroupBox("飞书机器人配置")
        feishu_form = QFormLayout()
        
        self.feishu_webhook = QLineEdit()
        self.feishu_webhook.setPlaceholderText("https://open.feishu.cn/open-apis/bot/v2/hook/****")
        
        feishu_form.addRow("Webhook地址", self.feishu_webhook)
        
        feishu_group.setLayout(feishu_form)
        layout.addWidget(feishu_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def send_test_push(self):
        """发送测试推送"""
        try:
            self.test1_status.setText("状态: 正在发送测试推送...")
            self.test1_status.setStyleSheet("color: blue;")
            QApplication.processEvents()  # 更新UI
            
            # 导入推送模块
            from core import push
            
            # 检查推送是否启用
            if not push.is_push_enabled():
                self.test1_status.setText("状态: 推送未启用")
                self.test1_status.setStyleSheet("color: orange;")
                QMessageBox.warning(self, "测试失败", "请先启用一种推送方式")
                return
            
            # 发送测试消息
            manager = push.NotificationManager()
            success = manager.send_with_active_sender(
                "测试推送",
                "这是一条来自 Capture_Push 的测试推送消息。\n\n如果您收到此消息，说明推送配置正确！"
            )
            
            if success:
                self.test1_status.setText("状态: 测试推送发送成功")
                self.test1_status.setStyleSheet("color: green;")
                QMessageBox.information(self, "测试成功", "测试推送已发送，请检查接收端")
            else:
                self.test1_status.setText("状态: 测试推送发送失败")
                self.test1_status.setStyleSheet("color: red;")
                QMessageBox.warning(self, "测试失败", "推送发送失败，请检查配置和日志")
                
        except Exception as e:
            self.test1_status.setText(f"状态: 发生错误")
            self.test1_status.setStyleSheet("color: red;")
            QMessageBox.critical(self, "错误", f"测试推送时发生错误:\n{str(e)}")

    def load_config(self):
        # 加载账号配置
        self.username.setText(self.cfg.get("account", "username", fallback=""))
        self.password.setText(self.cfg.get("account", "password", fallback=""))

        # 加载邮箱配置
        self.smtp.setText(self.cfg.get("email", "smtp", fallback=""))
        self.port.setText(self.cfg.get("email", "port", fallback=""))
        self.sender.setText(self.cfg.get("email", "sender", fallback=""))
        self.receiver.setText(self.cfg.get("email", "receiver", fallback=""))
        self.auth.setText(self.cfg.get("email", "auth", fallback=""))

        # 加载学期配置
        self.first_monday.setText(
            self.cfg.get("semester", "first_monday", fallback="")
        )

        # 加载循环检测配置 - 成绩
        self.loop_grade_enabled.setChecked(
            self.cfg.getboolean("loop_getCourseGrades", "enabled", fallback=True)
        )
        self.loop_grade_interval.setValue(
            self.cfg.getint("loop_getCourseGrades", "time", fallback=21600)
        )

        # 加载循环检测配置 - 课表
        self.loop_schedule_enabled.setChecked(
            self.cfg.getboolean("loop_getCourseSchedule", "enabled", fallback=False)
        )
        self.loop_schedule_interval.setValue(
            self.cfg.getint("loop_getCourseSchedule", "time", fallback=604800)
        )

        # 加载推送方式配置
        push_method = self.cfg.get("push", "method", fallback="none").strip().lower()
        if push_method == "none":
            self.push_none_radio.setChecked(True)
        elif push_method == "email":
            self.push_email_radio.setChecked(True)
        elif push_method == "test1":
            self.push_test1_radio.setChecked(True)
        elif push_method == "feishu":
            self.push_feishu_radio.setChecked(True)
        # 未来可扩展其他推送方式的加载
        # elif push_method == "wechat":
        #     self.push_wechat_radio.setChecked(True)
        # elif push_method == "dingtalk":
        #     self.push_dingtalk_radio.setChecked(True)
        else:
            # 默认不启用
            self.push_none_radio.setChecked(True)

        # 加载飞书配置
        self.feishu_webhook.setText(self.cfg.get("feishu", "webhook_url", fallback=""))

    def save_config(self):
        # 保存账号配置
        if "account" not in self.cfg:
            self.cfg["account"] = {}
        self.cfg["account"]["username"] = self.username.text()
        self.cfg["account"]["password"] = self.password.text()

        # 保存邮箱配置
        if "email" not in self.cfg:
            self.cfg["email"] = {}
        self.cfg["email"]["smtp"] = self.smtp.text()
        self.cfg["email"]["port"] = self.port.text()
        self.cfg["email"]["sender"] = self.sender.text()
        self.cfg["email"]["receiver"] = self.receiver.text()
        self.cfg["email"]["auth"] = self.auth.text()

        # 保存学期配置
        if "semester" not in self.cfg:
            self.cfg["semester"] = {}
        self.cfg["semester"]["first_monday"] = self.first_monday.text()

        # 保存循环检测配置 - 成绩
        if "loop_getCourseGrades" not in self.cfg:
            self.cfg["loop_getCourseGrades"] = {}
        self.cfg["loop_getCourseGrades"]["enabled"] = str(self.loop_grade_enabled.isChecked())
        self.cfg["loop_getCourseGrades"]["time"] = str(self.loop_grade_interval.value())

        # 保存循环检测配置 - 课表
        if "loop_getCourseSchedule" not in self.cfg:
            self.cfg["loop_getCourseSchedule"] = {}
        self.cfg["loop_getCourseSchedule"]["enabled"] = str(self.loop_schedule_enabled.isChecked())
        self.cfg["loop_getCourseSchedule"]["time"] = str(self.loop_schedule_interval.value())

        # 保存推送方式配置
        if "push" not in self.cfg:
            self.cfg["push"] = {}
        
        # 根据选中的单选按钮保存推送方式
        if self.push_none_radio.isChecked():
            self.cfg["push"]["method"] = "none"
        elif self.push_email_radio.isChecked():
            self.cfg["push"]["method"] = "email"
        elif self.push_feishu_radio.isChecked():
            self.cfg["push"]["method"] = "feishu"
        # 未来可扩展其他推送方式的保存
        # elif self.push_wechat_radio.isChecked():
        #     self.cfg["push"]["method"] = "wechat"
        # elif self.push_dingtalk_radio.isChecked():
        #     self.cfg["push"]["method"] = "dingtalk"
        else:
            self.cfg["push"]["method"] = "none"

        # 检测 Outlook 邮箱并警告
        sender_email = self.sender.text().strip().lower()
        outlook_domains = ["outlook.com", "outlook.cn", "outlook.com.cn", "hotmail.com", "live.com"]
        
        if any(sender_email.endswith(domain) for domain in outlook_domains):
            reply = QMessageBox.question(
                self, 
                "Outlook 邮箱警告", 
                f"您输入的发件邮箱 '{sender_email}' 是 Outlook/Hotmail 邮箱。\n\n"
                f"Microsoft 已禁用对这些邮箱的基本认证，仅支持 OAuth2，\n"
                f"因此无法使用此程序发送邮件。\n\n"
                f"是否仍要保存此配置？\n\n"
                f"（建议更换其他邮箱服务商，如 QQ、163、Gmail 等）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return  # 取消保存

        # 保存邮件配置
        if "email" not in self.cfg:
            self.cfg["email"] = {}
        self.cfg["email"]["smtp"] = self.smtp.text()
        self.cfg["email"]["port"] = self.port.text()
        self.cfg["email"]["sender"] = self.sender.text()
        self.cfg["email"]["receiver"] = self.receiver.text()
        self.cfg["email"]["auth"] = self.auth.text()

        # 保存飞书配置
        if "feishu" not in self.cfg:
            self.cfg["feishu"] = {}
        self.cfg["feishu"]["webhook_url"] = self.feishu_webhook.text()

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            self.cfg.write(f)

        QMessageBox.information(self, "成功", "配置已保存")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ConfigWindow()
    w.show()
    sys.exit(app.exec())
