# gui/tabs/basic_tab.py
from PySide6.QtWidgets import QVBoxLayout, QFormLayout, QComboBox, QLineEdit
from .base_tab import BaseTab
from ..widgets.collapsible_box import CollapsibleBox

from core.school import get_available_schools

class BasicTab(BaseTab):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.school_combo = QComboBox()
        self.available_schools = get_available_schools()
        for code, name in self.available_schools.items():
            self.school_combo.addItem(name, code)
        # 占位符处理在 load_config 中

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("选择院校", self.school_combo)
        form.addRow("学号", self.username)
        form.addRow("密码", self.password)

        layout.addLayout(form)
        layout.addStretch()

    def load_config(self):
        # 加载学校代码
        saved_school_code = self.config_manager.get("account", "school_code", fallback="")
        
        # 如果已保存学校代码且不是占位符，则设置为该学校
        if saved_school_code and saved_school_code != "12345":
            saved_index = self.school_combo.findData(saved_school_code)
            if saved_index >= 0:
                self.school_combo.setCurrentIndex(saved_index)
            else:
                # 如果保存的学校代码不存在于列表中，则显示占位符
                placeholder_index = self.school_combo.findData("12345")
                if placeholder_index >= 0:
                    self.school_combo.setCurrentIndex(placeholder_index)
        else:
            # 否则显示占位符
            placeholder_index = self.school_combo.findData("12345")
            if placeholder_index >= 0:
                self.school_combo.setCurrentIndex(placeholder_index)
        
        # 加载其他账户信息
        self.username.setText(self.config_manager.get("account", "username", fallback=""))
        self.password.setText(self.config_manager.get("account", "password", fallback=""))

    def save_config(self):
        if "account" not in self.config_manager:
            self.config_manager["account"] = {}
        self.config_manager["account"]["school_code"] = self.school_combo.currentData()
        self.config_manager["account"]["username"] = self.username.text()
        self.config_manager["account"]["password"] = self.password.text()