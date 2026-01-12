import sys
import os
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox,
    QCheckBox, QSpinBox, QHBoxLayout, QGroupBox
)
from crypto_util import encrypt, decrypt

# 动态计算配置文件路径
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.ini"
CONFIG_FILE = str(CONFIG_FILE)

class ConfigWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("学业助手 · 设置")
        self.resize(450, 600)

        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_FILE, encoding="utf-8")

        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        # 账号配置
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        # 邮箱配置
        self.smtp = QLineEdit()
        self.port = QLineEdit()
        self.sender = QLineEdit()
        self.receiver = QLineEdit()
        self.auth = QLineEdit()
        self.auth.setEchoMode(QLineEdit.Password)

        # 学期配置
        self.first_monday = QLineEdit()

        form.addRow("学号", self.username)
        form.addRow("密码", self.password)
        form.addRow("SMTP", self.smtp)
        form.addRow("端口", self.port)
        form.addRow("发件邮箱", self.sender)
        form.addRow("收件邮箱", self.receiver)
        form.addRow("邮箱授权码", self.auth)
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

        # 保存按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)

        layout.addWidget(self.save_btn)
        self.setLayout(layout)

    def load_config(self):
        # 加载账号配置
        self.username.setText(self.cfg.get("account", "username", fallback=""))
        self.password.setText(decrypt(self.cfg.get("account", "password", fallback="")))

        # 加载邮箱配置
        self.smtp.setText(self.cfg.get("email", "smtp", fallback=""))
        self.port.setText(self.cfg.get("email", "port", fallback=""))
        self.sender.setText(self.cfg.get("email", "sender", fallback=""))
        self.receiver.setText(self.cfg.get("email", "receiver", fallback=""))
        self.auth.setText(decrypt(self.cfg.get("email", "auth", fallback="")))

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

    def save_config(self):
        # 保存账号配置
        if "account" not in self.cfg:
            self.cfg["account"] = {}
        self.cfg["account"]["username"] = self.username.text()
        self.cfg["account"]["password"] = encrypt(self.password.text())

        # 保存邮箱配置
        if "email" not in self.cfg:
            self.cfg["email"] = {}
        self.cfg["email"]["smtp"] = self.smtp.text()
        self.cfg["email"]["port"] = self.port.text()
        self.cfg["email"]["sender"] = self.sender.text()
        self.cfg["email"]["receiver"] = self.receiver.text()
        self.cfg["email"]["auth"] = encrypt(self.auth.text())

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

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            self.cfg.write(f)

        QMessageBox.information(self, "成功", "配置已保存")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ConfigWindow()
    w.show()
    sys.exit(app.exec())
