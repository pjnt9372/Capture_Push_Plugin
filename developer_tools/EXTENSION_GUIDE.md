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
   from core.config_manager import load_config

   logger = init_logger('dingtalk_sender')

   class DingTalkSender:
       def send(self, subject, content):
           # 1. 加载配置（使用统一的配置管理器，自动处理加密）
           cfg = load_config()
           webhook = cfg.get("dingtalk", "webhook_url")
           
           # 2. 准备消息数据
           payload = {
               "msgtype": "text",
               "text": {
                   "content": f"{subject}\n\n{content}"
               }
           }
           
           # 3. 执行发送逻辑
           try:
               response = requests.post(webhook, json=payload, timeout=10)
               if response.status_code == 200:
                   result = response.json()
                   if result.get("errcode") == 0:
                       logger.info("钉钉消息发送成功")
                       return True
                   else:
                       logger.error(f"钉钉发送失败: {result}")
                       return False
               else:
                   logger.error(f"钉钉发送HTTP错误: {response.status_code}")
                   return False
           except Exception as e:
               logger.error(f"发送钉钉消息时发生异常: {e}")
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

### 配置文件示例：
在 `config.ini` 中添加：
```ini
[push]
method = dingtalk

[dingtalk]
webhook_url = https://oapi.dingtalk.com/robot/send?access_token=your_access_token
```

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

### 示例：成绩获取模块
```python
# core/school/12345/getCourseGrades.py

def fetch_grades(username, password, force_update=False):
    """
    获取成绩数据
    Args:
        username: 用户名
        password: 密码
        force_update: 是否强制更新
    
    Returns:
        list: 成绩数据列表，每项为包含课程信息的字典
    """
    # 登录逻辑...
    session = login(username, password)
    if not session:
        return None
    
    # 获取成绩页面
    grades_html = get_grade_html(session, force_update)
    if not grades_html:
        return None
    
    # 解析成绩
    return parse_grades(grades_html)

def parse_grades(html):
    """
    解析成绩HTML
    Args:
        html: 包含成绩信息的HTML内容
    
    Returns:
        list: 解析后的成绩数据列表
    """
    # 使用BeautifulSoup或其他工具解析HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    grades = []
    # 解析逻辑...
    # 每个成绩项应包含以下字段：
    grade_item = {
        "学期": "2023-2024-1",
        "课程名称": "高等数学",
        "成绩": "95",
        "学分": "4",
        "课程属性": "必修",
        "课程编号": "MATH101"
    }
    grades.append(grade_item)
    
    return grades
```

### 示例：课表获取模块
```python
# core/school/12345/getCourseSchedule.py

def fetch_course_schedule(username, password, force_update=False):
    """
    获取课表数据
    Args:
        username: 用户名
        password: 密码
        force_update: 是否强制更新
    
    Returns:
        list: 课表数据列表，每项为包含课程信息的字典
    """
    # 登录逻辑...
    session = login(username, password)
    if not session:
        return None
    
    # 获取课表页面
    schedule_html = get_schedule_html(session, force_update)
    if not schedule_html:
        return None
    
    # 解析课表
    return parse_schedule(schedule_html)

def parse_schedule(html):
    """
    解析课表HTML
    Args:
        html: 包含课表信息的HTML内容
    
    Returns:
        list: 解析后的课表数据列表
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    schedule = []
    # 解析逻辑...
    # 每个课程项应包含以下字段：
    course_item = {
        "星期": 1,  # 1-7，分别代表周一到周日
        "开始小节": 1,  # 第几节课开始
        "结束小节": 2,  # 第几节课结束
        "课程名称": "高等数学",
        "教室": "教学楼101",
        "教师": "张老师",
        "周次列表": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]  # 1-20周，或 ["全学期"]
    }
    schedule.append(course_item)
    
    return schedule
```

---

## 3. 配置管理与加密

### 配置文件加密
- 所有敏感配置（如密码、webhook URL、密钥等）都会自动使用 Windows DPAPI 加密存储
- 使用 `core.config_manager.load_config()` 加载配置，`core.config_manager.save_config()` 保存配置
- 配置文件路径统一使用 `core.log.get_config_path()` 获取

### 配置导出功能
- 用户可以通过 GUI 的"关于"界面导出明文配置文件
- 导出需要验证教务系统登录密码
- 验证通过后，将生成一个临时的明文配置文件供用户查看

---

## 4. 开发建议
- **日志**: 使用 `core.log.init_logger` 记录关键步骤。
- **配置**: 始终使用 `core.config_manager.load_config()` 获取配置（自动处理加密/解密）。
- **环境**: 确保在 `requirements.txt` 中列出所有新增的依赖库。
