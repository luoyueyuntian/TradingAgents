"""Session-only self service. Email changes require proof of mailbox ownership."""
from __future__ import annotations

import re
import smtplib
import sqlite3
import time
from contextlib import contextmanager
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth_routes import _build_me_response, _ensure_user_can_login, _get_current_session
from .mail import get_smtp_settings
from .passwords import generate_verification_code, hash_verification_code, verify_verification_code

router = APIRouter(prefix='/api/auth/profile', tags=['profile'])


class NicknameUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator('display_name')
    @classmethod
    def nickname(cls, value):
        if not value.strip():
            raise ValueError('昵称不能为空')
        return value.strip()


class EmailRequest(BaseModel):
    email: str = Field(max_length=254)

    @field_validator('email')
    @classmethod
    def email_address(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+', value):
            raise ValueError('请输入有效的邮箱地址')
        return value


class EmailConfirmation(BaseModel):
    code: str = Field(pattern=r'^\d{6}$')


@contextmanager
def profile_db(store):
    conn = sqlite3.connect(store.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('''CREATE TABLE IF NOT EXISTS email_changes (
            user_id TEXT PRIMARY KEY, email TEXT NOT NULL, code_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0
        )''')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def self_context(request):
    context = _get_current_session(request)
    _ensure_user_can_login(context[3])
    context[0].touch_session(context[1])
    return context


def send_email_change_code(address: str, code: str):
    settings = get_smtp_settings()
    if settings is None:
        raise RuntimeError('SMTP unavailable')
    message = EmailMessage()
    message['From'] = settings.from_email
    message['To'] = address
    message['Subject'] = 'TradingAgents 邮箱修改验证码 / Email verification'
    message.set_content(f'邮箱修改验证码 / Email verification code: {code}\n10 分钟内有效。若非本人操作，请忽略此邮件。\nExpires in 10 minutes. Ignore this email if you did not request it.')
    with smtplib.SMTP(settings.host, settings.port, timeout=10) as smtp:
        if settings.use_tls:
            smtp.starttls()
        if settings.username and settings.password:
            smtp.login(settings.username, settings.password)
        smtp.send_message(message)


@router.get('')
def get_profile(request: Request):
    store, _raw, current, user = self_context(request)
    now = int(time.time()*1000)
    with profile_db(store) as conn:
        sessions = conn.execute('SELECT * FROM sessions WHERE user_id=? AND expires_at>? ORDER BY created_at DESC', (user.account_id, now)).fetchall()
    return {
        'user': _build_me_response(user, current.expires_at).user,
        'created_at': user.created_at, 'password_updated_at': user.password_updated_at,
        'email_verification_available': get_smtp_settings() is not None,
        'sessions': [{'created_at': s['created_at'], 'last_seen_at': s['last_seen_at'], 'expires_at': s['expires_at'], 'current': s['id_hash']==current.id_hash} for s in sessions],
    }


@router.put('')
def update_profile(payload: NicknameUpdate, request: Request):
    store, _raw, current, user = self_context(request)
    store.update_account(user.account_id, display_name=payload.display_name)
    return _build_me_response(store.get_session_user(_raw), current.expires_at)


@router.post('/sessions/revoke-others')
def revoke_others(request: Request):
    store, _raw, current, user = self_context(request)
    with profile_db(store) as conn:
        count = conn.execute('DELETE FROM sessions WHERE user_id=? AND id_hash<>?', (user.account_id, current.id_hash)).rowcount
    return {'revoked': count}


def ensure_email_free(conn, user, email):
    if email.casefold() == user.email.casefold():
        raise HTTPException(400, '新邮箱与当前邮箱相同，请输入其他邮箱。')
    if conn.execute('SELECT 1 FROM accounts WHERE (lower(email)=? OR lower(username)=?) AND id<>?', (email, email, user.account_id)).fetchone():
        raise HTTPException(409, '该邮箱已被其他账号使用，请更换邮箱。')


@router.post('/email/request')
def request_email(payload: EmailRequest, request: Request):
    store, _raw, _current, user = self_context(request)
    if get_smtp_settings() is None:
        raise HTTPException(503, '管理员尚未配置邮件发送服务，暂时无法发送验证码。当前邮箱未改变。')
    now = int(time.time()*1000)
    with profile_db(store) as conn:
        ensure_email_free(conn, user, payload.email)
        pending = conn.execute('SELECT * FROM email_changes WHERE user_id=?', (user.account_id,)).fetchone()
        if pending and now - pending['created_at'] < 60_000:
            raise HTTPException(429, '验证码发送过于频繁，请等待 60 秒后再试。')
        code = generate_verification_code()
        code_hash = hash_verification_code(code)
        conn.execute('INSERT OR REPLACE INTO email_changes VALUES (?,?,?,?,?,0)', (user.account_id, payload.email, code_hash, now, now+600_000))
    try:
        send_email_change_code(payload.email, code)
    except Exception:
        with profile_db(store) as conn:
            conn.execute('DELETE FROM email_changes WHERE user_id=? AND code_hash=?', (user.account_id, code_hash))
        raise HTTPException(502, '验证码发送失败，请稍后重试或联系管理员。当前邮箱未改变。') from None
    return {'sent': True, 'expires_in': 600, 'resend_after': 60}


@router.post('/email/confirm')
def confirm_email(payload: EmailConfirmation, request: Request):
    store, _raw, current, user = self_context(request)
    now = int(time.time()*1000)
    invalid = False
    with profile_db(store) as conn:
        pending = conn.execute('SELECT * FROM email_changes WHERE user_id=?', (user.account_id,)).fetchone()
        if not pending or pending['expires_at'] <= now or pending['attempts'] >= 5:
            raise HTTPException(400, '验证码已过期或失效，请重新发送验证码。')
        if not verify_verification_code(payload.code, pending['code_hash']):
            conn.execute('UPDATE email_changes SET attempts=attempts+1 WHERE user_id=?', (user.account_id,))
            invalid = True
        else:
            ensure_email_free(conn, user, pending['email'])
            try:
                store._update_account_in_connection(conn, user.account_id, {'email': pending['email']})
            except (ValueError, sqlite3.IntegrityError) as exc:
                raise HTTPException(409, '该邮箱已被其他账号使用，请更换邮箱。') from exc
            conn.execute('DELETE FROM email_changes WHERE user_id=?', (user.account_id,))
            conn.execute('DELETE FROM password_reset_tokens WHERE user_id=?', (user.account_id,))
    if invalid:
        raise HTTPException(400, '验证码不正确，请检查新邮箱收到的最新验证码。连续错误 5 次后需重新发送。')
    store.record_audit_event('auth.email_changed', actor_user_id=user.id, target_user_id=user.id, tenant_id=user.tenant_id or None)
    return _build_me_response(store.get_session_user(_raw), current.expires_at)
