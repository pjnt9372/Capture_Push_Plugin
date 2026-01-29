# gui/tabs/software_settings_tab.py
from PySide6.QtWidgets import QVBoxLayout, QGroupBox, QHBoxLayout, QCheckBox, QSpinBox, QLabel
from .base_tab import BaseTab

class SoftwareSettingsTab(BaseTab):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

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

    def load_config(self):
        # 循环
        self.loop_grade_enabled.setChecked(self.config_manager.getboolean("loop_getCourseGrades", "enabled", fallback=True))
        self.loop_grade_interval.setValue(self.config_manager.getint("loop_getCourseGrades", "time", fallback=21600))
        self.loop_schedule_enabled.setChecked(self.config_manager.getboolean("loop_getCourseSchedule", "enabled", fallback=False))
        self.loop_schedule_interval.setValue(self.config_manager.getint("loop_getCourseSchedule", "time", fallback=604800))

        # 定时推送
        if "schedule_push" not in self.config_manager:
            self.config_manager["schedule_push"] = {}
        self.push_today_enabled.setChecked(self.config_manager.getboolean("schedule_push", "today_8am", fallback=False))
        self.push_tomorrow_enabled.setChecked(self.config_manager.getboolean("schedule_push", "tomorrow_9pm", fallback=False))
        self.push_next_week_enabled.setChecked(self.config_manager.getboolean("schedule_push", "next_week_sunday", fallback=False))

        # 自启动设置
        if "software_settings" not in self.config_manager:
            self.config_manager["software_settings"] = {}
        self.autostart_enabled.setChecked(self.config_manager.getboolean("software_settings", "autostart_tray", fallback=False))

    def save_config(self):
        if "loop_getCourseGrades" not in self.config_manager:
            self.config_manager["loop_getCourseGrades"] = {}
        self.config_manager["loop_getCourseGrades"]["enabled"] = str(self.loop_grade_enabled.isChecked())
        self.config_manager["loop_getCourseGrades"]["time"] = str(self.loop_grade_interval.value())

        if "loop_getCourseSchedule" not in self.config_manager:
            self.config_manager["loop_getCourseSchedule"] = {}
        self.config_manager["loop_getCourseSchedule"]["enabled"] = str(self.loop_schedule_enabled.isChecked())
        self.config_manager["loop_getCourseSchedule"]["time"] = str(self.loop_schedule_interval.value())

        if "schedule_push" not in self.config_manager:
            self.config_manager["schedule_push"] = {}
        self.config_manager["schedule_push"]["today_8am"] = str(self.push_today_enabled.isChecked())
        self.config_manager["schedule_push"]["tomorrow_9pm"] = str(self.push_tomorrow_enabled.isChecked())
        self.config_manager["schedule_push"]["next_week_sunday"] = str(self.push_next_week_enabled.isChecked())

        autostart = self.autostart_enabled.isChecked()
        if "software_settings" not in self.config_manager:
            self.config_manager["software_settings"] = {}
        self.config_manager["software_settings"]["autostart_tray"] = str(autostart)