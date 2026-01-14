# register_or_undo.py
import os
import sys
import winreg
import ctypes

def is_admin():
    """检查当前是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_to_admin():
    """以管理员身份重新启动当前脚本"""
    print("⚠️  检测到当前未以管理员权限运行，正在请求提权...")
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1  # SW_SHOWNORMAL
        )
        sys.exit(0)  # 当前进程退出，由新进程接管
    except Exception as e:
        print(f"❌ 提权失败: {e}")
        sys.exit(1)

def get_project_root():
    """获取项目根目录（developer_tools 的父目录）"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def write_registry(value_data):
    """写入 InstallPath 到注册表"""
    try:
        # 打开/创建 HKLM\SOFTWARE\Capture_Push
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Capture_Push")
        winreg.SetValueEx(key, "InstallPath", 0, winreg.REG_SZ, value_data)
        winreg.CloseKey(key)
        print(f"\n✅ 成功注册路径到注册表！")
        print(f"   键名: InstallPath")
        print(f"   路径: {value_data}")
    except PermissionError:
        print("\n❌ 权限不足！请以管理员身份运行此脚本。")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 写入注册表失败: {e}")
        sys.exit(1)

def delete_registry():
    """从注册表删除 Capture_Push 键"""
    try:
        # 尝试删除 HKLM\SOFTWARE\Capture_Push 及其子项
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Capture_Push")
        print("\n✅ 成功撤回注册表项！Capture_Push 键已删除。")
    except FileNotFoundError:
        print("\nℹ️  注册表中未找到 Capture_Push 键，无需撤回。")
    except PermissionError:
        print("\n❌ 权限不足！请以管理员身份运行此脚本。")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 撤回操作失败: {e}")
        sys.exit(1)

def ask_user_choice():
    """向用户提问并返回选择：'register' 或 'undo'"""
    print("🔧 Capture_Push 路径注册工具")
    print("此操作将修改系统环境变量（需管理员权限）。\n")
    
    while True:
        choice = input("请选择操作：\n"
                       "  [1] 注册路径到系统环境变量\n"
                       "  [2] 撤回已注册的路径\n"
                       "请输入 1 或 2: ").strip()
        
        if choice == "1":
            return "register"
        elif choice == "2":
            return "undo"
        else:
            print("⚠️  无效输入，请输入 1 或 2。\n")

def main():
    action = ask_user_choice()
    
    if action == "register":
        project_root = get_project_root()
        print(f"\n即将注册的项目根目录为:\n{project_root}\n")
        confirm = input("确认注册？(y/n): ").strip().lower()
        if confirm in ("y", "yes"):
            write_registry(project_root)
        else:
            print("操作已取消。")
    elif action == "undo":
        confirm = input("\n确认撤回 Capture_Push 注册项？(y/n): ").strip().lower()
        if confirm in ("y", "yes"):
            delete_registry()
        else:
            print("操作已取消。")

if __name__ == "__main__":
    # 检查是否在 Windows 上运行
    if not sys.platform.startswith('win'):
        print("❌ 此脚本仅支持 Windows 系统。")
        sys.exit(1)

    # === 新增：自动提权逻辑 ===
    if not is_admin():
        elevate_to_admin()  # 自动请求管理员权限并重启
    # =========================

    main()