# gui/tabs/school_time_tab.py
from PySide6.QtWidgets import (
    QVBoxLayout, QFormLayout, QDateEdit, QSpinBox, QTimeEdit,
    QScrollArea, QLabel, QHBoxLayout, QLineEdit, QWidget
)
from PySide6.QtCore import QDate, QTime
from .base_tab import BaseTab
from ..widgets.collapsible_box import CollapsibleBox

class ClassTimesEditor(QWidget):
    """
    一个独立的组件，用于编辑各节课的开始时间。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.form = QFormLayout()

        self.first_monday = QDateEdit()
        self.first_monday.setCalendarPopup(True)
        self.first_monday.setDisplayFormat("yyyy-MM-dd")
        self.form.addRow("第一周周一", self.first_monday)

        self.morning_count = QSpinBox()
        self.morning_count.setRange(0, 10)
        self.form.addRow("上午几节课", self.morning_count)

        self.afternoon_count = QSpinBox()
        self.afternoon_count.setRange(0, 10)
        self.form.addRow("下午几节课", self.afternoon_count)

        self.evening_count = QSpinBox()
        self.evening_count.setRange(0, 10)
        self.form.addRow("晚上几节课", self.evening_count)

        self.class_duration = QSpinBox()
        self.class_duration.setRange(1, 120)
        self.class_duration.setSuffix(" 分钟")
        self.form.addRow("一节课时长", self.class_duration)

        self.first_class_start = QTimeEdit()
        self.first_class_start.setDisplayFormat("HH:mm")
        self.form.addRow("第一节课开始时间", self.first_class_start)

        layout.addLayout(self.form)

        layout.addWidget(QLabel("各节课开始时间 (可手动修改):"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.class_times_container = QWidget()
        self.class_times_layout = QVBoxLayout(self.class_times_container)
        scroll.setWidget(self.class_times_container)
        layout.addWidget(scroll)

        self.class_time_edits = []

    def _connect_signals(self):
        self.morning_count.valueChanged.connect(self._update_class_time_inputs)
        self.afternoon_count.valueChanged.connect(self._update_class_time_inputs)
        self.evening_count.valueChanged.connect(self._update_class_time_inputs)
        self.first_class_start.timeChanged.connect(self._recalculate_class_times)
        self.class_duration.valueChanged.connect(self._recalculate_class_times)

    def _update_class_time_inputs(self):
        # 清空现有布局
        while self.class_times_layout.count():
            item = self.class_times_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
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

        self._recalculate_class_times()

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    def _recalculate_class_times(self):
        if not self.class_time_edits:
            return
        start_time = self.first_class_start.time()
        duration = self.class_duration.value()
        for i, edit in enumerate(self.class_time_edits):
            current_time = start_time.addSecs(i * duration * 60)
            # 只在为空时自动填充，保留用户手动修改
            if not edit.text():
                edit.setText(current_time.toString("HH:mm"))

    def get_class_times_list(self):
        """获取当前所有课时时间的列表"""
        return [edit.text() for edit in self.class_time_edits]

    def set_class_times_from_list(self, times_list):
        """根据列表设置课时时间"""
        for i, time_str in enumerate(times_list):
            if i < len(self.class_time_edits):
                self.class_time_edits[i].setText(time_str)


class SchoolTimeTab(BaseTab):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.editor = ClassTimesEditor(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)

    def load_config(self):
        # 从配置加载数值
        self.editor.morning_count.setValue(self.config_manager.getint("school_time", "morning_count", fallback=4))
        self.editor.afternoon_count.setValue(self.config_manager.getint("school_time", "afternoon_count", fallback=4))
        self.editor.evening_count.setValue(self.config_manager.getint("school_time", "evening_count", fallback=2))
        self.editor.class_duration.setValue(self.config_manager.getint("school_time", "class_duration", fallback=45))
        start_time_str = self.config_manager.get("school_time", "first_class_start", fallback="08:30")
        self.editor.first_class_start.setTime(QTime.fromString(start_time_str, "HH:mm"))

        # 更新课时输入框
        self.editor._update_class_time_inputs()

        # 加载具体的各节课时间
        class_times_str = self.config_manager.get("school_time", "class_times", fallback="")
        if class_times_str:
            times = class_times_str.split(",")
            self.editor.set_class_times_from_list([t.strip() for t in times])

        # 日期
        date_str = self.config_manager.get("semester", "first_monday", fallback="")
        if date_str:
            self.editor.first_monday.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        else:
            self.editor.first_monday.setDate(QDate.currentDate())

    def save_config(self):
        if "school_time" not in self.config_manager:
            self.config_manager["school_time"] = {}
        self.config_manager["school_time"]["morning_count"] = str(self.editor.morning_count.value())
        self.config_manager["school_time"]["afternoon_count"] = str(self.editor.afternoon_count.value())
        self.config_manager["school_time"]["evening_count"] = str(self.editor.evening_count.value())
        self.config_manager["school_time"]["class_duration"] = str(self.editor.class_duration.value())
        self.config_manager["school_time"]["first_class_start"] = self.editor.first_class_start.time().toString("HH:mm")

        class_times = self.editor.get_class_times_list()
        self.config_manager["school_time"]["class_times"] = ",".join(class_times)

        if "semester" not in self.config_manager:
            self.config_manager["semester"] = {}
        self.config_manager["semester"]["first_monday"] = self.editor.first_monday.date().toString("yyyy-MM-dd")