from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


class EmailSender:
    def send_code(self, email: str, code: str) -> None:
        message = MIMEText(f"你的验证码是：{code}，5 分钟内有效。")
        message["From"] = settings.from_email
        message["To"] = email
        message["Subject"] = "Mock Interview Agent 验证码"

        with smtplib.SMTP_SSL(settings.email_host, settings.email_port) as smtp:
            smtp.login(settings.from_email, settings.email_password)
            smtp.sendmail(settings.from_email, email, message.as_string())

