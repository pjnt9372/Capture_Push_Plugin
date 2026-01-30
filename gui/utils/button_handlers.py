# gui/utils/button_handlers.py

import logging
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QMessageBox, QFileDialog, QPushButton,
    QCheckBox, QLineEdit, QSpinBox, QTextEdit, QGroupBox,
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QScrollArea, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QPixmap, QIcon

from core.config_manager import load_config, save_config
# from core.config import default_config # core 中目前没有此模块
default_config = {} # 临时占位

from core.utils.dpapi import encrypt_file, decrypt_file_to_str
from core.utils.windows_auth import verify_user_credentials
# from core.utils.network import send_test_email, fetch_school_times, fetch_school_list # 模块尚未创建
from core.utils.registry import set_autostart
# from core.utils.validation import validate_email # 模块尚未创建

def send_test_email(*args, **kwargs): return False, "Module not implemented"
def fetch_school_times(*args, **kwargs): return []
def fetch_school_list(*args, **kwargs): return []
def validate_email(email): return "@" in email


from gui.widgets.collapsible_box import CollapsibleBox
from gui.tabs.base_tab import BaseTab # 导入选项卡基类


def verify_with_school_password(parent_window):
    """
    使用教务系统密码进行验证
    Args:
        parent_window: 父窗口实例
    Returns:
        bool: 验证是否成功
    """
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    from core.config_manager import load_config
    
    try:
        # 从配置中获取教务系统用户名和密码
        config = load_config()
        
        # 尝试获取教务系统登录凭据
        username = config.get('account', 'username', fallback='')
        password = config.get('account', 'password', fallback='')
        
        if not username or not password:
            logger.warning("配置中缺少教务系统登录凭据")
            return False
        
        # 弹出输入对话框让用户输入教务系统密码
        entered_password, ok = QInputDialog.getText(
            parent_window,
            "教务系统验证",
            f"请输入用户 {username} 的教务系统密码进行验证:\n(用于确认身份以导出配置)",
            echo=QLineEdit.Password
        )
        
        if ok and entered_password:
            # 验证输入的密码是否与配置中的密码匹配
            if entered_password == password:
                logger.info("教务系统密码验证成功")
                return True
            else:
                logger.info("教务系统密码验证失败")
                QMessageBox.warning(parent_window, "验证失败", "教务系统密码不正确！")
                return False
        else:
            logger.info("用户取消了教务系统密码验证")
            return False
            
    except Exception as e:
        logger.error(f"教务系统密码验证过程中发生错误: {e}")
        return False

logger = logging.getLogger(__name__)

# --- 通用按钮处理函数 ---

def handle_save_config_button_clicked(config_window_instance):
    """
    处理“保存配置”按钮的点击事件。
    Args:
        config_window_instance (ConfigWindow): 主窗口实例，用于获取所有选项卡的数据。
    """
    logger.info("保存配置按钮被点击")
    try:
        # 通知所有选项卡将其数据保存到 config_manager
        for tab_instance in config_window_instance.tab_instances.values():
            if hasattr(tab_instance, 'save_config'):
                tab_instance.save_config()

        # 使用 core.config_manager.save_config 保存加密后的配置
        save_config(config_window_instance.config_manager)
        logger.info("配置已保存并加密")
        QMessageBox.information(config_window_instance, "成功", "配置已保存！")


    except Exception as e:
        logger.error(f"处理保存配置时发生错误: {e}")
        QMessageBox.critical(config_window_instance, "错误", f"保存配置时发生错误: {str(e)}")

def handle_reset_config_button_clicked(config_window_instance):
    """
    处理“恢复默认”按钮的点击事件。
    Args:
        config_window_instance (ConfigWindow): 主窗口实例。
    """
    reply = QMessageBox.question(
        config_window_instance,
        "确认",
        "确定要恢复默认设置吗？所有当前配置将丢失。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    if reply == QMessageBox.StandardButton.Yes:
        try:
            # 加载默认配置并保存
            save_config(default_config)
            # 通知所有选项卡刷新UI
            for tab_instance in config_window_instance.tab_instances.values():
                 if hasattr(tab_instance, 'load_config'): # 假设选项卡有load_config方法
                     tab_instance.load_config()
            logger.info("配置已恢复默认")
            QMessageBox.information(config_window_instance, "成功", "已恢复默认配置！")
        except Exception as e:
            logger.error(f"恢复默认配置时发生错误: {e}")
            QMessageBox.critical(config_window_instance, "错误", f"恢复默认配置时发生错误: {str(e)}")

def handle_export_config_button_clicked(config_window_instance):
    """
    处理“导出明文配置”按钮的点击事件。
    首先尝试 Windows Hello 认证，如果不可用则使用教务系统密码验证。
    Args:
        config_window_instance (ConfigWindow): 主窗口实例。
    """
    logger.info("导出配置按钮被点击")
    try:
        # 1. 首先进行 Windows Hello 验证
        from core.utils.windows_auth import verify_user_credentials
        if not verify_user_credentials():
            logger.warning("Windows 身份验证未通过或已取消，无法导出配置。")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(config_window_instance, "验证取消", "Windows 身份验证未通过或已取消，无法导出配置。")
            logger.info("Windows 身份验证未通过或已取消。")
            return

        logger.info("Windows 身份验证成功。")

        # 2. 验证通过，执行导出逻辑
        # 选择文件路径并导出
        file_path, _ = QFileDialog.getSaveFileName(
            config_window_instance,
            "导出明文配置",
            "config_plaintext.ini",
            "INI Files (*.ini);;All Files (*)"
        )
        
        if not file_path:
            logger.info("用户取消了文件保存")
            return

        # 加载当前加密配置字典
        from core.config_manager import load_config
        import configparser
        
        current_config = load_config()
        
        # 创建新的 ConfigParser 来保存明文
        plaintext_cfg = configparser.ConfigParser()
        
        # 遍历并填入数据
        for section, options in current_config.items():
            # 修复 'DEFAULT' 导致的 Invalid section name 错误
            if section.upper() == 'DEFAULT':
                # DEFAULT 节在 ConfigParser 中是内置的，直接写入 options
                for key, value in options.items():
                    plaintext_cfg.set('DEFAULT', key, str(value))
            else:
                # 普通节：如果不存在则创建
                if not plaintext_cfg.has_section(section):
                    plaintext_cfg.add_section(section)
                for key, value in options.items():
                    plaintext_cfg.set(section, key, str(value))
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            plaintext_cfg.write(f)
            
        logger.info(f"配置成功导出至: {file_path}")
        QMessageBox.information(config_window_instance, "成功", f"明文配置已导出至：\n{file_path}\n\n请注意：此文件包含明文密码，请妥善保管！")

    except Exception as e:
        logger.error(f"导出过程中发生错误: {e}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(config_window_instance, "导出失败", f"导出过程中发生错误：\n{str(e)}")
        logger.error(f"导出明文配置失败: {e}")
        import traceback
        traceback.print_exc()

def handle_import_config_button_clicked(config_window_instance):
    """
    处理“导入配置”按钮的点击事件。
    触发 Windows Hello 认证。
    Args:
        config_window_instance (ConfigWindow): 主窗口实例。
    """
    logger.info("导入配置按钮被点击")
    try:
        auth_success = verify_user_credentials()

        if auth_success:
            logger.info("Windows Hello 认证成功")
            file_path, _ = QFileDialog.getOpenFileName(
                config_window_instance,
                "导入配置",
                "",
                "INI Files (*.ini);;All Files (*)"
            )
            if file_path:
                # Read the INI file directly using configparser
                imported_config = configparser.ConfigParser()
                imported_config.read(file_path, encoding='utf-8')
                # 保存导入的配置（会自动加密）
                save_config(imported_config)
                # 通知所有选项卡刷新UI
                for tab_instance in config_window_instance.tab_instances.values():
                    if hasattr(tab_instance, 'load_config'):
                        tab_instance.load_config()
                logger.info(f"配置已从 {file_path} 导入")
                QMessageBox.information(config_window_instance, "成功", f"配置已从 {file_path} 导入！")
        else:
            logger.info("Windows Hello 认证失败或被取消")
            QMessageBox.warning(config_window_instance, "认证失败", "无法导入配置：认证未通过。")

    except Exception as e:
        logger.error(f"处理导入配置时发生错误: {e}")
        QMessageBox.critical(config_window_instance, "错误", f"导入配置时发生错误: {str(e)}")

def handle_toggle_autostart_button_clicked(config_window_instance, autostart_checkbox: QCheckBox):
    """
    处理“开机自启”复选框状态改变的事件。
    Args:
        config_window_instance (ConfigWindow): 主窗口实例。
        autostart_checkbox (QCheckBox): 开机自启复选框。
    """
    enabled = autostart_checkbox.isChecked()
    logger.info(f"开机自启按钮被点击，状态: {enabled}")
    try:
        set_autostart(enabled)
        logger.info(f"开机自启设置已{'启用' if enabled else '禁用'}")
        # 状态栏提示
        config_window_instance.status_bar.showMessage(f"开机自启 {'已启用' if enabled else '已禁用'}", 2000)
    except Exception as e:
        logger.error(f"设置开机自启时发生错误: {e}")
        QMessageBox.critical(config_window_instance, "错误", f"设置开机自启时发生错误: {str(e)}")
        # 还原复选框状态
        autostart_checkbox.setChecked(not enabled)


# --- 各选项卡专属的按钮处理函数 ---

# Home Tab
def handle_refresh_grades(config_manager, parent_window):
    """处理“刷新成绩”按钮点击事件"""
    logger.info("刷新成绩按钮被点击")
    try:
        import sys
        import subprocess
        from pathlib import Path
        
        # 获取当前执行文件的目录
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        go_script = str(BASE_DIR / "core" / "go.py")
        
        # 获取 pythonw.exe 路径
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "pythonw.exe").exists():
            py_exe = str(exe_dir / "pythonw.exe")
        else:
            py_exe = sys.executable
        
        logger.info("正在运行成绩刷新脚本...")
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen([py_exe, go_script, "--fetch-grade", "--force"], 
                        creationflags=CREATE_NO_WINDOW).wait()
        
        QMessageBox.information(parent_window, "成功", "成绩数据已开始刷新！")
        logger.info("成绩数据刷新已启动")
    except Exception as e:
        logger.error(f"刷新成绩时发生错误: {e}")
        QMessageBox.critical(parent_window, "错误", f"刷新成绩失败:\n{str(e)}")

def handle_refresh_schedule(config_manager, parent_window):
    """处理“刷新课表”按钮点击事件"""
    logger.info("刷新课表按钮被点击")
    try:
        import sys
        import subprocess
        from pathlib import Path
        
        # 获取当前执行文件的目录
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        go_script = str(BASE_DIR / "core" / "go.py")
        
        # 获取 pythonw.exe 路径
        exe_dir = Path(sys.executable).parent
        if (exe_dir / "pythonw.exe").exists():
            py_exe = str(exe_dir / "pythonw.exe")
        else:
            py_exe = sys.executable
        
        logger.info("正在运行课表刷新脚本...")
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen([py_exe, go_script, "--fetch-schedule", "--force"], 
                        creationflags=CREATE_NO_WINDOW).wait()
        
        QMessageBox.information(parent_window, "成功", "课表数据已开始刷新！")
        logger.info("课表数据刷新已启动")
    except Exception as e:
        logger.error(f"刷新课表时发生错误: {e}")
        QMessageBox.critical(parent_window, "错误", f"刷新课表失败:\n{str(e)}")

def handle_import_plaintext_config(parent_window, config_manager):
    """处理“导入明文配置”按钮点击事件"""
    logger.info("导入明文配置按钮被点击")
    try:
        # 1. 尝试调用Windows Hello认证
        from core.utils.windows_auth import verify_user_credentials
        auth_success = verify_user_credentials()

        if auth_success:
            logger.info("Windows Hello 认证成功")
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            import configparser
            
            file_path, _ = QFileDialog.getOpenFileName(
                parent_window,
                "导入明文配置",
                "",
                "INI Files (*.ini);;All Files (*)"
            )
            if file_path:
                # Read the INI file directly using configparser
                imported_config = configparser.ConfigParser()
                imported_config.read(file_path, encoding='utf-8')
                # 保存导入的配置（会自动加密）
                from core.config_manager import save_config
                save_config(imported_config)
                # 通知所有选项卡刷新UI
                for tab_instance in parent_window.tab_instances.values():
                    if hasattr(tab_instance, 'load_config'):
                        tab_instance.load_config()
                logger.info(f"配置已从 {file_path} 导入")
                QMessageBox.information(parent_window, "成功", f"配置已从 {file_path} 导入！")
        else:
            logger.info("Windows Hello 认证失败或被取消")
            QMessageBox.warning(parent_window, "认证失败", "无法导入配置：认证未通过。")

    except Exception as e:
        logger.error(f"处理导入明文配置时发生错误: {e}")
        QMessageBox.critical(parent_window, "错误", f"导入明文配置时发生错误: {str(e)}")

def handle_check_update_clicked(home_tab_instance):

    """处理“检查更新”按钮点击事件"""
    # 实现检查更新逻辑
    logger.info("检查更新按钮被点击")
    # ... (更新检查逻辑) ...
    QMessageBox.information(home_tab_instance, "提示", "正在检查更新... (功能待实现)")

def handle_launch_main_app_clicked(home_tab_instance):
    """处理“启动主程序”按钮点击事件"""
    # 实现启动主程序逻辑
    logger.info("启动主程序按钮被点击")
    # ... (启动逻辑) ...
    QMessageBox.information(home_tab_instance, "提示", "启动主程序... (功能待实现)")


# Basic Tab
def handle_test_email_clicked(basic_tab_instance):
    """处理“测试邮箱”按钮点击事件"""
    logger.info("测试邮箱按钮被点击")
    email = basic_tab_instance.email_input.text()
    password = basic_tab_instance.password_input.text()
    smtp_server = basic_tab_instance.smtp_input.text()
    smtp_port = basic_tab_instance.smtp_port_input.value()
    recipient = basic_tab_instance.recipient_input.text()

    if not validate_email(email) or not validate_email(recipient):
        QMessageBox.warning(basic_tab_instance, "输入错误", "请输入有效的邮箱地址。")
        return

    # 在后台线程中发送邮件，避免阻塞UI
    worker_thread = QThread()
    worker = TestEmailWorker(email, password, smtp_server, smtp_port, recipient)
    worker.moveToThread(worker_thread)

    worker.finished.connect(lambda success, msg: on_test_email_finished(basic_tab_instance, success, msg))
    worker_thread.started.connect(worker.run)
    worker_thread.start()

    # 临时禁用按钮
    basic_tab_instance.test_email_button.setEnabled(False)

def on_test_email_finished(basic_tab_instance, success, message):
    """处理测试邮件完成后的UI更新"""
    basic_tab_instance.test_email_button.setEnabled(True)
    if success:
        QMessageBox.information(basic_tab_instance, "成功", f"测试邮件发送成功: {message}")
    else:
        QMessageBox.critical(basic_tab_instance, "失败", f"测试邮件发送失败: {message}")

class TestEmailWorker(QObject):
    finished = Signal(bool, str) # 信号：success, message

    def __init__(self, sender_email, sender_password, smtp_server, smtp_port, recipient_email):
        super().__init__()
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.recipient_email = recipient_email

    def run(self):
        try:
            success, message = send_test_email(
                self.sender_email, self.sender_password,
                self.smtp_server, self.smtp_port, self.recipient_email
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))

# Push Tab
def handle_refresh_schools_clicked(push_tab_instance):
    """处理“刷新学校”按钮点击事件"""
    logger.info("刷新学校按钮被点击")
    # 在后台线程中获取学校列表
    worker_thread = QThread()
    worker = FetchSchoolsWorker()
    worker.moveToThread(worker_thread)

    worker.finished.connect(lambda schools: on_schools_fetched(push_tab_instance, schools))
    worker_thread.started.connect(worker.run)
    worker_thread.start()

    push_tab_instance.refresh_schools_button.setEnabled(False) # 临时禁用按钮

def on_schools_fetched(push_tab_instance, schools):
    """处理获取学校列表完成后的UI更新"""
    push_tab_instance.refresh_schools_button.setEnabled(True)
    if schools:
        push_tab_instance.school_combo.clear()
        push_tab_instance.school_combo.addItems(schools)
        QMessageBox.information(push_tab_instance, "成功", f"获取到 {len(schools)} 所学校。")
    else:
        QMessageBox.warning(push_tab_instance, "警告", "未能获取学校列表。")

class FetchSchoolsWorker(QObject):
    finished = Signal(list) # 信号：schools_list

    def run(self):
        try:
            schools = fetch_school_list() # 假设此函数已实现
            self.finished.emit(schools)
        except Exception as e:
            logger.error(f"获取学校列表失败: {e}")
            self.finished.emit([])

def handle_fetch_class_times_clicked(push_tab_instance):
    """处理“获取课时”按钮点击事件"""
    school_id = push_tab_instance.school_combo.currentData() # 假设 combo 存储 ID
    if not school_id:
        QMessageBox.warning(push_tab_instance, "警告", "请选择一所学校。")
        return

    logger.info(f"获取课时按钮被点击，学校ID: {school_id}")
    # 在后台线程中获取课时
    worker_thread = QThread()
    worker = FetchClassTimesWorker(school_id)
    worker.moveToThread(worker_thread)

    worker.finished.connect(lambda times: on_class_times_fetched(push_tab_instance, times))
    worker_thread.started.connect(worker.run)
    worker_thread.start()

    push_tab_instance.fetch_class_times_button.setEnabled(False) # 临时禁用按钮

def on_class_times_fetched(push_tab_instance, times):
    """处理获取课时完成后的UI更新"""
    push_tab_instance.fetch_class_times_button.setEnabled(True)
    if times:
        # 清空现有的课时设置组件
        for widget in push_tab_instance.class_time_widgets:
            push_tab_instance.class_time_layout.removeWidget(widget)
            widget.setParent(None)
        push_tab_instance.class_time_widgets.clear()

        # 创建新的课时设置组件
        for idx, time_info in enumerate(times):
            # 假设 time_info 是一个包含 start_time, end_time, name 等信息的字典
            collapsible_box = CollapsibleBox(title=time_info.get('name', f'课时 {idx+1}'))
            layout_content = QVBoxLayout()

            start_edit = QLineEdit(time_info.get('start_time', ''))
            end_edit = QLineEdit(time_info.get('end_time', ''))
            # ... 添加其他控件 ...

            layout_content.addWidget(QLabel("开始时间:"))
            layout_content.addWidget(start_edit)
            layout_content.addWidget(QLabel("结束时间:"))
            layout_content.addWidget(end_edit)
            # ... 添加其他控件到 layout_content ...

            collapsible_box.setContentLayout(layout_content)
            push_tab_instance.class_time_layout.addWidget(collapsible_box)
            push_tab_instance.class_time_widgets.append(collapsible_box)
        QMessageBox.information(push_tab_instance, "成功", f"获取到 {len(times)} 个课时。")
    else:
        QMessageBox.warning(push_tab_instance, "警告", "未能获取课时信息。")