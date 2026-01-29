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
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont, QPixmap, QIcon

from core.config_manager import load_config, save_config
# from core.config import default_config # core 中目前没有此模块
default_config = {} # 临时占位

from core.utils.dpapi import encrypt_file, decrypt_file_to_str
from core.utils.windows_auth import verify_user_credentials
# from core.utils.network import send_test_email, fetch_school_times, fetch_school_list # 模块尚未创建
# from core.utils.registry import set_autostart # 模块尚未创建
# from core.utils.validation import validate_email # 模块尚未创建

def send_test_email(*args, **kwargs): return False, "Module not implemented"
def fetch_school_times(*args, **kwargs): return []
def fetch_school_list(*args, **kwargs): return []
def set_autostart(*args, **kwargs): pass
def validate_email(email): return "@" in email


from gui.widgets.collapsible_box import CollapsibleBox
from gui.tabs.base_tab import BaseTab # 导入选项卡基类

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
    触发 Windows Hello 认证。
    Args:
        config_window_instance (ConfigWindow): 主窗口实例。
    """
    logger.info("导出配置按钮被点击")
    try:
        # 1. 尝试调用Windows Hello认证
        auth_success = verify_user_credentials()

        if auth_success:
            logger.info("Windows Hello 认证成功")
            # 2. 认证成功后，选择文件路径并导出
            file_path, _ = QFileDialog.getSaveFileName(
                config_window_instance,
                "导出配置",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            if file_path:
                encrypted_path = Path("config.json.enc") # 假设加密文件路径
                if encrypted_path.exists():
                    plaintext_config = decrypt_file_to_str(str(encrypted_path))
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(plaintext_config)
                    logger.info(f"配置已导出到: {file_path}")
                    QMessageBox.information(config_window_instance, "成功", f"配置已导出到: {file_path}")
                else:
                    logger.warning("加密配置文件不存在，无法导出")
                    QMessageBox.warning(config_window_instance, "警告", "找不到加密配置文件，无法导出。")
        else:
            logger.info("Windows Hello 认证失败或被取消")
            QMessageBox.warning(config_window_instance, "认证失败", "无法导出配置：认证未通过。")

    except Exception as e:
        logger.error(f"处理导出配置时发生错误: {e}")
        QMessageBox.critical(config_window_instance, "错误", f"导出配置时发生错误: {str(e)}")

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
                "JSON Files (*.json);;All Files (*)"
            )
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)
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
    QMessageBox.information(parent_window, "提示", "正在刷新成绩... (功能待实现)")

def handle_refresh_schedule(config_manager, parent_window):
    """处理“刷新课表”按钮点击事件"""
    logger.info("刷新课表按钮被点击")
    QMessageBox.information(parent_window, "提示", "正在刷新课表... (功能待实现)")

def handle_import_plaintext_config(parent_window, config_manager):
    """处理“导入明文配置”按钮点击事件"""
    logger.info("导入明文配置按钮被点击")
    QMessageBox.information(parent_window, "提示", "正在导入明文配置... (功能待实现)")

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