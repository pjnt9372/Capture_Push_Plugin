# gui/tabs/home_tab.py
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QGroupBox, QHBoxLayout, QMessageBox, QApplication
)
from PySide6.QtCore import Qt

from .base_tab import BaseTab
from ..utils.button_handlers import (
    handle_refresh_grades, handle_refresh_schedule, handle_import_plaintext_config
)

class HomeTab(BaseTab):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.parent_window = parent # 保存对主窗口的引用
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel("Capture_Push 首页")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4; margin: 20px 0 20px 0;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        features_group = QGroupBox("功能")
        features_layout = QVBoxLayout(features_group)

        self.refresh_grades_btn = QPushButton("刷新成绩")
        self.refresh_grades_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
        self.refresh_grades_btn.clicked.connect(self._refresh_grades_wrapper)

        self.refresh_schedule_btn = QPushButton("刷新课表")
        self.refresh_schedule_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
        self.refresh_schedule_btn.clicked.connect(self._refresh_schedule_wrapper)

        self.view_grades_btn = QPushButton("查看成绩")
        self.view_grades_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.view_grades_btn.clicked.connect(self._show_grades_viewer_wrapper)

        self.view_schedule_btn = QPushButton("查看课表")
        self.view_schedule_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.view_schedule_btn.clicked.connect(self._show_schedule_viewer_wrapper)

        self.import_config_btn = QPushButton("导入明文配置")
        self.import_config_btn.setStyleSheet("background-color: #ffc107; color: #212529; font-weight: bold; padding: 10px;")
        self.import_config_btn.clicked.connect(self._import_config_wrapper)

        features_layout.addWidget(self.refresh_grades_btn)
        features_layout.addWidget(self.refresh_schedule_btn)
        features_layout.addWidget(self.view_grades_btn)
        features_layout.addWidget(self.view_schedule_btn)
        features_layout.addWidget(self.import_config_btn)

        layout.addWidget(features_group)
        layout.addStretch()

    def _set_button_pressed_style(self, button, pressed=True):
        if pressed:
            button.setStyleSheet(
                "QPushButton { "
                "background-color: #005a9e; "
                "color: white; "
                "font-weight: bold; "
                "padding: 10px; "
                "border: 2px solid #004a87; "
                "border-radius: 4px; "
                "box-shadow: inset 0 2px 4px rgba(0,0,0,0.3); "
                "}"
            )
        else:
            if button == self.refresh_grades_btn:
                button.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
            elif button == self.refresh_schedule_btn:
                button.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; padding: 10px;")
            elif button == self.view_grades_btn:
                button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
            elif button == self.view_schedule_btn:
                button.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
            elif button == self.import_config_btn:
                button.setStyleSheet("background-color: #ffc107; color: #212529; font-weight: bold; padding: 10px;")

    def _refresh_grades_wrapper(self):
        self._set_button_pressed_style(self.refresh_grades_btn, pressed=True)
        QApplication.processEvents()
        try:
            handle_refresh_grades(self.config_manager, self.parent_window)
        finally:
            self._set_button_pressed_style(self.refresh_grades_btn, pressed=False)

    def _refresh_schedule_wrapper(self):
        self._set_button_pressed_style(self.refresh_schedule_btn, pressed=True)
        QApplication.processEvents()
        try:
            handle_refresh_schedule(self.config_manager, self.parent_window)
        finally:
            self._set_button_pressed_style(self.refresh_schedule_btn, pressed=False)

    def _show_grades_viewer_wrapper(self):
        self._set_button_pressed_style(self.view_grades_btn, pressed=True)
        QApplication.processEvents()
        try:
            self.parent_window.show_grades_viewer()
        finally:
            self._set_button_pressed_style(self.view_grades_btn, pressed=False)

    def _show_schedule_viewer_wrapper(self):
        self._set_button_pressed_style(self.view_schedule_btn, pressed=True)
        QApplication.processEvents()
        try:
            self.parent_window.show_schedule_viewer()
        finally:
            self._set_button_pressed_style(self.view_schedule_btn, pressed=False)

    def _import_config_wrapper(self):
        self._set_button_pressed_style(self.import_config_btn, pressed=True)
        QApplication.processEvents()
        try:
            handle_import_plaintext_config(self.parent_window, self.config_manager)
        finally:
            self._set_button_pressed_style(self.import_config_btn, pressed=False)

    def load_config(self):
        # HomeTab 不加载配置
        pass

    def save_config(self):
        # HomeTab 不保存配置
        pass