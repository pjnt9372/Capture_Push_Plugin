from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt

class CourseEditDialog(QWidget):
    """手动编辑/添加课程的对话框"""
    def __init__(self, parent=None, data=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("编辑课程")
        self.setFixedSize(400, 400) # 增大尺寸
        self.data = data or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.data.get("课程名称", ""))
        self.room_edit = QLineEdit(self.data.get("教室", ""))
        self.teacher_edit = QLineEdit(self.data.get("教师", ""))
        self.weeks_edit = QLineEdit(self.data.get("上课周次", "1-20"))
        # 优化提示文字
        self.weeks_edit.setPlaceholderText("提示：1-16 (连续) 或 1,3,5 (单周)")
        
        # 允许用户指定持续节数
        self.span_spin = QSpinBox()
        self.span_spin.setRange(1, 4)
        self.span_spin.setValue(self.data.get("row_span", 1))

        form.addRow("课程名称:", self.name_edit)
        form.addRow("教室:", self.room_edit)
        form.addRow("教师:", self.teacher_edit)
        form.addRow("上课周次:", self.weeks_edit)
        form.addRow("持续节数:", self.span_spin)
        
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("确定")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def parse_weeks(self, weeks_str):
        """解析周次字符串为列表"""
        weeks = set()
        try:
            parts = weeks_str.replace("，", ",").split(",")
            for part in parts:
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    weeks.update(range(start, end + 1))
                elif part.strip():
                    weeks.add(int(part.strip()))
        except:
            pass
        return sorted(list(weeks))

    def accept(self):
        weeks_str = self.weeks_edit.text()
        weeks_list = self.parse_weeks(weeks_str)
        
        self.result = {
            "课程名称": self.name_edit.text(),
            "教室": self.room_edit.text(),
            "教师": self.teacher_edit.text(),
            "上课周次": weeks_str,
            "周次列表": weeks_list,
            "row_span": self.span_spin.value(),
            "is_manual": True
        }
        self.parent().on_dialog_finished(self.result)
        self.close()
