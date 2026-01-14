import os
from pathlib import Path

# 获取当前用户的 AppData\Local 路径（Windows 专用）
local_appdata = os.getenv('LOCALAPPDATA')
if not local_appdata:
    raise EnvironmentError("无法获取 LOCALAPPDATA 环境变量，此脚本仅支持 Windows。")

# 构建目标文件夹和配置文件路径
capture_push_dir = Path(local_appdata) / "Capture_Push"
config_file = capture_push_dir / "config.ini"

# 如果文件夹不存在，则创建
if not capture_push_dir.exists():
    print(f"📁 创建文件夹: {capture_push_dir}")
    capture_push_dir.mkdir(parents=True, exist_ok=True)
else:
    print(f"✅ 文件夹已存在: {capture_push_dir}")

# 从项目根目录复制配置文件模板
import configparser
from pathlib import Path

# 获取项目根目录的 config.ini 文件
source_config_file = Path(__file__).parent.parent / "config.ini"

if not source_config_file.exists():
    print(f"❌ 找不到源配置文件: {source_config_file}")
    print("💡 请确保此脚本在项目 developer_tools 目录中运行")
    exit(1)

# 读取源配置文件
config = configparser.ConfigParser()
config.read(str(source_config_file), encoding='utf-8')

# 修改 [logging] 部分
if 'logging' not in config:
    config['logging'] = {}
config['logging']['level'] = 'DEBUG'

# 修改 [run_model] 部分
if 'run_model' not in config:
    config['run_model'] = {}
config['run_model']['model'] = 'DEV'

# 写入配置文件（UTF-8 无 BOM）
print(f"📝 写入配置文件: {config_file}")
with open(config_file, 'w', encoding='utf-8') as f:
    config.write(f)

print("✅ Capture_Push 配置文件初始化完成！")
print("💡 请手动编辑 config.ini，填写 username、password 和邮箱认证信息。")