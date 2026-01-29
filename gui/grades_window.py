import sys
import subprocess
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QHBoxLayout, QPushButton, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# 导入日志模块
try:
    from log import init_logger
except ImportError:
    from core.log import init_logger

# 初始化日志记录器
logger = init_logger("grades_window")

# 动态获取基础目录和配置路径
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from log import get_config_path, get_log_file_path
    from config_manager import load_config
except ImportError:
    from core.log import get_config_path, get_log_file_path
    from core.config_manager import load_config

try:
    from school import get_school_module
except ImportError:
    from core.school import get_school_module

CONFIG_FILE = str(get_config_path())
APPDATA_DIR = get_log_file_path('gui').parent

def get_current_school_code():
    """从配置文件中获取当前院校代码"""
    cfg = load_config()
    return cfg.get("account", "school_code", fallback="10546")

class GradesViewerWindow(QWidget):
    """独立窗口：查看成绩"""
    def __init__(self):
        logger.info("成绩查看窗口初始化开始")
        super().__init__()
        self.setWindowTitle("Capture_Push · 成绩查看")
        self.resize(900, 600)
        
        # 设置窗口图标
        try:
            icon_path = BASE_DIR / "resources" / "app_icon.ico"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception as e:
            logger.error(f"无法设置成绩窗口图标: {e}")
            print(f"无法设置成绩窗口图标: {e}")
        
        logger.info("正在初始化UI")
        self.init_ui()
        logger.info("成绩查看窗口初始化完成")

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 表格配置
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["学期", "课程名称", "成绩", "学分", "课程属性", "课程编号"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch) # 课程名称拉伸
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) # 不可编辑
        
        layout.addWidget(self.table)
        
        # 底部按钮区（刷新与清除）
        bottom_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新成绩 (从网络获取)")
        refresh_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        refresh_btn.clicked.connect(self.refresh_data)
        
        clear_btn = QPushButton("清除成绩缓存")
        clear_btn.setStyleSheet("color: #d83b01; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_grade_cache)
        
        bottom_layout.addWidget(refresh_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(clear_btn)
        layout.addLayout(bottom_layout)

        # 字体放大
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.table.setFont(font)

        self.load_data()

    def refresh_data(self):
        """手动触发网络刷新"""
        logger.info("开始手动触发成绩数据刷新")
        # 禁用按钮防止重复点击
        sender = self.sender()
        if sender: 
            logger.debug("禁用刷新按钮防止重复点击")
            sender.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # 获取 pythonw.exe 路径
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "pythonw.exe").exists():
                py_exe = str(exe_dir / "pythonw.exe")
            else:
                py_exe = sys.executable
                
            go_script = str(BASE_DIR / "core" / "go.py")
            logger.debug(f"执行成绩刷新脚本: {py_exe} {go_script} --fetch-grade --force")
            
            # 使用 subprocess 运行
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([py_exe, go_script, "--fetch-grade", "--force"], 
                            creationflags=CREATE_NO_WINDOW).wait()
            
            logger.info("成绩数据刷新完成，正在重新加载数据")
            self.load_data()
            logger.info("成绩数据已从网络同步")
            QMessageBox.information(self, "刷新完成", "成绩数据已从网络同步。")
        except Exception as e:
            logger.error(f"无法执行刷新脚本: {e}")
            QMessageBox.critical(self, "刷新失败", f"无法执行刷新脚本：{e}")
        finally:
            logger.debug("恢复鼠标光标")
            QApplication.restoreOverrideCursor()
            if sender: 
                logger.debug("启用刷新按钮")
                sender.setEnabled(True)

    def load_data(self):
        logger.debug("开始加载成绩数据")
        try:
            grade_html_file = APPDATA_DIR / "grade.html"
            logger.debug(f"检查成绩HTML文件是否存在: {grade_html_file}")
            if not grade_html_file.exists():
                logger.info("成绩HTML文件不存在，清空表格")
                self.table.setRowCount(0)
                return

            with open(grade_html_file, "r", encoding="utf-8") as f:
                html = f.read()
            logger.debug(f"成功读取成绩HTML文件，大小: {len(html)} 字符")
            
            school_code = get_current_school_code()
            logger.debug(f"获取当前院校代码: {school_code}")
            school_mod = get_school_module(school_code)
            if not school_mod:
                logger.error(f"找不到院校模块: {school_code}")
                QMessageBox.critical(self, "错误", f"找不到院校模块: {school_code}")
                return

            grades = school_mod.parse_grades(html)
            logger.debug(f"解析得到 {len(grades) if grades else 0} 条成绩记录")
            if not grades:
                logger.info("没有找到成绩记录，清空表格")
                self.table.setRowCount(0)
                return

            self.table.setRowCount(len(grades))
            logger.debug(f"设置表格行数为: {len(grades)}")
            for i, g in enumerate(grades):
                self.table.setItem(i, 0, QTableWidgetItem(g.get("学期", "")))
                self.table.setItem(i, 1, QTableWidgetItem(g.get("课程名称", "")))
                self.table.setItem(i, 2, QTableWidgetItem(g.get("成绩", "")))
                self.table.setItem(i, 3, QTableWidgetItem(g.get("学分", "")))
                self.table.setItem(i, 4, QTableWidgetItem(g.get("课程属性", "")))
                self.table.setItem(i, 5, QTableWidgetItem(g.get("课程编号", "")))
            logger.debug("成绩数据加载完成")
                
        except Exception as e:
            logger.error(f"查看成绩时发生错误: {e}")
            QMessageBox.critical(self, "加载失败", f"查看成绩时发生错误：\n{str(e)}")

    def clear_grade_cache(self):
        """清除成绩缓存"""
        logger.info("开始清除成绩缓存")
        reply = QMessageBox.question(self, "确认清除", "确定要清除成绩缓存文件吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                grade_html = APPDATA_DIR / "grade.html"
                if grade_html.exists(): 
                    logger.debug("删除成绩HTML缓存文件")
                    grade_html.unlink()
                # 同时清除 state 目录下的成绩状态，防止下次刷新没提醒
                state_file = APPDATA_DIR / "state" / "last_grades.json"
                if state_file.exists(): 
                    logger.debug("删除成绩状态文件")
                    state_file.unlink()
                
                logger.info("成绩缓存清除成功")
                QMessageBox.information(self, "成功", "成绩缓存已清除。")
                self.load_data()
            except Exception as e:
                logger.error(f"清除成绩缓存失败: {e}")
                QMessageBox.critical(self, "失败", f"清除失败：{e}")
