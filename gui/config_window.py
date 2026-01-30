# gui/config_window.py

import logging
import os
from typing import Dict

import ctypes
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStatusBar, QMenuBar, QToolBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

# 导入选项卡
from gui.tabs.home_tab import HomeTab
from gui.tabs.basic_tab import BasicTab
from gui.tabs.software_settings_tab import SoftwareSettingsTab
from gui.tabs.school_time_tab import SchoolTimeTab
from gui.tabs.push_tab import PushTab
from gui.tabs.about_tab import AboutTab
from gui.tabs.plugin_management_tab import PluginManagementTab

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
        self.setGeometry(100, 100, 500, 700)
        
        # 设置窗口图标
        try:
            import os
            from pathlib import Path
            import sys
            
            icon_path = None
            
            # 计算资源路径 - 尝试多种可能的路径
            BASE_DIR = Path(__file__).resolve().parent.parent
            possible_paths = [
                BASE_DIR / "resources" / "app_icon.ico",  # 开发环境路径
                Path(sys.prefix) / "resources" / "app_icon.ico",  # 安装环境路径
                Path.cwd() / "resources" / "app_icon.ico",  # 当前工作目录
                Path(sys.executable).parent / "resources" / "app_icon.ico"  # 可执行文件所在目录
            ]
            
            for path in possible_paths:
                if path.exists():
                    icon_path = path
                    break
            
            if icon_path:
                self.setWindowIcon(QIcon(str(icon_path)))
                
                # 在Windows上额外确保任务栏图标正确显示
                if sys.platform == "win32":
                    try:
                        # 使用ctypes设置应用程序组ID，这有助于Windows识别任务栏图标
                        myappid = 'Capture_Push.GUI.1'
                        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                    except Exception as e:
                        logger.error(f"无法设置Windows AppUserModelID: {e}")
        except Exception as e:
            logger.error(f"无法设置主窗口图标: {e}")
        
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

        # Bottom Save Button
        from PySide6.QtWidgets import QPushButton
        self.save_button = QPushButton("保存配置")
        self.save_button.setStyleSheet(
            "QPushButton {"
            "    background-color: #0078d4;"
            "    color: white;"
            "    font-weight: bold;"
            "    padding: 10px;"
            "    font-size: 14px;"
            "}"
            "QPushButton:hover {"
            "    background-color: #005a9e;"
            "}"
            "QPushButton:pressed {"
            "    background-color: #004a87;"
            "}"
        )
        # Connect the save button to the handler
        from gui.utils.button_handlers import handle_save_config_button_clicked
        self.save_button.clicked.connect(lambda: handle_save_config_button_clicked(self))
        layout.addWidget(self.save_button)

        # Create instances of tabs
        self.home_tab = HomeTab(self, self.config_manager)
        self.basic_tab = BasicTab(self, self.config_manager)
        self.software_settings_tab = SoftwareSettingsTab(self, self.config_manager)
        self.school_time_tab = SchoolTimeTab(self, self.config_manager)
        self.push_tab = PushTab(self, self.config_manager)
        self.about_tab = AboutTab(self, self.config_manager)
        self.plugin_management_tab = PluginManagementTab(self, self.config_manager)


        # Add tabs to the tab widget
        self.tab_widget.addTab(self.home_tab, "首页")
        self.tab_widget.addTab(self.basic_tab, "基本配置")
        self.tab_widget.addTab(self.software_settings_tab, "软件设置")
        self.tab_widget.addTab(self.school_time_tab, "学校时间")
        self.tab_widget.addTab(self.push_tab, "推送设置")
        self.tab_widget.addTab(self.plugin_management_tab, "插件管理")
        self.tab_widget.addTab(self.about_tab, "关于")

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)


        # Store references to tab instances for potential use by button handlers
        self.tab_instances: Dict[str, QWidget] = {
            "home": self.home_tab,
            "basic": self.basic_tab,
            "software_settings": self.software_settings_tab,
            "school_time": self.school_time_tab,
            "push": self.push_tab,
            "plugin_management": self.plugin_management_tab,
            "about": self.about_tab,
        }
        
        # Connect signals for AboutTab buttons
        self.about_tab.connect_signals(self)
        
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

    def show_grades_viewer(self):
        logger.info("显示成绩查看器")
        try:
            from .grades_window import GradesViewerWindow
            # 检查是否已存在成绩窗口实例
            if not hasattr(self, '_grades_viewer_window') or self._grades_viewer_window is None:
                self._grades_viewer_window = GradesViewerWindow()
            # 显示窗口
            self._grades_viewer_window.show()
            self._grades_viewer_window.raise_()  # 将窗口置于前台
            self._grades_viewer_window.activateWindow()  # 激活窗口
        except ImportError as e:
            from PySide6.QtWidgets import QMessageBox
            logger.error(f"无法打开成绩查看器：grades_window模块不可用 - {e}")
            QMessageBox.critical(self, "错误", "无法打开成绩查看器：模块不可用")
        except Exception as e:
            logger.error(f"打开成绩查看器时发生错误: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"打开成绩查看器时发生错误: {str(e)}")

    def show_schedule_viewer(self):
        logger.info("显示课表查看器")
        try:
            from .schedule_window import ScheduleViewerWindow
            # 检查是否已存在课表窗口实例
            if not hasattr(self, '_schedule_viewer_window') or self._schedule_viewer_window is None:
                self._schedule_viewer_window = ScheduleViewerWindow()
            # 显示窗口
            self._schedule_viewer_window.show()
            self._schedule_viewer_window.raise_()  # 将窗口置于前台
            self._schedule_viewer_window.activateWindow()  # 激活窗口
        except ImportError as e:
            from PySide6.QtWidgets import QMessageBox
            logger.error(f"无法打开课表查看器：schedule_window模块不可用 - {e}")
            QMessageBox.critical(self, "错误", "无法打开课表查看器：模块不可用")
        except Exception as e:
            logger.error(f"打开课表查看器时发生错误: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"打开课表查看器时发生错误: {str(e)}")

    # Methods for AboutTab buttons
    def check_for_updates(self):
        logger.info("检查更新按钮被点击")
        try:
            from core.updater import Updater
            updater = Updater()
            
            # 从配置中获取是否检测预发布版本的设置
            check_prerelease = self.config_manager.getboolean("update", "check_prerelease", fallback=False)
            
            # 使用正确的检查更新方法
            result = updater.check_update(include_prerelease=check_prerelease)
            if result:
                version, release_data = result
                is_prerelease = release_data.get('prerelease', False)
                
                # 如果有更新，可以弹出对话框询问是否下载
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "发现更新",
                    f"发现新版本 {version}{' (预发布)' if is_prerelease else ''}. 是否立即下载更新？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # 执行下载更新
                    installer_path = updater.download_update(release_data)
                    if installer_path:
                        # 启动安装程序
                        success = updater.install_update(installer_path)
                        if success:
                            from PySide6.QtWidgets import QMessageBox
                            QMessageBox.information(self, "更新", "更新已启动安装！")
                        else:
                            from PySide6.QtWidgets import QMessageBox
                            QMessageBox.critical(self, "错误", "启动安装程序失败！")
                    else:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.critical(self, "错误", "下载更新失败！")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "检查更新", "当前已是最新版本！")
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "无法检查更新：updater模块不可用")
        except Exception as e:
            logger.error(f"检查更新时发生错误: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"检查更新时发生错误: {str(e)}")

    def send_crash_report(self):
        logger.info("崩溃上报按钮被点击")
        try:
            # 提示用户报告中可能包含隐私信息
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "隐私提示",
                "崩溃报告可能包含敏感的系统信息和配置数据。\n您确定要生成并查看这些信息吗？\n请确认您了解其中可能涉及的隐私风险。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                from core.log import pack_logs
                report_path = pack_logs()
                if report_path:
                    QMessageBox.information(self, "成功", f"崩溃报告已生成并保存到桌面: {report_path}\n\n请注意保护您的隐私信息安全。")
                else:
                    QMessageBox.warning(self, "警告", "生成崩溃报告失败")
            else:
                logger.info("用户取消生成崩溃报告")
                QMessageBox.information(self, "取消", "已取消生成崩溃报告。")
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "无法生成崩溃报告：log模块不可用")
        except Exception as e:
            logger.error(f"生成崩溃报告时发生错误: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"生成崩溃报告时发生错误: {str(e)}")

    def export_plaintext_config(self):
        # 代理到现有的按钮处理函数
        from .utils.button_handlers import handle_export_config_button_clicked
        handle_export_config_button_clicked(self)

    def clear_config(self):
        logger.info("清除配置按钮被点击")
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清除所有配置吗？此操作不可逆！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 创建一个空的配置对象
                import configparser
                empty_config = configparser.ConfigParser()
                # 保存空配置（这将加密并覆盖现有配置）
                from core.config_manager import save_config
                save_config(empty_config)
                logger.info("配置已清除")
                QMessageBox.information(self, "成功", "所有配置已清除！")
                # 重新加载UI以反映更改
                self.load_config()
            except Exception as e:
                logger.error(f"清除配置时发生错误: {e}")
                QMessageBox.critical(self, "错误", f"清除配置时发生错误: {str(e)}")

    def repair_installation(self):
        logger.info("修复安装按钮被点击")
        try:
            from core.updater import Updater
            updater = Updater()
            
            # 调用updater中的修复安装方法
            installer_path = updater.repair_installation()
            
            if installer_path:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "确认安装",
                    f"修复包已准备就绪: {installer_path}\n是否立即运行安装程序进行修复？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # 启动安装程序进行修复
                    success = updater.install_update(installer_path, silent=False)
                    if success:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.information(self, "修复", "修复安装已启动！")
                    else:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.critical(self, "错误", "启动安装程序失败！")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "错误", "准备修复包失败！")
        except ImportError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "警告", "无法修复安装：updater模块不可用")
        except Exception as e:
            logger.error(f"修复安装时发生错误: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"修复安装时发生错误: {str(e)}")

    def show_developer_options(self):
        logger.info("开发者选项按钮被点击")
        try:
            # 创建一个简单的对话框来显示开发者选项
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QCheckBox
            dialog = QDialog(self)
            dialog.setWindowTitle("开发者选项")
            layout = QVBoxLayout(dialog)

            # 日志级别选择
            log_layout = QHBoxLayout()
            log_layout.addWidget(QLabel("日志级别:"))
            log_combo = QComboBox()
            log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
            current_log_level = self.config_manager.get("logging", "level", fallback="INFO")
            log_combo.setCurrentText(current_log_level)
            log_layout.addWidget(log_combo)
            layout.addLayout(log_layout)

            # 运行模式选择
            run_layout = QHBoxLayout()
            run_layout.addWidget(QLabel("运行模式:"))
            run_combo = QComboBox()
            run_combo.addItems(["BUILD", "DEV"])
            current_run_model = self.config_manager.get("run_model", "model", fallback="BUILD")
            run_combo.setCurrentText(current_run_model)
            run_layout.addWidget(run_combo)
            layout.addLayout(run_layout)
            
            # 预发布版本检测选项
            prerelease_layout = QHBoxLayout()
            prerelease_checkbox = QCheckBox("检测预发布版本")
            current_prerelease_setting = self.config_manager.getboolean("update", "check_prerelease", fallback=False)
            prerelease_checkbox.setChecked(current_prerelease_setting)
            prerelease_layout.addWidget(prerelease_checkbox)
            prerelease_layout.addStretch()  # 添加伸缩空间，让复选框靠左对齐
            layout.addLayout(prerelease_layout)

            # 按钮
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确定")
            cancel_btn = QPushButton("取消")
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)

            def on_ok_clicked():
                # 更新配置
                if "logging" not in self.config_manager:
                    self.config_manager["logging"] = {}
                if "run_model" not in self.config_manager:
                    self.config_manager["run_model"] = {}
                if "update" not in self.config_manager:
                    self.config_manager["update"] = {}
                
                self.config_manager["logging"]["level"] = log_combo.currentText()
                self.config_manager["run_model"]["model"] = run_combo.currentText()
                self.config_manager["update"]["check_prerelease"] = str(prerelease_checkbox.isChecked())
                
                # 保存配置
                from core.config_manager import save_config
                save_config(self.config_manager)
                
                logger.info(f"日志级别已设置为 {log_combo.currentText()}")
                logger.info(f"运行模式已设置为 {run_combo.currentText()}")
                logger.info(f"预发布版本检测已{'启用' if prerelease_checkbox.isChecked() else '禁用'}")
                
                QMessageBox.information(dialog, "成功", "开发者选项已保存！")
                dialog.accept()

            def on_cancel_clicked():
                dialog.reject()

            ok_btn.clicked.connect(on_ok_clicked)
            cancel_btn.clicked.connect(on_cancel_clicked)

            dialog.exec()
        except Exception as e:
            logger.error(f"显示开发者选项时发生错误: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"显示开发者选项时发生错误: {str(e)}")