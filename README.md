# Capture_Push 项目总体介绍

## 项目概述

Capture_Push 是一个课程成绩和课表自动追踪推送系统，能够自动获取学生课程成绩和课表信息，并通过邮件等方式推送更新通知。

## 核心功能

### 1. 成绩追踪
- **自动获取成绩**：定期从学校教务系统获取最新成绩信息
- **成绩变化检测**：智能检测成绩更新，仅在有变化时推送通知
- **循环检测**：支持配置循环检测间隔，可自定义检测频率

### 2. 课表追踪  
- **自动获取课表**：定期从学校教务系统获取课表信息
- **课表推送**：支持推送今日、明日及完整课表
- **循环检测**：支持课表循环检测功能

### 3. 推送通知
- **邮件推送**：通过邮件发送成绩和课表更新通知
- **推送管理**：支持多种推送方式的管理框架
- **推送记录**：完整的推送日志记录

### 4. 托盘程序
- **系统托盘**：后台运行的系统托盘程序
- **菜单操作**：通过托盘菜单执行各种操作
- **循环检测**：支持后台自动循环检测成绩和课表变化
- **配置管理**：便捷的配置界面和编辑功能

## 多院校支持

### 院校模块化
- **模块化设计**：支持多院校扩展，每个院校的抓取逻辑独立封装
- **动态加载**：系统根据配置自动加载对应的院校模块
- **统一接口**：所有院校模块遵循统一的API接口标准

### 开发新院校,以及新的操作模块

请参阅[开发指南](developer_tools/EXTENSION_GUIDE.md)
请参阅[ui开发指南](developer_tools/GUI_MODULAR_DESIGN.md)

## 技术特性

### 1. 日志系统
- **Python 日志**：所有 Python 模块包含完整的日志记录
- **C++ 日志**：托盘程序包含完整的日志记录
- **路径处理**：打包后自动使用用户可写目录存储日志
- **日志级别**：支持 INFO、DEBUG、ERROR、WARNING 等多个级别
- **日志打包**：支持将日志打包成ZIP文件便于故障排查

### 2. 依赖管理
- **uv 支持**：现代化依赖管理工具支持
- **requirements.txt**：标准依赖文件支持
- **虚拟环境**：完整的虚拟环境管理

### 3. 配置管理
- **配置文件**：支持 `config.ini` 配置文件
- **运行模式**：支持 DEV（开发）和 BUILD（生产）两种模式
- **加密存储**：配置文件中的敏感信息（如账号密码）使用 Windows DPAPI 加密存储
- **灵活配置**：支持账户、邮箱、循环检测等多种配置
- **导出功能**：用户可通过关于界面导出明文配置文件（需要输入教务系统密码）

## 用户界面功能

### 配置导出
- **明文导出**：在关于界面提供配置文件导出功能
- **安全验证**：导出配置需要输入教务系统登录密码
- **清除配置**：支持清除现有配置文件

## 项目结构

```
Capture_Push/
├── core/                   # 核心功能模块
│   ├── school/              # 院校模块根目录
│   │   ├── 10546/           # 衡阳师范学院模块
│   │   │   ├── getCourseGrades.py
│   │   │   ├── getCourseSchedule.py
│   │   │   └── __init__.py
│   │   └── __init__.py      # 院校管理入口
│   ├── senders/             # 推送发送器模块
│   │   ├── email_sender.py  # 邮件推送实现
│   │   ├── feishu_sender.py # 飞书机器人推送实现
│   │   ├── serverchan_sender.py # Server酱推送实现
│   │   └── __init__.py
│   ├── utils/               # 工具模块
│   │   └── dpapi.py         # Windows DPAPI加密实现
│   ├── config_manager.py    # 统一配置管理器（加密/解密）
│   ├── push.py              # 推送模块
│   ├── go.py                # 主执行模块
│   └── log.py               # 日志管理模块
├── gui/                     # GUI 界面模块
│   ├── gui.py               # GUI入口
│   ├── config_window.py     # 主配置窗口（含配置导出/清除功能）
│   ├── grades_window.py     # 成绩查看窗口
│   ├── schedule_window.py   # 课表查看窗口
│   ├── dialogs.py           # 对话框组件
│   └── widgets.py           # 自定义UI组件
├── tray/                    # 系统托盘程序
│   └── tray_app.cpp         # C++ 托盘程序
├── developer_tools/         # 开发者工具
│   ├── EXTENSION_GUIDE.md   # 扩展开发指南
│   ├── GUI_MODULAR_DESIGN.md # GUI模块化设计说明
│   ├── build.py             # 构建脚本
│   ├── register_or_undo.py  # 模块注册/注销脚本
│   └── changconfig.py       # 配置管理工具
├── .gitignore
├── Capture_Push_Lite_Setup.iss # Inno Setup 配置（轻量版）
├── Capture_Push_Setup.iss   # Inno Setup 配置（完整版）
├── ChineseSimplified.isl    # 中文语言文件
├── README.md                # 项目说明文档
├── config.ini               # 配置文件模板
├── config.md                # 配置文件详解
├── build_installer_exe.py   # 打包脚本
├── requirements.txt         # Python依赖
├── pyproject.toml           # 项目配置
└── uv.lock                  # 依赖锁定文件
```
```

## 安装与使用

### 开发环境安装
```bash
# 使用 uv 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/Scripts/activate  # Windows
# 或
source .venv/bin/activate      # Unix

# 安装依赖
uv pip install -r requirements.txt
```

### 构建与打包

如果你需要修改 C++ 托盘程序或重新打包程序：

1. **构建 C++ 托盘程序**
   ```bash
   cd tray
   # 重新配置项目 (Release 模式)
   cmake -B build -G "Visual Studio 17 2022" -A x64
   # 编译
   cmake --build build --config Release
   ```

2. **准备打包环境**
   运行脚本自动同步资源并准备隔离的构建空间：
   ```bash
   python developer_tools/build.py
   ```

3. **生成安装包**
   使用 Inno Setup 编译 `build/` 目录下的脚本：
   - 完整版：编译 `build\Capture_Push_Setup.iss`
   - 轻量版：编译 `build\Capture_Push_Lite_Setup.iss`

## 部署与打包

- **隔离运行**：程序自带嵌入式 Python 运行时，不依赖系统环境。
- **平滑更新**：支持覆盖安装，自动保留用户配置文件。
- **双版本分发**：提供包含环境的完整版和仅包含程序的轻量版。

## 日志与配置

程序运行产生的日志和配置文件存储在：
- `%LOCALAPPDATA%\Capture_Push` 

## 版本说明

- **对应版本**： 大于等于0.2.0