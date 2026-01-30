# gui/tabs/software_settings_tab.py
from PySide6.QtWidgets import QVBoxLayout, QGroupBox, QHBoxLayout, QCheckBox, QSpinBox, QLabel
from .base_tab import BaseTab

from core.utils.registry import is_autostart_enabled

from PySide6.QtCore import Signal

class SoftwareSettingsTab(BaseTab):
    autostart_changed = Signal(bool)  # 自定义信号，当自启动状态改变时发出
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.init_ui()
        self.connect_signals()
    
    def connect_signals(self):
        # 连接自启动复选框状态改变信号到处理函数
        self.autostart_enabled.stateChanged.connect(self.on_autostart_changed)
    
    def on_autostart_changed(self, state):
        # 当复选框状态改变时，更新注册表中的自启动设置
        autostart_enabled = bool(state)
        from core.utils.registry import set_autostart
        from PySide6.QtWidgets import QMessageBox
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            set_autostart(autostart_enabled)
            # 同时更新配置文件中的状态
            if "software_settings" not in self.config_manager:
                self.config_manager["software_settings"] = {}
            self.config_manager["software_settings"]["autostart_tray"] = str(autostart_enabled)
            
            # 成功更新后显示提示
            QMessageBox.information(self, "成功", f"开机自启{'已启用' if autostart_enabled else '已禁用'}")
            
        except PermissionError as e:
            logger.error(f"更新自启动设置时权限不足: {e}")
            # 权限不足时提示用户
            QMessageBox.critical(self, "权限错误", 
                               f"修改自启动设置时遇到权限问题:\n{str(e)}")
            # 恢复复选框的原始状态
            self.autostart_enabled.blockSignals(True)  # 阻止信号循环触发
            self.autostart_enabled.setChecked(not autostart_enabled)
            self.autostart_enabled.blockSignals(False)  # 恢复信号连接
            
        except Exception as e:
            logger.error(f"更新自启动设置时发生错误: {e}")
            # 其他错误也提示用户
            QMessageBox.critical(self, "错误", f"更新自启动设置时发生错误:\n{str(e)}")
            # 恢复复选框的原始状态
            self.autostart_enabled.blockSignals(True)  # 阻止信号循环触发
            self.autostart_enabled.setChecked(not autostart_enabled)
            self.autostart_enabled.blockSignals(False)  # 恢复信号连接

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

        # 自启动设置 - 优先从注册表读取当前状态，如果配置文件和注册表不一致则更新配置文件
        if "software_settings" not in self.config_manager:
            self.config_manager["software_settings"] = {}
        
        try:
            # 从注册表读取实际的自启动状态
            registry_autostart_status = is_autostart_enabled()
            
            # 检查配置文件中的状态
            config_autostart_status = self.config_manager.getboolean("software_settings", "autostart_tray", fallback=False)
            
            # 如果配置文件和注册表状态不一致，以注册表为准并更新配置文件
            if registry_autostart_status != config_autostart_status:
                self.config_manager["software_settings"]["autostart_tray"] = str(registry_autostart_status)
            
            self.autostart_enabled.setChecked(registry_autostart_status)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"读取自启动状态时发生错误: {e}，使用配置文件中的默认值")
            # 发生错误时，使用配置文件中的状态
            config_autostart_status = self.config_manager.getboolean("software_settings", "autostart_tray", fallback=False)
            self.autostart_enabled.setChecked(config_autostart_status)

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
        
        # 注意：自启动设置已在on_autostart_changed中更新注册表，不需要在此处重复设置