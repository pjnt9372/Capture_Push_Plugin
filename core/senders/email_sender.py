# -*- coding: utf-8 -*-
"""
邮件发送器实现
"""
import smtplib
import configparser
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart

# 导入统一日志模块和配置路径
try:
    from log import init_logger, get_config_path
    from config_manager import load_config
except ImportError:
    from core.log import init_logger, get_config_path
    from core.config_manager import load_config

# 延迟初始化日志（在第一次调用时初始化）
_logger = None
_config_path = None

def _get_logger():
    """Lazy initialization of logger"""
    global _logger, _config_path
    if _logger is None:
        _logger = init_logger('email_sender')
        _config_path = get_config_path()
    return _logger

def _get_config_path():
    """Get config path"""
    global _config_path
    if _config_path is None:
        _get_logger()  # 这会同时初始化 config_path
    return _config_path


def load_mail_config():
    """加载邮件配置"""
    logger = _get_logger()
    logger.info("加载并自动解密配置文件")
    return load_config()


class EmailSender:
    """邮件推送实现"""
    
    def send(self, subject, content):
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容（纯文本）
            
        Returns:
            bool: 发送是否成功
        """
        logger = _get_logger()
        logger.info(f"开始发送邮件: {subject}")
        cfg = load_mail_config()
        
        try:
            smtp = cfg.get("email", "smtp")
            port = cfg.getint("email", "port")
            sender = cfg.get("email", "sender")
            receiver = cfg.get("email", "receiver")
            auth = cfg.get("email", "auth")
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.error(f"邮件配置缺失: {e}")
            print(f"❌ 邮件配置缺失，请检查配置文件")
            return False
        
        logger.debug(f"SMTP服务器: {smtp}:{port}, 发件人: {sender}, 收件人: {receiver}")
        
        # 检测 Outlook 邮箱并拒绝发送
        outlook_domains = ["outlook.com", "outlook.cn", "outlook.com.cn", "hotmail.com", "live.com"]
        if any(sender.lower().endswith(domain) for domain in outlook_domains):
            logger.error(f"Outlook/Hotmail 邮箱不支持基本认证: {sender}")
            print(f"❌ Outlook/Hotmail 邮箱不支持基本认证")
            print(f"💡 原因: Microsoft 已禁用对这些邮箱的基本认证，仅支持 OAuth2")
            print(f"💡 解决方案: 请更换其他邮箱服务商（如 QQ、163、Gmail 等）")
            return False

        # 验证配置是否为空
        if not all([smtp, port, sender, receiver, auth]):
            logger.error(f"邮件配置验证失败: smtp='{smtp}', port='{port}', sender='{sender}', receiver='{receiver}', auth='{'*' * len(auth) if auth else ''}'")
            print(f"❌ 邮件配置验证失败，请检查配置文件")
            return False

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = Header(subject, "utf-8")

        msg.attach(MIMEText(content, "plain", "utf-8"))
        
        logger.debug(f"邮件消息构建完成，文本长度: {len(content)}")

        try:
            logger.debug(f"连接到 SMTP 服务器: {smtp}:{port}")
            
            # 根据端口选择连接方式
            if port == 465:
                # 端口 465 使用 SMTP_SSL（隐式 SSL）
                logger.debug("使用 SMTP_SSL 连接（端口 465）")
                server = smtplib.SMTP_SSL(smtp, port)
            else:
                # 端口 587 或其他端口使用 SMTP + starttls（显式 TLS）
                logger.debug(f"使用 SMTP + starttls 连接（端口 {port}）")
                server = smtplib.SMTP(smtp, port)
                logger.debug("开始 TLS 加密...")
                server.starttls()
            
            logger.debug("正在登录...")
            server.login(sender, auth)
            logger.debug("正在发送邮件...")
            logger.debug(f"收件人列表: {[receiver]}")
            logger.debug(f"邮件内容: {msg.as_string()[:500]}...")
            server.sendmail(sender, [receiver], msg.as_string())
            server.quit()
            logger.info(f"✅ 邮件发送成功: {subject}")
            print(f"✅ 邮件发送成功: {subject}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP 认证失败: {e}", exc_info=True)
            # 检查是否是 Office365 常见问题
            error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
            if "basic authentication is disabled" in error_msg.lower():
                print("❌ 认证失败: Office365 已禁用基本认证")
                print("💡 解决方案: 请使用应用密码而非账户密码")
                print("   1. 为您的账户启用两步验证")
                print("   2. 创建应用密码")
                print("   3. 在配置文件中使用应用密码")
            else:
                print(f"❌ SMTP 认证失败: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {e}", exc_info=True)
            print(f"❌ 邮件发送失败: {e}")
            return False
