"""Browser-auth routes for TradingAgents Web."""

from __future__ import annotations

import os
import uuid
from contextlib import suppress
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from tradingagents.service.web_state import get_web_auth_db_path

from .mail import (
    PasswordResetEmail,
    password_reset_mail_available,
    send_password_reset_email,
)
from .passwords import (
    generate_verification_code,
    hash_password,
    hash_verification_code,
    validate_password_policy,
    verify_password,
    verify_verification_code,
)
from .schemas import (
    AuthLoginRequest,
    AuthMeResponse,
    AuthUser,
    ChangePasswordRequest,
    PasswordResetAvailability,
    PasswordResetConfirm,
    PasswordResetRequest,
)
from .user_store import PASSWORD_RESET_MAX_ATTEMPTS, UserRecord, UserStore

SESSION_COOKIE_NAME = "tradingagents_session"
SESSION_TTL_SECONDS = 43_200
INVALID_RESET_CODE_DETAIL = "Invalid or expired reset code"

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_store() -> UserStore:
    return UserStore(get_web_auth_db_path())


def _is_user_expired(user: UserRecord) -> bool:
    return user.expires_at is not None and datetime.fromisoformat(user.expires_at) <= datetime.now(
        timezone.utc
    )


def _ensure_user_can_login(user: UserRecord) -> None:
    if user.disabled:
        raise HTTPException(status_code=403, detail="User account is disabled")
    if _is_user_expired(user):
        raise HTTPException(status_code=403, detail="User account has expired")


def _password_reset_available() -> bool:
    return password_reset_mail_available()


def _invalid_reset_code_error() -> HTTPException:
    return HTTPException(status_code=400, detail=INVALID_RESET_CODE_DETAIL)


def _session_cookie_secure(request: Request) -> bool:
    override = os.environ.get("TRADINGAGENTS_SESSION_COOKIE_SECURE", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def _build_auth_user(user: UserRecord) -> AuthUser:
    return AuthUser(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        tenant_id=user.tenant_id,
        expires_at=user.expires_at,
        must_change_password=user.must_change_password,
    )


def _build_me_response(user: UserRecord, session_expires_at: str) -> AuthMeResponse:
    return AuthMeResponse(
        user=_build_auth_user(user),
        session_expires_at=session_expires_at,
        password_reset=PasswordResetAvailability(available=_password_reset_available()),
    )


def _get_current_session(request: Request):
    raw_session_id = request.cookies.get(SESSION_COOKIE_NAME, "").strip()
    if not raw_session_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    store = _get_store()
    session = store.get_session(raw_session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = store.get_user(session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return store, raw_session_id, session, user


def _lookup_password_reset_row(
    store: UserStore,
    token_id: str,
):
    with store._connect() as conn:  # noqa: SLF001
        return conn.execute(
            "SELECT * FROM password_reset_tokens WHERE id = ?",
            (token_id,),
        ).fetchone()


def _get_user_by_email(store: UserStore, email: str) -> UserRecord | None:
    target = email.casefold()
    for user in store.list_users():
        if user.email.casefold() == target:
            return user
    return None


@router.post("/login", response_model=AuthMeResponse)
def login(payload: AuthLoginRequest, request: Request, response: Response) -> AuthMeResponse:
    store = _get_store()
    user = store.get_user_by_identifier(payload.identifier)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _ensure_user_can_login(user)
    if not verify_password(payload.password, user.password_hash, user.password_salt):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    raw_session_id, session = store.create_session(user.id, ttl_seconds=SESSION_TTL_SECONDS)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_session_id,
        httponly=True,
        samesite="lax",
        secure=_session_cookie_secure(request),
        max_age=SESSION_TTL_SECONDS,
    )
    return _build_me_response(user, session.expires_at)


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, str]:
    raw_session_id = request.cookies.get(SESSION_COOKIE_NAME, "").strip()
    if raw_session_id:
        _get_store().delete_session(raw_session_id)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=_session_cookie_secure(request),
    )
    return {"status": "ok"}


@router.get("/me", response_model=AuthMeResponse)
def me(request: Request) -> AuthMeResponse:
    _store, _raw_session_id, session, user = _get_current_session(request)
    _ensure_user_can_login(user)
    return _build_me_response(user, session.expires_at)


@router.post("/change-password", response_model=AuthMeResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
) -> AuthMeResponse:
    store, _raw_session_id, session, user = _get_current_session(request)
    _ensure_user_can_login(user)
    if not verify_password(payload.old_password, user.password_hash, user.password_salt):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        validate_password_policy(
            payload.new_password,
            username=user.username,
            email=user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    password_record = hash_password(payload.new_password)
    updated = store.update_user(
        user.id,
        password_hash=password_record.encoded_hash,
        password_salt=password_record.salt,
        password_updated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        must_change_password=False,
    )
    store.record_audit_event(
        "auth.password_changed",
        actor_user_id=user.id,
        target_user_id=user.id,
        tenant_id=user.tenant_id,
    )
    return _build_me_response(updated, session.expires_at)


@router.post("/password-reset/request", response_model=PasswordResetAvailability)
def password_reset_request(payload: PasswordResetRequest) -> PasswordResetAvailability:
    if not _password_reset_available():
        return PasswordResetAvailability(
            available=False,
            reset_id=None,
            detail="Password reset is unavailable",
        )

    store = _get_store()
    user = _get_user_by_email(store, payload.email)
    fallback_reset_id = uuid.uuid4().hex
    if user is None or user.disabled or _is_user_expired(user):
        return PasswordResetAvailability(available=True, reset_id=fallback_reset_id)

    code = generate_verification_code()
    token = store.create_password_reset_token(user.id, hash_verification_code(code))
    send_password_reset_email(PasswordResetEmail(to_email=user.email, code=code))
    return PasswordResetAvailability(available=True, reset_id=token.id)


@router.post("/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirm) -> dict[str, str]:
    store = _get_store()
    row = _lookup_password_reset_row(store, payload.reset_id)
    if row is None:
        raise _invalid_reset_code_error()
    if row["used_at"] is not None:
        raise _invalid_reset_code_error()
    if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        raise _invalid_reset_code_error()
    if int(row["attempt_count"]) >= PASSWORD_RESET_MAX_ATTEMPTS:
        raise _invalid_reset_code_error()

    token = store.get_password_reset_token(payload.reset_id)
    if token is None:
        raise _invalid_reset_code_error()

    if not verify_verification_code(payload.code, token.code_hash):
        with suppress(ValueError):
            store.increment_password_reset_attempts(payload.reset_id)
        raise _invalid_reset_code_error()

    user = store.get_user(token.user_id)
    if user is None or user.disabled or _is_user_expired(user):
        raise _invalid_reset_code_error()
    try:
        validate_password_policy(
            payload.new_password,
            username=user.username,
            email=user.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        store.mark_password_reset_token_used(payload.reset_id)
    except ValueError as exc:
        raise _invalid_reset_code_error() from exc
    password_record = hash_password(payload.new_password)
    store.update_user(
        user.id,
        password_hash=password_record.encoded_hash,
        password_salt=password_record.salt,
        password_updated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        must_change_password=False,
    )
    store.record_audit_event(
        "auth.password_reset_confirmed",
        actor_user_id=user.id,
        target_user_id=user.id,
        tenant_id=user.tenant_id,
    )
    return {"status": "ok"}
