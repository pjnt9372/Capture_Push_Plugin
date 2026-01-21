from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class CourseBlock(QFrame):
    """自定义课表色块"""
    def __init__(self, name, room, teacher, color_hex):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color_hex};
                border-radius: 6px;
                margin: 1px;
            }}
            QLabel {{
                color: black;
                background: transparent;
                font-family: "Microsoft YaHei";
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(1)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        
        info_text = ""
        if room: info_text += f"@{room}\n"
        if teacher: info_text += f"{teacher}"
        
        info_label = QLabel(info_text.strip())
        info_label.setStyleSheet("font-size: 11px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(name_label)
        layout.addWidget(info_label)
        layout.addStretch()
