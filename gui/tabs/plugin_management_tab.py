# -*- coding: utf-8 -*-
"""
插件管理标签页
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from core.plugins.school_plugin_manager import get_plugin_manager


class PluginManagementTab(QWidget):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.plugin_manager = get_plugin_manager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 创建表格
        self.plugin_table = QTableWidget()
        self.plugin_table.setColumnCount(5)  # 院校代码、院校名称、当前版本、最新版本、贡献者
        self.plugin_table.setHorizontalHeaderLabels(['院校代码', '院校名称', '当前版本', '最新版本', '贡献者'])
        header = self.plugin_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # 创建按钮布局
        btn_layout = QHBoxLayout()

        self.refresh_btn = QPushButton('刷新插件列表')
        self.check_update_btn = QPushButton('检查更新')
        self.install_btn = QPushButton('安装插件')
        self.uninstall_btn = QPushButton('卸载插件')

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.check_update_btn)
        btn_layout.addWidget(self.install_btn)
        btn_layout.addWidget(self.uninstall_btn)
        btn_layout.addStretch()

        layout.addWidget(self.plugin_table)
        layout.addLayout(btn_layout)

        # 连接信号
        self.refresh_btn.clicked.connect(self.refresh_plugins)
        self.check_update_btn.clicked.connect(self.check_updates)

    def refresh_plugins(self):
        """刷新插件列表"""
        try:
            available_schools = self.plugin_manager.get_available_plugins()
            
            self.plugin_table.setRowCount(len(available_schools))
            
            for row, (code, name) in enumerate(available_schools.items()):
                # 院校代码
                code_item = QTableWidgetItem(code)
                code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 0, code_item)
                
                # 院校名称
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 1, name_item)
                
                # 当前版本
                current_version = self.plugin_manager._get_local_plugin_version(code)
                current_ver_item = QTableWidgetItem(current_version)
                current_ver_item.setFlags(current_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 2, current_ver_item)
                
                # 最新版本（暂时显示为未知，需要检查更新后才能知道）
                latest_ver_item = QTableWidgetItem('-')
                latest_ver_item.setFlags(latest_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 3, latest_ver_item)
                
                # 贡献者（暂时显示为未知，需要检查更新后才能知道）
                contributor_item = QTableWidgetItem('-')
                contributor_item.setFlags(contributor_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.plugin_table.setItem(row, 4, contributor_item)
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'刷新插件列表失败: {str(e)}')

    def check_updates(self):
        """检查插件更新"""
        try:
            available_schools = self.plugin_manager.get_available_plugins()
            
            for row in range(self.plugin_table.rowCount()):
                code_item = self.plugin_table.item(row, 0)
                if code_item:
                    school_code = code_item.text()
                    
                    # 检查更新
                    update_info = self.plugin_manager.check_plugin_update(school_code)
                    if update_info:
                        latest_version = update_info.get('remote_version', '-')
                        contributor = update_info.get('contributor', 'Unknown')
                    else:
                        # 如果没有更新，使用当前版本作为最新版本显示
                        latest_version = self.plugin_manager._get_local_plugin_version(school_code)
                        contributor = 'Unknown'
                    
                    # 更新最新版本列
                    latest_ver_item = QTableWidgetItem(latest_version)
                    latest_ver_item.setFlags(latest_ver_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.plugin_table.setItem(row, 3, latest_ver_item)
                    
                    # 更新贡献者列
                    contributor_item = QTableWidgetItem(contributor)
                    contributor_item.setFlags(contributor_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.plugin_table.setItem(row, 4, contributor_item)
                    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'检查更新失败: {str(e)}')


class PluginUpdateWorker(QThread):
    """插件更新工作线程"""
    finished = Signal(bool, str)  # 成功标志和消息
    
    def __init__(self, plugin_manager, school_code):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.school_code = school_code
    
    def run(self):
        try:
            # 检查更新
            update_info = self.plugin_manager.check_plugin_update(self.school_code)
            if update_info:
                # 下载并安装更新
                success = self.plugin_manager.download_and_install_plugin(self.school_code, update_info)
                if success:
                    self.finished.emit(True, f'院校 {self.school_code} 插件更新成功')
                else:
                    self.finished.emit(False, f'院校 {self.school_code} 插件更新失败')
            else:
                self.finished.emit(True, f'院校 {self.school_code} 插件已是最新版本')
        except Exception as e:
            self.finished.emit(False, f'更新过程中发生错误: {str(e)}')