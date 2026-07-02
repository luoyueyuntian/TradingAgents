"""SMTP helpers for TradingAgents Web mail delivery."""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str
    use_tls: bool


@dataclass(frozen=True)
class PasswordResetEmail:
    to_email: str
    code: str


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized not in {"0", "false", "no", "off"}


def get_smtp_settings() -> SMTPSettings | None:
    host = os.environ.get("TRADINGAGENTS_SMTP_HOST", "").strip()
    from_email = os.environ.get("TRADINGAGENTS_SMTP_FROM", "").strip()
    if not host or not from_email:
        return None
    port = int(os.environ.get("TRADINGAGENTS_SMTP_PORT", "587").strip() or "587")
    username = os.environ.get("TRADINGAGENTS_SMTP_USER", "").strip() or None
    password = os.environ.get("TRADINGAGENTS_SMTP_PASSWORD", "").strip() or None
    use_tls = _parse_bool(os.environ.get("TRADINGAGENTS_SMTP_TLS"), default=True)
    return SMTPSettings(
        host=host,
        port=port,
        username=username,
        password=password,
        from_email=from_email,
        use_tls=use_tls,
    )


def password_reset_mail_available() -> bool:
    return get_smtp_settings() is not None


def send_password_reset_email(message: PasswordResetEmail) -> None:
    settings = get_smtp_settings()
    if settings is None:
        raise RuntimeError("SMTP is not configured")

    email = EmailMessage()
    email["From"] = settings.from_email
    email["To"] = message.to_email
    email["Subject"] = "TradingAgents password reset code"
    email.set_content(
        "Use this verification code to reset your TradingAgents password: "
        f"{message.code}"
    )

    with smtplib.SMTP(settings.host, settings.port) as smtp:
        if settings.use_tls:
            smtp.starttls()
        if settings.username and settings.password:
            smtp.login(settings.username, settings.password)
        smtp.send_message(email)
