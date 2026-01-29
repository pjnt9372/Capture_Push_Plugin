# register_school.py
import os
import sys


def get_project_root():
    """获取项目根目录（developer_tools 的父目录）"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)


def register_school_module(school_code, school_name, module_path):
    """注册新学校模块到 SCHOOL_MODULES 映射表"""
    
    school_init_path = os.path.join(get_project_root(), "core", "school", "__init__.py")
    
    try:
        # 读取现有内容
        with open(school_init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 SCHOOL_MODULES 字典的开始和结束位置
        lines = content.split('\n')
        new_lines = []
        in_school_modules = False
        school_modules_indent = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('SCHOOL_MODULES = {'):
                in_school_modules = True
                school_modules_indent = len(line) - len(line.lstrip())
                new_lines.append(line)
            elif in_school_modules and line.strip() == "}" and len(line) - len(line.lstrip()) == school_modules_indent:
                # 在字典结束前插入新学校
                new_lines.append(f'{" " * (school_modules_indent + 4)}"{school_code}": "{module_path}",  # {school_name}')
                new_lines.append(line)
                in_school_modules = False
            elif in_school_modules and f'"{school_code}":' in line:
                # 如果学校代码已经存在，跳过这一行（替换旧条目）
                continue
            else:
                new_lines.append(line)
        
        # 写回文件
        with open(school_init_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        print(f"\n✅ 成功注册新院校到 SCHOOL_MODULES 映射表！")
        print(f"   院校代码: {school_code}")
        print(f"   院校名称: {school_name}")
        print(f"   模块路径: {module_path}")
        
    except Exception as e:
        print(f"\n❌ 注册新院校失败: {e}")
        sys.exit(1)


def main():
    print("🎓 Capture_Push 院校注册工具")
    print("此工具用于注册新院校模块。")
    print("")
    
    print("📝 注册新院校")
    school_code = input("请输入院校代码 (例如: 12345): ").strip()
    school_name = input("请输入院校名称 (例如: 测试大学): ").strip()
    module_path = input("请输入模块路径 (例如: core.school.12345): ").strip()
    
    if not school_code or not school_name or not module_path:
        print("❌ 院校代码、名称和模块路径不能为空！")
        sys.exit(1)
    
    print(f"\n即将注册新院校:\n"
          f"  院校代码: {school_code}\n"
          f"  院校名称: {school_name}\n"
          f"  模块路径: {module_path}")
    
    confirm = input("\n确认注册？(y/n): ").strip().lower()
    if confirm in ("y", "yes"):
        register_school_module(school_code, school_name, module_path)
    else:
        print("操作已取消。")


if __name__ == "__main__":
    # 检查是否在 Windows 上运行
    if not sys.platform.startswith('win'):
        print("❌ 此脚本仅支持 Windows 系统。")
        sys.exit(1)

    main()