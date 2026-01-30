import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 尝试导入Windows API相关模块
try:
    import ctypes
    from ctypes import wintypes
    import win32api
    import win32gui
    import win32con
    WINDOWS_API_AVAILABLE = True
except ImportError:
    WINDOWS_API_AVAILABLE = False

# 添加父目录到 sys.path（确保能找到 core 模块）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 导入日志模块
try:
    from log import init_logger
except ImportError:
    try:
        from core.log import init_logger
    except ImportError:
        # 如果都找不到，创建一个简单的日志函数
        def init_logger(name):
            import logging
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            if not logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            return logger

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
    
    # 在Windows上确保任务栏图标正确显示
    if sys.platform == "win32":
        try:
            # 设置应用程序组ID
            import ctypes
            myappid = 'Capture_Push.GUI.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except ImportError:
            pass  # 如果ctypes不可用则跳过
        except Exception as e:
            logger.error(f"无法设置AppUserModelID: {e}")
    
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    icon_path = None
    
    # 尝试多种可能的路径
    possible_paths = [
        BASE_DIR / "resources" / "app_icon.ico",  # 开发环境路径
        Path(sys.prefix) / "resources" / "app_icon.ico",  # 安装环境路径
        Path.cwd() / "resources" / "app_icon.ico",  # 当前工作目录
        Path(sys.executable).parent / "resources" / "app_icon.ico"  # 可执行文件所在目录
    ]
    
    for path in possible_paths:
        if path.exists():
            icon_path = path
            break
    
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
        
        # 在Windows系统上，额外设置任务栏图标
        if sys.platform == "win32":
            try:
                # 使用ctypes设置应用程序组ID，这有助于Windows识别任务栏图标
                myappid = 'Capture_Push.GUI.1'  # 任意唯一字符串
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception as e:
                logger.error(f"无法设置Windows AppUserModelID: {e}")
            
            # 尝试使用win32api设置图标（如果可用）
            if WINDOWS_API_AVAILABLE:
                try:
                    # 设置当前进程的图标
                    icon_handle = win32gui.LoadImage(
                        win32api.GetModuleHandle(None),
                        str(icon_path),
                        win32con.IMAGE_ICON,
                        0, 0,
                        win32con.LR_LOADFROMFILE
                    )
                    
                    # 设置大图标和小图标
                    win32gui.SendMessage(
                        win32gui.GetConsoleWindow(),
                        win32con.WM_SETICON,
                        win32con.ICON_BIG,
                        icon_handle
                    )
                    win32gui.SendMessage(
                        win32gui.GetConsoleWindow(),
                        win32con.WM_SETICON,
                        win32con.ICON_SMALL,
                        icon_handle
                    )
                except Exception as e:
                    logger.error(f"无法设置Windows任务栏图标: {e}")
    
    logger.info("正在创建配置窗口")
    w = ConfigWindow()
    logger.info("正在显示配置窗口")
    w.show()
    logger.info("GUI应用启动完成，等待退出")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
