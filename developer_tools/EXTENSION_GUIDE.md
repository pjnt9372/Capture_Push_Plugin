# Capture_Push 扩展开发指南

本指南详细说明如何为 Capture_Push 系统添加新的**推送方式**和**院校支持模块**。

---

## 1. 如何注册一个新的推送模块 (Sender)

推送模块负责将格式化后的消息发送到特定的平台（如邮件、飞书、钉钉等）。

### 步骤：

1. **创建发送器文件**  
   在 `core/senders/` 目录下创建新的 Python 文件（例如 `dingtalk_sender.py`）。

2. **实现发送器类**  
   发送器类必须实现 `send(subject, content)` 方法。建议继承抽象基类或遵循相同的接口。
   ```python
   # core/senders/dingtalk_sender.py
   import requests
   from core.log import init_logger, get_config_path
   import configparser

   logger = init_logger('dingtalk_sender')

   class DingTalkSender:
       def send(self, subject, content):
           # 1. 加载配置
           cfg = configparser.ConfigParser()
           cfg.read(str(get_config_path()), encoding='utf-8')
           webhook = cfg.get("dingtalk", "webhook_url")
           
           # 2. 执行发送逻辑
           try:
               # 发送逻辑实现...
               return True
           except Exception as e:
               logger.error(f"发送失败: {e}")
               return False
   ```

3. **在 `core/push.py` 中注册**  
   修改 `NotificationManager._register_available_senders()` 方法：
   ```python
   # core/push.py
   def _register_available_senders(self):
       # ...
       try:
           from core.senders.dingtalk_sender import DingTalkSender
           self.register_sender("dingtalk", DingTalkSender())
       except Exception as e:
           logger.warning(f"注册钉钉发送器失败: {e}")
   ```

4. **更新配置文件和 GUI**  
   在 `config.ini` 中添加对应的配置节，并在 `gui/gui.py` 中添加对应的 UI 选项。

---

## 2. 如何创建一个新的院校模块 (School Module)

院校模块负责从教务系统抓取并解析成绩和课表数据。

### 步骤：

1. **确定院校代码**  
   选择一个唯一的代码（通常是教育部院校代码），在 `core/school/` 下创建同名文件夹（例如 `12345`）。

2. **创建必要文件**  
   在文件夹内创建 `__init__.py`, `getCourseGrades.py`, 和 `getCourseSchedule.py`。

3. **实现获取逻辑**
   - **成绩获取 (`getCourseGrades.py`)**: 必须导出 `fetch_grades(username, password, force_update=False)` 函数。
   - **课表获取 (`getCourseSchedule.py`)**: 必须导出 `fetch_course_schedule(username, password, force_update=False)` 函数。

4. **在 `__init__.py` 中导出接口**
   ```python
   # core/school/12345/__init__.py
   from .getCourseGrades import fetch_grades
   from .getCourseSchedule import fetch_course_schedule
   ```

5. **注册模块**  
   使用 `developer_tools/register_or_undo.py` 脚本注册新院校，或者手动在 `core/school/__init__.py` 的映射表中添加：
   ```python
   SCHOOL_MODULES = {
       "10546": "core.school.10546",
       "12345": "core.school.12345",  # 新增
   }
   ```

### 数据规范：
- **成绩数据**: 返回列表，每项为字典，必须包含 `课程名称`, `成绩`, `学分`, `课程属性`, `学期`。
- **课表数据**: 返回列表，每项为字典，必须包含 `星期` (1-7), `开始小节`, `结束小节`, `课程名称`, `教室`, `教师`, `周次列表` (int列表)。

---

## 3. 开发建议
- **日志**: 使用 `core.log.init_logger` 记录关键步骤。
- **配置**: 始终使用 `core.log.get_config_path()` 获取配置文件路径（兼容打包环境）。
- **环境**: 确保在 `requirements.txt` 中列出所有新增的依赖库。
