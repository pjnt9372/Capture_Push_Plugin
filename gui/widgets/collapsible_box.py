# gui/widgets/collapsible_box.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolButton
from PySide6.QtCore import Qt, Signal

class CollapsibleBox(QWidget):
    """
    一个可折叠的小组件。
    用于在设置界面中组织配置项。
    """
    # 信号：当折叠状态改变时发出
    state_changed = Signal(bool)

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._is_expanded = False
        self._title = title

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 标题按钮
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet(
            "QToolButton {"
            "    border: none;"
            "    background: #f0f0f0;"
            "    border-radius: 4px;"
            "    padding: 6px;"
            "    font-weight: bold;"
            "    text-align: left;"
            "}"
            "QToolButton::pressed {"
            "    background: #e0e0e0;"
            "}"
        )
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)

        # 内容区域
        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)

        # 将部件添加到主布局
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)

        # 连接信号
        self.toggle_button.clicked.connect(self._on_toggled)

    def _on_toggled(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if not checked else Qt.RightArrow)
        
        if checked:
            self.content_area.setMaximumHeight(16777215) # 最大高度
        else:
            self.content_area.setMaximumHeight(0) # 折叠
        
        self._is_expanded = checked
        self.state_changed.emit(self._is_expanded)

    def set_expanded(self, expanded: bool):
        """设置折叠状态"""
        self.toggle_button.setChecked(expanded)
        # 手动触发一次切换来更新UI
        if self._is_expanded != expanded:
             self._on_toggled()

    def is_expanded(self) -> bool:
        """获取折叠状态"""
        return self._is_expanded

    def setTitle(self, title: str):
        """设置标题文本"""
        self._title = title
        self.toggle_button.setText(title)