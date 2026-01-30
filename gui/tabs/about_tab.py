# gui/tabs/about_tab.py
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QGridLayout, QMessageBox
)
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtCore import QUrl, Qt
from .base_tab import BaseTab

# --- 导入所需函数 ---
try:
    from core.log import pack_logs
    from core.updater import Updater
    from core.config_manager import save_config as save_config_manager
except ImportError:
    from log import pack_logs
    from updater import Updater
    from config_manager import save_config as save_config_manager

def get_app_version():
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    version_file = BASE_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"

APP_VERSION = get_app_version()
GITHUB_URL = "https://github.com/pjnt9372/Capture_Push"

class AboutTab(BaseTab):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        title_label = QLabel("Capture_Push")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4;")
        title_label.setAlignment(Qt.AlignCenter)

        version_label = QLabel(f"版本: {APP_VERSION}")
        version_label.setStyleSheet("font-size: 14px; color: #666666;")
        version_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel("课程成绩与课表自动追踪推送系统")
        desc_label.setStyleSheet("font-size: 14px;")
        desc_label.setAlignment(Qt.AlignCenter)

        github_btn = QPushButton("GitHub 项目主页")
        github_btn.setCursor(Qt.PointingHandCursor)
        github_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #0078d4;
                text-decoration: underline;
                background: transparent;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #005a9e;
            }
        """)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))

        # 假设这些功能将由主窗口处理
        self.update_btn = QPushButton("检查更新")
        self.crash_report_btn = QPushButton("崩溃上报")
        self.export_config_btn = QPushButton("导出明文配置")
        self.clear_config_btn = QPushButton("清除现有配置")
        self.repair_btn = QPushButton("修复安装")
        self.developer_options_btn = QPushButton("开发者选项")

        author_label = QLabel(" ")
        author_label.setStyleSheet("font-size: 12px; color: #999999;")
        author_label.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addWidget(desc_label)
        layout.addWidget(github_btn)
        layout.addSpacing(10)

        button_grid = QGridLayout()
        button_grid.setSpacing(10)
        button_grid.addWidget(self.update_btn, 0, 0)
        button_grid.addWidget(self.crash_report_btn, 0, 1)
        button_grid.addWidget(self.export_config_btn, 1, 0)
        button_grid.addWidget(self.clear_config_btn, 1, 1)
        button_grid.addWidget(self.repair_btn, 2, 0)
        button_grid.addWidget(self.developer_options_btn, 2, 1)
        button_grid.setColumnStretch(0, 1)
        button_grid.setColumnStretch(1, 1)
        layout.addLayout(button_grid)

        layout.addSpacing(20)
        layout.addWidget(author_label)
        layout.addStretch()

    def connect_signals(self, parent_window):
        """将按钮信号连接到主窗口的槽函数"""
        self.update_btn.clicked.connect(parent_window.check_for_updates)
        self.crash_report_btn.clicked.connect(parent_window.send_crash_report)
        self.export_config_btn.clicked.connect(parent_window.export_plaintext_config)
        self.clear_config_btn.clicked.connect(parent_window.clear_config)
        self.repair_btn.clicked.connect(parent_window.repair_installation)
        self.developer_options_btn.clicked.connect(parent_window.show_developer_options)

    # AboutTab 不需要 load_config 和 save_config
    def load_config(self):
        pass # AboutTab 不加载配置

    def save_config(self):
        pass # AboutTab 不保存配置