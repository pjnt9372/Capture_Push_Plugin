from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class CourseBlock(QFrame):
    """自定义课表色块"""
    def __init__(self, name, room, teacher, color_hex, is_manual=False):
        super().__init__()
        # 如果是手动添加的课程，使用稍微不同的样式
        if is_manual:
            # 手动添加的课程使用更深的颜色但无边框，仅通过颜色区分
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
        else:
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
        layout.setAlignment(Qt.AlignCenter)  # 确保布局内容居中
        layout.setContentsMargins(4, 6, 4, 6)  # 增加边距以改善视觉效果
        layout.setSpacing(2)  # 增加间距
        
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setContentsMargins(0, 0, 0, 0)  # 确保标签内部没有额外边距
        
        info_text = ""
        if room: info_text += f"@{room}\n"
        if teacher: info_text += f"{teacher}"
        
        info_label = QLabel(info_text.strip())
        info_label.setStyleSheet("font-size: 11px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setContentsMargins(0, 0, 0, 0)  # 确保标签内部没有额外边距
        
        layout.addWidget(name_label)
        layout.addWidget(info_label)
        layout.addStretch()