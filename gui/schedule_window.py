import sys
import json
import subprocess
import configparser
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QHBoxLayout, QPushButton, QMessageBox, 
    QApplication, QLabel, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# 动态获取基础目录和配置路径
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from log import get_config_path, get_log_file_path
except ImportError:
    from core.log import get_config_path, get_log_file_path

try:
    from school import get_school_module
except ImportError:
    from core.school import get_school_module

# 导入自定义组件和对话框
try:
    from widgets import CourseBlock
    from dialogs import CourseEditDialog
except ImportError:
    from gui.widgets import CourseBlock
    from gui.dialogs import CourseEditDialog

CONFIG_FILE = str(get_config_path())
APPDATA_DIR = get_log_file_path('gui').parent
MANUAL_SCHEDULE_FILE = APPDATA_DIR / "manual_schedule.json"

def get_current_school_code():
    """从配置文件中获取当前院校代码"""
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    return cfg.get("account", "school_code", fallback="10546")

class ScheduleViewerWindow(QWidget):
    """独立窗口：查看课表（色块展示版，支持周次切换）"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push · 课表查看")
        self.resize(1100, 850)
        
        # 预设更柔和的浅色列表，适合黑色文字
        self.colors = [
            "#FFD1D1", "#FFDFD1", "#FFF0D1", "#E6FAD1", 
            "#D1FAE5", "#D1F2FA", "#D1D5FA", "#E9D1FA",
            "#FAD1F5", "#FAD1D1", "#F5F5F5", "#EEEEEE"
        ]
        self.course_colors = {}
        
        # 加载配置获取第一周周一
        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_FILE, encoding="utf-8")
        self.first_monday_str = self.cfg.get("semester", "first_monday", fallback="")
        
        self.current_week = self.calculate_current_week()
        self.selected_week = self.current_week
        
        self.init_ui()

    def calculate_current_week(self):
        """根据第一周周一反推当前是第几周"""
        if not self.first_monday_str:
            return 1
        try:
            import datetime
            first_monday = datetime.datetime.strptime(self.first_monday_str, "%Y-%m-%d").date()
            today = datetime.date.today()
            delta = (today - first_monday).days
            if delta < 0: return 1
            week = (delta // 7) + 1
            return min(max(week, 1), 20) # 限制在 1-20 周
        except:
            return 1

    def get_color(self, course_name):
        """为课程名分配固定颜色"""
        if course_name not in self.course_colors:
            color_idx = len(self.course_colors) % len(self.colors)
            self.course_colors[course_name] = self.colors[color_idx]
        return self.course_colors[course_name]

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部控制栏
        top_ctrl = QHBoxLayout()
        
        # 周次切换
        top_ctrl.addWidget(QLabel("当前显示："))
        self.week_combo = QSpinBox()
        self.week_combo.setRange(1, 25) # 稍微扩大范围
        self.week_combo.setValue(self.selected_week)
        self.week_combo.setPrefix("第 ")
        self.week_combo.setSuffix(" 周")
        self.week_combo.valueChanged.connect(self.on_week_changed)
        top_ctrl.addWidget(self.week_combo)
        
        self.this_week_label = QLabel("")
        self.this_week_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        top_ctrl.addWidget(self.this_week_label)
        self.update_this_week_label()
            
        top_ctrl.addStretch()
        top_ctrl.addWidget(QLabel("提示：双击单元格进行手动编辑"))
        layout.addLayout(top_ctrl)

        self.table = QTableWidget()
        self.table.setColumnCount(8) # 1列节次 + 7列星期
        self.table.setRowCount(10)   # 调整为10节课
        
        days = ["节次", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.table.setHorizontalHeaderLabels(days)
        
        # 设置表头样式
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50) # 稍微加宽节次列
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False) # 隐藏网格线
        
        # 绑定双击事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        # 初始化节次列
        for i in range(10):
            item = QTableWidgetItem(str(i+1))
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor("#f8f9fa"))
            self.table.setItem(i, 0, item)
            self.table.setRowHeight(i, 75) # 增加行高以适应大字体

        layout.addWidget(self.table)
        
        # 底部按钮区（添加刷新和清除）
        bottom_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新课表 (从网络获取)")
        refresh_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        refresh_btn.clicked.connect(self.refresh_data)
        
        clear_btn = QPushButton("清除课表数据 (含手动修改)")
        clear_btn.setStyleSheet("color: #d83b01; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_schedule_cache)
        
        bottom_layout.addWidget(refresh_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(clear_btn)
        layout.addLayout(bottom_layout)

        self.load_data()

    def on_week_changed(self, value):
        self.selected_week = value
        self.update_this_week_label()
        self.load_data()

    def update_this_week_label(self):
        """更新本周标识标签"""
        if self.selected_week == self.current_week:
            self.this_week_label.setText("(本周)")
        else:
            self.this_week_label.setText(f"(本周是第 {self.current_week} 周)")

    def on_cell_double_clicked(self, row, col):
        """双击单元格打开编辑对话框"""
        if col == 0: return # 节次列不可编辑
        
        # 尝试获取当前格子已有的数据
        existing_data = {}
        # 检查是否是手动修改过的格子
        manual_key = f"{col}-{row+1}"
        manual_data = self.load_manual_schedule()
        if manual_key in manual_data:
            existing_data = manual_data[manual_key]
        
        self.current_editing_pos = (row, col)
        self.edit_dialog = CourseEditDialog(self, existing_data)
        self.edit_dialog.show()

    def on_dialog_finished(self, result):
        """对话框保存后的回调"""
        row, col = self.current_editing_pos
        manual_key = f"{col}-{row+1}" # 星期-开始小节
        
        manual_data = self.load_manual_schedule()
        if not result.get("课程名称"):
            # 如果名称为空，视为删除该位置的手动修改
            if manual_key in manual_data:
                del manual_data[manual_key]
        else:
            manual_data[manual_key] = result
            
        self.save_manual_schedule(manual_data)
        self.load_data() # 重新渲染

    def load_manual_schedule(self):
        """加载手动修改的课表数据"""
        if not MANUAL_SCHEDULE_FILE.exists():
            return {}
        try:
            with open(MANUAL_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_manual_schedule(self, data):
        """保存手动修改的课表数据"""
        try:
            with open(MANUAL_SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存手动修改：{e}")

    def clear_schedule_cache(self):
        """清除课表缓存"""
        reply = QMessageBox.question(self, "确认清除", "确定要清除所有课表缓存（包括手动修改的数据）吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                schedule_html = APPDATA_DIR / "schedule.html"
                if schedule_html.exists(): schedule_html.unlink()
                if MANUAL_SCHEDULE_FILE.exists(): MANUAL_SCHEDULE_FILE.unlink()
                QMessageBox.information(self, "成功", "课表数据已清除。")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "失败", f"清除失败：{e}")

    def refresh_data(self):
        """手动触发网络刷新"""
        # 禁用按钮防止重复点击
        sender = self.sender()
        if sender: sender.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            exe_dir = Path(sys.executable).parent
            if (exe_dir / "pythonw.exe").exists():
                py_exe = str(exe_dir / "pythonw.exe")
            else:
                py_exe = sys.executable
                
            go_script = str(BASE_DIR / "core" / "go.py")
            
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([py_exe, go_script, "--fetch-schedule", "--force"], 
                            creationflags=CREATE_NO_WINDOW).wait()
            
            self.load_data()
            QMessageBox.information(self, "刷新完成", "课表数据已从网络同步。")
        except Exception as e:
            QMessageBox.critical(self, "刷新失败", f"无法执行刷新脚本：{e}")
        finally:
            QApplication.restoreOverrideCursor()
            if sender: sender.setEnabled(True)

    def load_data(self):
        try:
            schedule_html_file = APPDATA_DIR / "schedule.html"
            
            # 1. 加载手动修改的数据
            manual_data = self.load_manual_schedule()
            
            # 2. 加载网页解析的数据
            parsed_schedule = []
            if schedule_html_file.exists():
                with open(schedule_html_file, "r", encoding="utf-8") as f:
                    html = f.read()
                
                school_code = get_current_school_code()
                school_mod = get_school_module(school_code)
                if school_mod:
                    parsed_schedule = school_mod.parse_schedule(html)
                else:
                    QMessageBox.warning(self, "警告", f"找不到院校模块: {school_code}")
            
            # 清除之前的色块和合并单元格
            for r in range(10):
                for c in range(1, 8):
                    self.table.setCellWidget(r, c, None)
                    self.table.setSpan(r, c, 1, 1)

            # 3. 准备合并：记录已占用的单元格，手动修改优先
            occupied = set()

            # 先处理手动修改
            for key, data in manual_data.items():
                col, start = map(int, key.split("-"))
                row = start - 1
                row_span = data.get("row_span", 1)
                
                # 检查周次是否包含在内
                weeks_list = data.get("周次列表", [])
                if weeks_list and self.selected_week not in weeks_list:
                    continue

                name = data.get("课程名称", "")
                room = data.get("教室", "")
                teacher = data.get("教师", "")
                
                if 0 < col <= 7 and 0 <= row < 10:
                    color = self.get_color(name)
                    block = CourseBlock(name, room, teacher, color)
                    # 标记手动修改
                    block.setStyleSheet(block.styleSheet() + "QFrame { border: 2px solid #0078d4; }")
                    
                    actual_span = min(row_span, 10 - row)
                    self.table.setSpan(row, col, actual_span, 1)
                    self.table.setCellWidget(row, col, block)
                    
                    for r in range(row, row + actual_span):
                        occupied.add((r, col))

            # 再处理解析到的数据（如果单元格未被手动占用）
            for s in parsed_schedule:
                day_idx = s.get("星期", 0)
                start = s.get("开始小节", 0)
                end = s.get("结束小节", 0)
                
                # 关键：检查课程周次
                weeks_list = s.get("周次列表", [])
                if "全学期" not in weeks_list and self.selected_week not in weeks_list:
                    continue
                
                if 0 < day_idx <= 7 and 0 < start <= 10:
                    row = start - 1
                    col = day_idx
                    
                    if (row, col) in occupied:
                        continue # 手动修改已占用
                        
                    name = s.get("课程名称", "")
                    room = s.get("教室", "")
                    teacher = s.get("教师", "")
                    
                    effective_end = min(end, 10)
                    row_span = effective_end - start + 1
                    
                    # 检查跨度内是否被占用
                    can_place = True
                    for r in range(row, row + row_span):
                        if (r, col) in occupied:
                            can_place = False
                            break
                    
                    if can_place:
                        color = self.get_color(name)
                        block = CourseBlock(name, room, teacher, color)
                        self.table.setSpan(row, col, row_span, 1)
                        self.table.setCellWidget(row, col, block)
                        for r in range(row, row + row_span):
                            occupied.add((r, col))
                    
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"渲染课表失败：{e}")
