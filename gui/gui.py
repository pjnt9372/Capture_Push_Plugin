import sys
import os
import configparser
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox,
    QCheckBox, QSpinBox, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QDateEdit, QComboBox # 新增 QFrame 用于美化色块
)
from PySide6.QtGui import QColor, QFont # 新增相关引用
from PySide6.QtCore import Qt, QDate

# 添加父目录到 sys.path（确保能找到 core 模块）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 导入统一配置路径管理和解析模块
from core.log import get_config_path, get_log_file_path
from core.school import get_available_schools, get_school_module

# 使用统一的配置路径管理（AppData 目录）
CONFIG_FILE = str(get_config_path())
APPDATA_DIR = get_log_file_path('gui').parent
MANUAL_SCHEDULE_FILE = APPDATA_DIR / "manual_schedule.json"

def get_current_school_code():
    """从配置文件中获取当前院校代码"""
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    return cfg.get("account", "school_code", fallback="10546")

class CourseEditDialog(QWidget):
    """手动编辑/添加课程的对话框"""
    def __init__(self, parent=None, data=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("编辑课程")
        self.setFixedSize(400, 400) # 增大尺寸
        self.data = data or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.data.get("课程名称", ""))
        self.room_edit = QLineEdit(self.data.get("教室", ""))
        self.teacher_edit = QLineEdit(self.data.get("教师", ""))
        self.weeks_edit = QLineEdit(self.data.get("上课周次", "1-20"))
        # 优化提示文字
        self.weeks_edit.setPlaceholderText("提示：1-16 (连续) 或 1,3,5 (单周)")
        
        # 允许用户指定持续节数
        self.span_spin = QSpinBox()
        self.span_spin.setRange(1, 4)
        self.span_spin.setValue(self.data.get("row_span", 1))

        form.addRow("课程名称:", self.name_edit)
        form.addRow("教室:", self.room_edit)
        form.addRow("教师:", self.teacher_edit)
        form.addRow("上课周次:", self.weeks_edit)
        form.addRow("持续节数:", self.span_spin)
        
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("确定")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def parse_weeks(self, weeks_str):
        """解析周次字符串为列表"""
        weeks = set()
        try:
            parts = weeks_str.replace("，", ",").split(",")
            for part in parts:
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    weeks.update(range(start, end + 1))
                elif part.strip():
                    weeks.add(int(part.strip()))
        except:
            pass
        return sorted(list(weeks))

    def accept(self):
        weeks_str = self.weeks_edit.text()
        weeks_list = self.parse_weeks(weeks_str)
        
        self.result = {
            "课程名称": self.name_edit.text(),
            "教室": self.room_edit.text(),
            "教师": self.teacher_edit.text(),
            "上课周次": weeks_str,
            "周次列表": weeks_list,
            "row_span": self.span_spin.value(),
            "is_manual": True
        }
        self.parent().on_dialog_finished(self.result)
        self.close()

class GradesViewerWindow(QWidget):
    """独立窗口：查看成绩"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push · 成绩查看")
        self.resize(900, 600)
        self.init_ui()

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
        
        # 底部按钮区（清除缓存）
        bottom_layout = QHBoxLayout()
        clear_btn = QPushButton("清除成绩缓存")
        clear_btn.setStyleSheet("color: #d83b01; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_grade_cache)
        bottom_layout.addStretch()
        bottom_layout.addWidget(clear_btn)
        layout.addLayout(bottom_layout)

        # 字体放大
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.table.setFont(font)

        self.load_data()

    def load_data(self):
        try:
            grade_html_file = APPDATA_DIR / "grade.html"
            if not grade_html_file.exists():
                # 清空表格
                self.table.setRowCount(0)
                # QMessageBox.warning(self, "未找到数据", f"未发现成绩缓存文件：\n{grade_html_file}\n请先运行程序获取数据。")
                return

            with open(grade_html_file, "r", encoding="utf-8") as f:
                html = f.read()
            
            school_code = get_current_school_code()
            school_mod = get_school_module(school_code)
            if not school_mod:
                QMessageBox.critical(self, "错误", f"找不到院校模块: {school_code}")
                return

            grades = school_mod.parse_grades(html)
            if not grades:
                self.table.setRowCount(0)
                # QMessageBox.information(self, "提示", "未能从缓存文件中解析出成绩，可能文件内容为空或格式不匹配。")
                return

            self.table.setRowCount(len(grades))
            for i, g in enumerate(grades):
                self.table.setItem(i, 0, QTableWidgetItem(g.get("学期", "")))
                self.table.setItem(i, 1, QTableWidgetItem(g.get("课程名称", "")))
                self.table.setItem(i, 2, QTableWidgetItem(g.get("成绩", "")))
                self.table.setItem(i, 3, QTableWidgetItem(g.get("学分", "")))
                self.table.setItem(i, 4, QTableWidgetItem(g.get("课程属性", "")))
                self.table.setItem(i, 5, QTableWidgetItem(g.get("课程编号", "")))
                
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"查看成绩时发生错误：\n{str(e)}")

    def clear_grade_cache(self):
        """清除成绩缓存"""
        reply = QMessageBox.question(self, "确认清除", "确定要清除成绩缓存文件吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                grade_html = APPDATA_DIR / "grade.html"
                if grade_html.exists(): grade_html.unlink()
                # 同时清除 state 目录下的成绩状态，防止下次刷新没提醒
                state_file = APPDATA_DIR / "state" / "last_grades.json"
                if state_file.exists(): state_file.unlink()
                
                QMessageBox.information(self, "成功", "成绩缓存已清除。")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "失败", f"清除失败：{e}")

class CourseBlock(QFrame):
    """自定义课表色块"""
    def __init__(self, name, room, teacher, color_hex):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color_hex};
                border-radius: 6px;
                margin: 1px;
            }}
            QLabel {{
                color: black;
                background: transparent;
                font-family: "Microsoft YaHei";
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(1)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        
        info_text = ""
        if room: info_text += f"@{room}\n"
        if teacher: info_text += f"{teacher}"
        
        info_label = QLabel(info_text.strip())
        info_label.setStyleSheet("font-size: 11px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(name_label)
        layout.addWidget(info_label)
        layout.addStretch()

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
        
        # 底部按钮区（添加清除缓存）
        bottom_layout = QHBoxLayout()
        clear_btn = QPushButton("清除课表数据 (含手动修改)")
        clear_btn.setStyleSheet("color: #d83b01; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_schedule_cache)
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

class ConfigWindow(QWidget):
    """主配置窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Capture_Push · 设置")
        self.resize(500, 650)
        
        # 放大全局字体以确保看清
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

        self.cfg = configparser.ConfigParser()
        self.cfg.read(CONFIG_FILE, encoding="utf-8")

        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 标签页
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_basic_tab(), "基本配置")
        self.tabs.addTab(self.create_push_tab(), "推送设置")
        layout.addWidget(self.tabs)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        
        self.view_grades_btn = QPushButton("查看成绩")
        self.view_grades_btn.clicked.connect(self.show_grades_viewer)
        
        self.view_schedule_btn = QPushButton("查看课表")
        self.view_schedule_btn.clicked.connect(self.show_schedule_viewer)
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_config)
        
        btn_layout.addWidget(self.view_grades_btn)
        btn_layout.addWidget(self.view_schedule_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

    def create_basic_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.school_combo = QComboBox()
        self.available_schools = get_available_schools()
        for code, name in self.available_schools.items():
            self.school_combo.addItem(name, code)

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.first_monday = QDateEdit()
        self.first_monday.setCalendarPopup(True)
        self.first_monday.setDisplayFormat("yyyy-MM-dd")

        form.addRow("选择院校", self.school_combo)
        form.addRow("学号", self.username)
        form.addRow("密码", self.password)
        form.addRow("第一周周一", self.first_monday)
        layout.addLayout(form)

        loop_group = QGroupBox("循环检测配置")
        loop_layout = QVBoxLayout(loop_group)

        # 成绩循环
        grade_lay = QHBoxLayout()
        self.loop_grade_enabled = QCheckBox("启用成绩循环检测")
        self.loop_grade_interval = QSpinBox()
        self.loop_grade_interval.setRange(60, 604800)
        self.loop_grade_interval.setSuffix(" 秒")
        grade_lay.addWidget(self.loop_grade_enabled)
        grade_lay.addWidget(QLabel("间隔:"))
        grade_lay.addWidget(self.loop_grade_interval)
        loop_layout.addLayout(grade_lay)

        # 课表循环
        sched_lay = QHBoxLayout()
        self.loop_schedule_enabled = QCheckBox("启用课表循环检测")
        self.loop_schedule_interval = QSpinBox()
        self.loop_schedule_interval.setRange(60, 604800)
        self.loop_schedule_interval.setSuffix(" 秒")
        sched_lay.addWidget(self.loop_schedule_enabled)
        sched_lay.addWidget(QLabel("间隔:"))
        sched_lay.addWidget(self.loop_schedule_interval)
        loop_layout.addLayout(sched_lay)

        loop_layout.addWidget(QLabel("提示: 1小时=3600秒, 1天=86400秒"))
        layout.addWidget(loop_group)

        # 课表定时推送设置
        push_group = QGroupBox("课表定时推送设置")
        push_layout = QVBoxLayout(push_group)
        self.push_today_enabled = QCheckBox("当天 08:00 推送今日课表")
        self.push_tomorrow_enabled = QCheckBox("前一天 21:00 推送次日课表")
        self.push_next_week_enabled = QCheckBox("周日 20:00 推送下周全部课表")
        push_layout.addWidget(self.push_today_enabled)
        push_layout.addWidget(self.push_tomorrow_enabled)
        push_layout.addWidget(self.push_next_week_enabled)
        layout.addWidget(push_group)

        layout.addStretch()
        return tab

    def create_push_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 推送方式
        method_group = QGroupBox("推送方式 (单选)")
        method_layout = QVBoxLayout(method_group)
        self.push_button_group = QButtonGroup(self)
        
        self.push_none_radio = QRadioButton("不启用推送")
        self.push_email_radio = QRadioButton("邮件推送")
        self.push_feishu_radio = QRadioButton("飞书机器人推送")
        self.push_test1_radio = QRadioButton("TEST1 (测试方式)")
        
        self.push_button_group.addButton(self.push_none_radio, 0)
        self.push_button_group.addButton(self.push_email_radio, 1)
        self.push_button_group.addButton(self.push_feishu_radio, 2)
        self.push_button_group.addButton(self.push_test1_radio, 3)
        
        method_layout.addWidget(self.push_none_radio)
        method_layout.addWidget(self.push_email_radio)
        method_layout.addWidget(self.push_feishu_radio)
        method_layout.addWidget(self.push_test1_radio)
        layout.addWidget(method_group)

        # 邮件配置
        email_group = QGroupBox("邮件配置")
        email_form = QFormLayout(email_group)
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
        layout.addWidget(email_group)

        # 飞书配置
        feishu_group = QGroupBox("飞书机器人配置")
        feishu_form = QFormLayout(feishu_group)
        self.feishu_webhook = QLineEdit()
        feishu_form.addRow("Webhook URL", self.feishu_webhook)
        layout.addWidget(feishu_group)

        # TEST1 组
        test1_group = QGroupBox("TEST1 测试组")
        test1_lay = QHBoxLayout(test1_group)
        self.test1_btn = QPushButton("发送测试消息")
        self.test1_btn.clicked.connect(self.send_test_push)
        self.test1_status = QLabel("状态: 待命")
        test1_lay.addWidget(self.test1_btn)
        test1_lay.addWidget(self.test1_status)
        layout.addWidget(test1_group)

        layout.addStretch()
        return tab

    def load_config(self):
        # 院校
        school_code = self.cfg.get("account", "school_code", fallback="10546")
        index = self.school_combo.findData(school_code)
        if index >= 0:
            self.school_combo.setCurrentIndex(index)

        # 账号
        self.username.setText(self.cfg.get("account", "username", fallback=""))
        self.password.setText(self.cfg.get("account", "password", fallback=""))
        
        date_str = self.cfg.get("semester", "first_monday", fallback="")
        if date_str:
            self.first_monday.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        else:
            self.first_monday.setDate(QDate.currentDate())

        # 循环
        self.loop_grade_enabled.setChecked(self.cfg.getboolean("loop_getCourseGrades", "enabled", fallback=True))
        self.loop_grade_interval.setValue(self.cfg.getint("loop_getCourseGrades", "time", fallback=21600))
        self.loop_schedule_enabled.setChecked(self.cfg.getboolean("loop_getCourseSchedule", "enabled", fallback=False))
        self.loop_schedule_interval.setValue(self.cfg.getint("loop_getCourseSchedule", "time", fallback=604800))

        # 定时推送
        if "schedule_push" not in self.cfg:
            self.cfg["schedule_push"] = {}
        self.push_today_enabled.setChecked(self.cfg.getboolean("schedule_push", "today_8am", fallback=False))
        self.push_tomorrow_enabled.setChecked(self.cfg.getboolean("schedule_push", "tomorrow_9pm", fallback=False))
        self.push_next_week_enabled.setChecked(self.cfg.getboolean("schedule_push", "next_week_sunday", fallback=False))

        # 推送方式
        method = self.cfg.get("push", "method", fallback="none").lower()
        if method == "email": self.push_email_radio.setChecked(True)
        elif method == "feishu": self.push_feishu_radio.setChecked(True)
        elif method == "test1": self.push_test1_radio.setChecked(True)
        else: self.push_none_radio.setChecked(True)

        # 详细配置
        self.smtp.setText(self.cfg.get("email", "smtp", fallback=""))
        self.port.setText(self.cfg.get("email", "port", fallback=""))
        self.sender.setText(self.cfg.get("email", "sender", fallback=""))
        self.receiver.setText(self.cfg.get("email", "receiver", fallback=""))
        self.auth.setText(self.cfg.get("email", "auth", fallback=""))
        self.feishu_webhook.setText(self.cfg.get("feishu", "webhook_url", fallback=""))

    def save_config(self):
        # 检查 Outlook
        sender = self.sender.text().strip().lower()
        if any(sender.endswith(d) for d in ["outlook.com", "hotmail.com", "live.com", "msn.com"]):
            QMessageBox.critical(self, "不支持的邮箱", "Outlook/Hotmail 等微软邮箱由于强制 OAuth2 认证，目前无法使用基本认证发送邮件，请更换发件人邮箱。")
            return

        # 写入内存
        if "account" not in self.cfg: self.cfg["account"] = {}
        self.cfg["account"]["school_code"] = self.school_combo.currentData()
        self.cfg["account"]["username"] = self.username.text()
        self.cfg["account"]["password"] = self.password.text()

        if "semester" not in self.cfg: self.cfg["semester"] = {}
        self.cfg["semester"]["first_monday"] = self.first_monday.date().toString("yyyy-MM-dd")

        if "loop_getCourseGrades" not in self.cfg: self.cfg["loop_getCourseGrades"] = {}
        self.cfg["loop_getCourseGrades"]["enabled"] = str(self.loop_grade_enabled.isChecked())
        self.cfg["loop_getCourseGrades"]["time"] = str(self.loop_grade_interval.value())

        if "loop_getCourseSchedule" not in self.cfg: self.cfg["loop_getCourseSchedule"] = {}
        self.cfg["loop_getCourseSchedule"]["enabled"] = str(self.loop_schedule_enabled.isChecked())
        self.cfg["loop_getCourseSchedule"]["time"] = str(self.loop_schedule_interval.value())

        if "schedule_push" not in self.cfg:
            self.cfg["schedule_push"] = {}
        self.cfg["schedule_push"]["today_8am"] = str(self.push_today_enabled.isChecked())
        self.cfg["schedule_push"]["tomorrow_9pm"] = str(self.push_tomorrow_enabled.isChecked())
        self.cfg["schedule_push"]["next_week_sunday"] = str(self.push_next_week_enabled.isChecked())

        if "push" not in self.cfg: self.cfg["push"] = {}
        if self.push_email_radio.isChecked(): self.cfg["push"]["method"] = "email"
        elif self.push_feishu_radio.isChecked(): self.cfg["push"]["method"] = "feishu"
        elif self.push_test1_radio.isChecked(): self.cfg["push"]["method"] = "test1"
        else: self.cfg["push"]["method"] = "none"

        if "email" not in self.cfg: self.cfg["email"] = {}
        self.cfg["email"]["smtp"] = self.smtp.text()
        self.cfg["email"]["port"] = self.port.text()
        self.cfg["email"]["sender"] = self.sender.text()
        self.cfg["email"]["receiver"] = self.receiver.text()
        self.cfg["email"]["auth"] = self.auth.text()

        if "feishu" not in self.cfg: self.cfg["feishu"] = {}
        self.cfg["feishu"]["webhook_url"] = self.feishu_webhook.text()

        # 物理保存
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                self.cfg.write(f)
            QMessageBox.information(self, "保存成功", "配置已成功保存到本地。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入配置文件时出错：\n{str(e)}")

    def send_test_push(self):
        self.test1_status.setText("状态: 发送中...")
        QApplication.processEvents()
        try:
            from core import push
            if not push.is_push_enabled():
                self.test1_status.setText("状态: 未启用推送")
                QMessageBox.warning(self, "测试失败", "请先在'推送设置'中启用一种推送方式并保存。")
                return
            
            manager = push.NotificationManager()
            success = manager.send_with_active_sender("Capture_Push 测试", "如果您看到这条消息，说明推送配置正常。")
            if success:
                self.test1_status.setText("状态: 发送成功")
                QMessageBox.information(self, "成功", "测试消息已发出。")
            else:
                self.test1_status.setText("状态: 发送失败")
                QMessageBox.warning(self, "失败", "消息发送失败，请检查配置或日志。")
        except Exception as e:
            self.test1_status.setText("状态: 出错")
            QMessageBox.critical(self, "错误", f"发送测试消息时异常：\n{str(e)}")

    def show_grades_viewer(self):
        if not hasattr(self, 'grades_win') or not self.grades_win.isVisible():
            self.grades_win = GradesViewerWindow()
            self.grades_win.show()
        else:
            self.grades_win.activateWindow()

    def show_schedule_viewer(self):
        if not hasattr(self, 'sched_win') or not self.sched_win.isVisible():
            self.sched_win = ScheduleViewerWindow()
            self.sched_win.show()
        else:
            self.sched_win.activateWindow()

    def closeEvent(self, event):
        """主窗口关闭事件：检查是否有子窗口未关闭"""
        active_sub_windows = []
        
        # 检查成绩窗口
        if hasattr(self, 'grades_win') and self.grades_win and self.grades_win.isVisible():
            active_sub_windows.append("成绩查看")
            
        # 检查课表窗口
        if hasattr(self, 'sched_win') and self.sched_win and self.sched_win.isVisible():
            active_sub_windows.append("课表查看")
            
        if active_sub_windows:
            win_list = "、".join(active_sub_windows)
            QMessageBox.warning(
                self, 
                "提示", 
                f"请先关闭正在运行的【{win_list}】页面，然后再关闭设置窗口。"
            )
            event.ignore()  # 忽略关闭事件
        else:
            event.accept()  # 允许关闭

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ConfigWindow()
    w.show()
    sys.exit(app.exec())
