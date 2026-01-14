import os
from pathlib import Path

# 获取当前用户的 AppData\Local 路径（Windows 专用）
local_appdata = os.getenv('LOCALAPPDATA')
if not local_appdata:
    raise EnvironmentError("无法获取 LOCALAPPDATA 环境变量，此脚本仅支持 Windows。")

# 构建目标文件夹和配置文件路径
grade_tracker_dir = Path(local_appdata) / "GradeTracker"
config_file = grade_tracker_dir / "config.ini"

# 如果文件夹不存在，则创建
if not grade_tracker_dir.exists():
    print(f"📁 创建文件夹: {grade_tracker_dir}")
    grade_tracker_dir.mkdir(parents=True, exist_ok=True)
else:
    print(f"✅ 文件夹已存在: {grade_tracker_dir}")

# 定义 config.ini 的完整内容（使用三重引号保留格式和注释）
config_content = """[logging]
level= DEBUG

[run_model]
model= DEV

; ===== 账号配置 =====
[account]
username=
password=

; ===== 学期配置 =====
[semester]
first_monday=2026-02-24

; ===== 循环检测配置 =====
[loop_getCourseGrades]
enabled=False
time=3600

[loop_getCourseSchedule]
enabled=False
time=3600

; ===== 邮件推送配置 =====
[email]
smtp=smtp.example.com
port=465
sender=your_email@example.com
receiver=target_email@example.com
auth=your_email_password_or_auth_code
"""

# 写入配置文件（UTF-8 无 BOM）
print(f"📝 写入配置文件: {config_file}")
with open(config_file, 'w', encoding='utf-8') as f:
    f.write(config_content)

print("✅ GradeTracker 配置文件初始化完成！")
print("💡 请手动编辑 config.ini，填写 username、password 和邮箱认证信息。")