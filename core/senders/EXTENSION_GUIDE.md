# -*- coding: utf-8 -*-
"""
推送方式扩展说明

本文件演示如何添加新的推送方式。

## 添加新推送方式的步骤：

1. 在 core/senders 目录下创建新的发送器文件（如 wechat_sender.py）
2. 实现发送器类，包含 send(subject, content) 方法
3. 在 core/senders/__init__.py 中导出新的发送器
4. 在 core/push.py 的 NotificationManager._register_available_senders() 中注册新发送器
5. 在 config.ini 中添加新发送器的配置节（如 [wechat]）
6. 将 config.ini 中的 [push] method 设置为新的推送方式名称

## 示例：添加微信推送

### 1. 创建 core/senders/wechat_sender.py

```python
# -*- coding: utf-8 -*-
import configparser
import requests

try:
    from log import init_logger, get_config_path
except ImportError:
    from core.log import init_logger, get_config_path

_logger = None
_config_path = None

def _get_logger():
    global _logger, _config_path
    if _logger is None:
        _logger = init_logger('wechat_sender')
        _config_path = get_config_path()
    return _logger

def _get_config_path():
    global _config_path
    if _config_path is None:
        _get_logger()
    return _config_path

def load_wechat_config():
    logger = _get_logger()
    config_path = _get_config_path()
    cfg = configparser.ConfigParser()
    logger.info(f"加载配置文件: {config_path}")
    cfg.read(str(config_path), encoding="utf-8")
    return cfg

class WeChatSender:
    def send(self, subject, html_content):
        logger = _get_logger()
        logger.info(f"开始发送微信消息: {subject}")
        cfg = load_wechat_config()
        
        try:
            webhook_url = cfg.get("wechat", "webhook_url")
            # 企业微信或其他微信推送API实现
            # ...
            return True
        except Exception as e:
            logger.error(f"微信发送失败: {e}")
            return False
```

### 2. 更新 core/senders/__init__.py

```python
from .email_sender import EmailSender

# 尝试导入微信发送器（可选）
try:
    from .wechat_sender import WeChatSender
    __all__ = ['EmailSender', 'WeChatSender']
except ImportError:
    __all__ = ['EmailSender']
```

### 3. 在 core/push.py 中注册

在 `NotificationManager._register_available_senders()` 方法中添加：

```python
# 注册微信推送（如果可用）
try:
    from senders.wechat_sender import WeChatSender
    self.register_sender("wechat", WeChatSender())
except ImportError:
    logger.debug("微信发送器未安装")
except Exception as e:
    logger.warning(f"注册微信发送器失败: {e}")
```

### 4. 在 config.ini 中添加配置

```ini
[push]
method=wechat

[wechat]
webhook_url=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

## 支持的推送方式

当前已实现：
- none: 不推送
- email: 邮件推送

未来可扩展：
- wechat: 微信推送（企业微信机器人）
- dingtalk: 钉钉推送
- telegram: Telegram Bot
- slack: Slack Webhook
- custom: 自定义HTTP推送

## 注意事项

1. **延迟初始化**：所有发送器应使用延迟初始化模式，避免导入时立即访问配置文件
2. **错误处理**：发送器应妥善处理配置缺失和网络错误
3. **日志记录**：发送器应记录详细的调试信息，便于排查问题
4. **配置验证**：发送器应在发送前验证配置的完整性
5. **返回值**：send() 方法必须返回 bool 值表示成功或失败
"""
