# gui/tabs/push_tab.py
from PySide6.QtWidgets import (
    QVBoxLayout, QGroupBox, QVBoxLayout as VBox, QRadioButton, QButtonGroup,
    QFormLayout, QLineEdit
)
from .base_tab import BaseTab
from ..widgets.collapsible_box import CollapsibleBox

class PushTab(BaseTab):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent, config_manager)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 推送方式
        method_group = QGroupBox("推送方式 (单选)")
        method_layout = VBox(method_group)
        self.push_button_group = QButtonGroup(self)
        self.push_none_radio = QRadioButton("不启用推送")
        self.push_email_radio = QRadioButton("邮件推送")
        self.push_feishu_radio = QRadioButton("飞书机器人推送")
        self.push_serverchan_radio = QRadioButton("Server酱推送")

        self.push_button_group.addButton(self.push_none_radio, 0)
        self.push_button_group.addButton(self.push_email_radio, 1)
        self.push_button_group.addButton(self.push_feishu_radio, 2)
        self.push_button_group.addButton(self.push_serverchan_radio, 3)

        method_layout.addWidget(self.push_none_radio)
        method_layout.addWidget(self.push_email_radio)
        method_layout.addWidget(self.push_feishu_radio)
        method_layout.addWidget(self.push_serverchan_radio)
        layout.addWidget(method_group)

        # 邮件配置（可折叠）
        self.email_collapsible = CollapsibleBox("邮件配置")
        email_form = QFormLayout(self.email_collapsible.content_area)
        self.smtp = QLineEdit()
        self.port = QLineEdit()
        self.sender = QLineEdit()
        self.receiver = QLineEdit()
        self.auth = QLineEdit()
        self.auth.setEchoMode(QLineEdit.Password)
        email_form.addRow("SMTP服务器", self.smtp)
        email_form.addRow("端口", self.port)
        email_form.addRow("发件邮箱", self.sender)
        email_form.addRow("收件邮箱", self.receiver)
        email_form.addRow("授权码", self.auth)
        layout.addWidget(self.email_collapsible)

        # 飞书配置（可折叠）
        self.feishu_collapsible = CollapsibleBox("飞书机器人配置")
        feishu_form = QFormLayout(self.feishu_collapsible.content_area)
        self.feishu_webhook = QLineEdit()
        self.feishu_webhook.setEchoMode(QLineEdit.Password)
        self.feishu_secret = QLineEdit()
        self.feishu_secret.setEchoMode(QLineEdit.Password)
        feishu_form.addRow("Webhook URL", self.feishu_webhook)
        feishu_form.addRow("密钥 (启用签名校验)", self.feishu_secret)
        layout.addWidget(self.feishu_collapsible)

        # Server酱配置（可折叠）
        self.serverchan_collapsible = CollapsibleBox("Server酱配置")
        serverchan_form = QFormLayout(self.serverchan_collapsible.content_area)
        self.serverchan_sendkey = QLineEdit()
        serverchan_form.addRow("SendKey", self.serverchan_sendkey)
        layout.addWidget(self.serverchan_collapsible)

        layout.addStretch()

    def load_config(self):
        # 推送方式
        method = self.config_manager.get("push", "method", fallback="none").lower()
        if method == "email":
            self.push_email_radio.setChecked(True)
        elif method == "feishu":
            self.push_feishu_radio.setChecked(True)
        elif method == "serverchan":
            self.push_serverchan_radio.setChecked(True)
        else:
            self.push_none_radio.setChecked(True)

        # 详细配置
        self.smtp.setText(self.config_manager.get("email", "smtp", fallback=""))
        self.port.setText(self.config_manager.get("email", "port", fallback=""))
        self.sender.setText(self.config_manager.get("email", "sender", fallback=""))
        self.receiver.setText(self.config_manager.get("email", "receiver", fallback=""))
        self.auth.setText(self.config_manager.get("email", "auth", fallback=""))
        self.feishu_webhook.setText(self.config_manager.get("feishu", "webhook_url", fallback=""))
        self.feishu_secret.setText(self.config_manager.get("feishu", "secret", fallback=""))
        self.serverchan_sendkey.setText(self.config_manager.get("serverchan", "sendkey", fallback=""))

    def save_config(self):
        if "push" not in self.config_manager:
            self.config_manager["push"] = {}
        if self.push_email_radio.isChecked():
            self.config_manager["push"]["method"] = "email"
        elif self.push_feishu_radio.isChecked():
            self.config_manager["push"]["method"] = "feishu"
        elif self.push_serverchan_radio.isChecked():
            self.config_manager["push"]["method"] = "serverchan"
        else:
            self.config_manager["push"]["method"] = "none"

        if "email" not in self.config_manager:
            self.config_manager["email"] = {}
        self.config_manager["email"]["smtp"] = self.smtp.text()
        self.config_manager["email"]["port"] = self.port.text()
        self.config_manager["email"]["sender"] = self.sender.text()
        self.config_manager["email"]["receiver"] = self.receiver.text()
        self.config_manager["email"]["auth"] = self.auth.text()

        if "feishu" not in self.config_manager:
            self.config_manager["feishu"] = {}
        self.config_manager["feishu"]["webhook_url"] = self.feishu_webhook.text()
        self.config_manager["feishu"]["secret"] = self.feishu_secret.text()

        if "serverchan" not in self.config_manager:
            self.config_manager["serverchan"] = {}
        self.config_manager["serverchan"]["sendkey"] = self.serverchan_sendkey.text()