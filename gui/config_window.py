# gui/config_window.py

import logging
from typing import Dict

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStatusBar, QMenuBar, QToolBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

# 导入选项卡
from gui.tabs.home_tab import HomeTab
from gui.tabs.basic_tab import BasicTab
from gui.tabs.software_settings_tab import SoftwareSettingsTab
from gui.tabs.school_time_tab import SchoolTimeTab
from gui.tabs.push_tab import PushTab
from gui.tabs.about_tab import AboutTab

from core.config_manager import load_config


# 导入按钮处理函数
from gui.utils.button_handlers import (
    handle_save_config_button_clicked,
    handle_reset_config_button_clicked,
    handle_export_config_button_clicked,
    handle_import_config_button_clicked,
    handle_toggle_autostart_button_clicked
)

logger = logging.getLogger(__name__)

class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push - 配置")
        self.setGeometry(100, 100, 800, 600)
        
        # 初始化配置管理器
        try:
            self.config_manager = load_config()
            logger.info("配置加载成功")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            import configparser
            self.config_manager = configparser.ConfigParser()

        # Central Widget Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Tab Widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create instances of tabs
        self.home_tab = HomeTab(self, self.config_manager)
        self.basic_tab = BasicTab(self, self.config_manager)
        self.software_settings_tab = SoftwareSettingsTab(self, self.config_manager)
        self.school_time_tab = SchoolTimeTab(self, self.config_manager)
        self.push_tab = PushTab(self, self.config_manager)
        self.about_tab = AboutTab(self, self.config_manager)


        # Add tabs to the tab widget
        self.tab_widget.addTab(self.home_tab, "首页")
        self.tab_widget.addTab(self.basic_tab, "基本配置")
        self.tab_widget.addTab(self.software_settings_tab, "软件设置")
        self.tab_widget.addTab(self.school_time_tab, "学校时间")
        self.tab_widget.addTab(self.push_tab, "推送设置")
        self.tab_widget.addTab(self.about_tab, "关于")

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Toolbar (for common actions like Save, Reset, etc.)
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Example actions on toolbar
        save_action = QAction("保存配置", self)
        reset_action = QAction("恢复默认", self)
        export_action = QAction("导出配置", self)
        import_action = QAction("导入配置", self)

        save_action.triggered.connect(lambda: handle_save_config_button_clicked(self))
        reset_action.triggered.connect(lambda: handle_reset_config_button_clicked(self))
        export_action.triggered.connect(lambda: handle_export_config_button_clicked(self))
        import_action.triggered.connect(lambda: handle_import_config_button_clicked(self))

        toolbar.addAction(save_action)
        toolbar.addAction(reset_action)
        toolbar.addAction(export_action)
        toolbar.addAction(import_action)

        # Store references to tab instances for potential use by button handlers
        self.tab_instances: Dict[str, QWidget] = {
            "home": self.home_tab,
            "basic": self.basic_tab,
            "software_settings": self.software_settings_tab,
            "school_time": self.school_time_tab,
            "push": self.push_tab,
            "about": self.about_tab,
        }
        
        self.load_config()

        logger.info("ConfigWindow initialized")


    def load_config(self):
        """Load configuration into all tabs."""
        # This method would typically load the config once and pass it to each tab
        # For now, assuming each tab handles its own loading upon initialization or via a signal
        for tab_instance in self.tab_instances.values():
            if hasattr(tab_instance, 'load_config'):
                tab_instance.load_config()

    def get_all_config_data(self):
        """Collect configuration data from all tabs."""
        all_config_data = {}
        for tab_name, tab_instance in self.tab_instances.items():
            if hasattr(tab_instance, 'get_config_data'):
                all_config_data.update(tab_instance.get_config_data())
        return all_config_data