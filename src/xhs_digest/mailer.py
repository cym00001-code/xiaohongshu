"""SMTP email sender for rendered digest messages."""

from __future__ import annotations

import os
import smtplib
import subprocess
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable, Sequence

from .config import EnvSettings


@dataclass(frozen=True, slots=True)
class SMTPConfig:
    """SMTP connection settings."""

    host: str
    port: int = 587
    username: str | None = None
    password: str | None = None
    sender: str | None = None
    use_tls: bool = True
    use_ssl: bool = False
    timeout_seconds: float = 20.0
    sendmail_path: str = "/usr/sbin/sendmail"

    @classmethod
    def from_env(cls, prefix: str = "SMTP_") -> "SMTPConfig":
        """Build config from environment variables without logging secrets."""

        return cls(
            host=os.environ[f"{prefix}HOST"],
            port=int(os.getenv(f"{prefix}PORT", "587")),
            username=os.getenv(f"{prefix}USERNAME"),
            password=os.getenv(f"{prefix}PASSWORD"),
            sender=os.getenv(f"{prefix}SENDER") or os.getenv(f"{prefix}USERNAME"),
            use_tls=_env_bool(f"{prefix}USE_TLS", True),
            use_ssl=_env_bool(f"{prefix}USE_SSL", False),
            timeout_seconds=float(os.getenv(f"{prefix}TIMEOUT_SECONDS", "20")),
        )


def build_email_message(
    *,
    subject: str,
    html: str,
    sender: str,
    recipients: Sequence[str],
    text: str | None = None,
) -> EmailMessage:
    """Create a multipart email message."""

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(text or _html_to_text(html))
    message.add_alternative(html, subtype="html")
    return message


def send_email(
    *,
    config: SMTPConfig,
    subject: str,
    html: str,
    recipients: Iterable[str],
    text: str | None = None,
) -> None:
    """Send an HTML email via SMTP."""

    recipient_list = [recipient for recipient in recipients if recipient]
    if not recipient_list:
        raise ValueError("At least one recipient is required.")
    sender = config.sender or config.username
    if not sender:
        raise ValueError("SMTP sender is required.")

    message = build_email_message(subject=subject, html=html, sender=sender, recipients=recipient_list, text=text)
    if config.host.lower() == "sendmail":
        _send_with_sendmail(config.sendmail_path, message, sender, recipient_list)
        return

    smtp_cls = smtplib.SMTP_SSL if config.use_ssl else smtplib.SMTP
    with smtp_cls(config.host, config.port, timeout=config.timeout_seconds) as smtp:
        if config.use_tls and not config.use_ssl:
            smtp.starttls()
        if config.username and config.password:
            smtp.login(config.username, config.password)
        smtp.send_message(message)


class SmtpMailer:
    """Small OO wrapper used by the CLI and scheduled job."""

    def __init__(self, config: SMTPConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls, env: EnvSettings) -> "SmtpMailer":
        return cls(
            SMTPConfig(
                host=env.smtp_host or "",
                port=env.smtp_port,
                username=env.smtp_user,
                password=env.smtp_password,
                sender=env.smtp_from,
                use_tls=env.smtp_use_tls,
                use_ssl=env.smtp_use_ssl,
                timeout_seconds=env.smtp_timeout_seconds,
            )
        )

    def send_html(self, *, subject: str, html: str, recipients: Iterable[str]) -> None:
        send_email(config=self.config, subject=subject, html=html, recipients=recipients)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _html_to_text(html: str) -> str:
    return " ".join(html.replace("<", " <").replace(">", "> ").split())


def _send_with_sendmail(path: str, message: EmailMessage, sender: str, recipients: Sequence[str]) -> None:
    command = [path, "-f", sender, *recipients]
    subprocess.run(command, input=message.as_bytes(), check=True)
