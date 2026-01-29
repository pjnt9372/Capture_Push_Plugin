import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 添加父目录到 sys.path（确保能找到 core 模块）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 导入日志模块
try:
    from log import init_logger
except ImportError:
    from core.log import init_logger

# 初始化日志记录器
logger = init_logger("gui")

# 导入主配置窗口
try:
    from gui.config_window import ConfigWindow
except ImportError as e:
    logger.error(f"导入 ConfigWindow 失败: {e}")
    # 提供更有用的错误信息，并重新抛出异常以便调试
    print(f"致命错误: 无法导入 ConfigWindow。请确保所有依赖模块都已正确安装且路径正确。")
    print(f"错误详情: {e}")
    raise


def main():
    logger.info("GUI应用启动")
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = BASE_DIR / "resources" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    logger.info("正在创建配置窗口")
    w = ConfigWindow()
    logger.info("正在显示配置窗口")
    w.show()
    logger.info("GUI应用启动完成，等待退出")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
