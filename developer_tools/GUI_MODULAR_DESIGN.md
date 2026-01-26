# GUI 模块化设计说明

### 模块划分原则
- **功能独立**：每个模块负责单一功能领域
- **职责分离**：UI 层、业务逻辑层、数据访问层分离
- **易于复用**：组件可在不同窗口间共享

### 模块结构

#### [gui/gui.py]
- **职责**：应用入口点
- **功能**：初始化 Qt 应用并启动主窗口
- **特点**：最轻量，只包含启动逻辑

#### [gui/config_window.py]
- **职责**：主配置窗口
- **功能**：包含基本配置、推送设置、关于三个标签页的所有 UI 逻辑
- **特点**：管理所有配置项的加载与保存，包含配置导出和清除功能

**示例代码片段**：
```python
# 加载配置
def load_config(self):
    from core.config_manager import load_config
    self.cfg = load_config()
    # 加载各个字段的值
    self.username.setText(self.cfg.get("account", "username", fallback=""))
    self.password.setText(self.cfg.get("account", "password", fallback=""))

# 保存配置
def save_config(self):
    from core.config_manager import save_config
    # 更新配置对象
    if "account" not in self.cfg: self.cfg["account"] = {}
    self.cfg["account"]["username"] = self.username.text()
    self.cfg["account"]["password"] = self.password.text()
    # 保存到文件
    save_config(self.cfg)
```

#### [gui/grades_window.py]
- **职责**：成绩查看窗口
- **功能**：成绩表格展示、网络刷新、缓存清除
- **特点**：独立于其他窗口，专注于成绩数据

#### [gui/schedule_window.py]
- **职责**：课表查看窗口
- **功能**：课表色块渲染、周次切换、手动编辑
- **特点**：复杂交互逻辑，支持双击编辑

#### [gui/dialogs.py]
- **职责**：对话框组件
- **功能**：课程编辑对话框等弹窗
- **特点**：可被多个窗口复用

#### [gui/widgets.py]
- **职责**：自定义 UI 组件
- **功能**：课程色块等可视化元素
- **特点**：纯粹的 UI 组件，不含逻辑

## 维护指南

### 添加新功能
1. **新窗口**：创建独立模块，如 `new_window.py`
2. **新对话框**：添加到 [dialogs.py] 或新建对话框模块
3. **新组件**：添加到 [widgets.py]或新建组件模块
4. **配置项**：在 [config_window.py]中添加相应 UI 和配置逻辑

### 修改现有功能
1. **UI 变更**：在对应模块中修改，不影响其他模块
2. **业务逻辑**：在对应模块中修改，保持模块内部职责一致性
3. **跨模块交互**：通过函数调用或信号槽机制实现

## 配置导出功能

### 导出明文配置
- **位置**：在 [config_window.py] 的"关于"标签页中实现
- **验证**：需要用户提供教务系统登录密码进行身份验证
- **实现**：使用 `core.config_manager.load_config()` 加载加密配置，然后保存为明文文件
- **安全**：导出的明文配置文件应有明确的安全提示

**示例代码**：
```python
def export_plaintext_config(self):
    from PySide6.QtWidgets import QInputDialog, QFileDialog
    import os
    
    # 验证用户身份
    password, ok = QInputDialog.getText(self, "身份验证", "请输入教务系统登录密码:", QLineEdit.Password)
    if not ok:
        return
    
    # 验证密码
    current_password = self.password.text()
    if password != current_password:
        QMessageBox.critical(self, "验证失败", "密码不正确")
        return
    
    # 导出配置
    from core.config_manager import load_config
    cfg = load_config()
    
    # 选择保存位置
    file_path, _ = QFileDialog.getSaveFileName(
        self, "保存明文配置文件", os.path.expanduser("~/config_export.ini"), 
        "配置文件 (*.ini)"
    )
    
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as f:
            cfg.write(f)
        QMessageBox.information(self, "导出成功", f"配置已保存到：{file_path}")
```

### 清除配置
- **位置**：在 [config_window.py] 的"关于"标签页中实现
- **确认**：需要二次确认以防止误操作
- **实现**：删除配置文件并提示用户重启程序

### 调整日志级别和运行模式
- **位置**：在 [config_window.py] 的"关于"标签页中实现
- **功能**：允许用户调整 [logging] 和 [run_model] 配置
- **实现**：通过对话框让用户选择新值并保存

**示例代码**：
```python
def adjust_logging_and_run_model(self):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
    
    dialog = QDialog(self)
    dialog.setWindowTitle("调整日志级别和运行模式")
    
    layout = QVBoxLayout(dialog)
    
    # 日志级别选择
    log_layout = QHBoxLayout()
    log_layout.addWidget(QLabel("日志级别:"))
    log_combo = QComboBox()
    log_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    log_combo.setCurrentText(self.cfg.get("logging", "level", fallback="INFO"))
    log_layout.addWidget(log_combo)
    layout.addLayout(log_layout)
    
    # 运行模式选择
    run_layout = QHBoxLayout()
    run_layout.addWidget(QLabel("运行模式:"))
    run_combo = QComboBox()
    run_combo.addItems(["DEV", "BUILD"])
    run_combo.setCurrentText(self.cfg.get("run_model", "model", fallback="BUILD"))
    run_layout.addWidget(run_combo)
    layout.addLayout(run_layout)
    
    # 按钮
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    
    if dialog.exec() == QDialog.Accepted:
        # 更新配置
        self.cfg["logging"]["level"] = log_combo.currentText()
        self.cfg["run_model"]["model"] = run_combo.currentText()
        
        # 保存配置
        from core.config_manager import save_config
        save_config(self.cfg)
        QMessageBox.information(self, "修改成功", "配置已更新")
```
