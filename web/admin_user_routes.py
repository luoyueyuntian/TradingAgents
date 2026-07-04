"""Administrator user management routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from tradingagents.service.web_state import get_web_auth_db_path

from .auth import get_request_user
from .passwords import hash_password, validate_password_policy
from .schemas import AdminUserCreate, AdminUserResponse, AdminUserUpdate
from .user_store import UserRecord, UserStore

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])

_LAST_ADMIN_ERROR = "Cannot remove the last active admin from tenant"


def _get_store() -> UserStore:
    return UserStore(get_web_auth_db_path())


def _require_admin_user(request: Request) -> UserRecord:
    user = get_request_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _build_user_response(user: UserRecord) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        tenant_id=user.tenant_id,
        expires_at=user.expires_at,
        disabled=user.disabled,
        must_change_password=user.must_change_password,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


def _get_tenant_user(store: UserStore, tenant_id: str, user_id: str) -> UserRecord:
    user = store.get_user(user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _parse_expires_at(expires_at: str | None) -> datetime | None:
    if expires_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(expires_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="expires_at must be an offset-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=400, detail="expires_at must be an offset-aware ISO timestamp")
    return parsed


def _would_remove_last_active_admin(
    store: UserStore,
    tenant_id: str,
    user: UserRecord,
    payload: AdminUserUpdate | None = None,
) -> bool:
    if user.role != "admin" or user.disabled:
        return False
    if user.expires_at is not None and datetime.fromisoformat(user.expires_at) <= datetime.now(timezone.utc):
        return False
    if store.active_admin_count(tenant_id) != 1:
        return False
    if payload is None:
        return True
    if payload.role is not None and payload.role != "admin":
        return True
    if payload.disabled is True:
        return True
    if payload.expires_at is not None:
        expires_at = _parse_expires_at(payload.expires_at)
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            return True
    return False


def _map_store_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail in {"username already exists", "email already exists", "username or email already exists"}:
        status_code = 409
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=detail)


def list_users_for_tenant(store: UserStore, tenant_id: str) -> dict[str, list[AdminUserResponse]]:
    users = store.list_users(tenant_id=tenant_id)
    return {"users": [_build_user_response(user) for user in users]}


def create_user_for_tenant(
    store: UserStore,
    tenant_id: str,
    payload: AdminUserCreate,
) -> dict[str, AdminUserResponse]:
    try:
        validate_password_policy(
            payload.password,
            username=payload.username,
            email=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    password_record = hash_password(payload.password)
    try:
        user = store.create_user(
            username=payload.username,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            tenant_id=tenant_id,
            password_hash=password_record.encoded_hash,
            password_salt=password_record.salt,
            password_updated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            must_change_password=True,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return {"user": _build_user_response(user)}


def update_user_for_tenant(
    store: UserStore,
    tenant_id: str,
    user_id: str,
    payload: AdminUserUpdate,
) -> dict[str, AdminUserResponse]:
    target_user = _get_tenant_user(store, tenant_id, user_id)

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    if _would_remove_last_active_admin(store, tenant_id, target_user, payload):
        raise HTTPException(status_code=400, detail=_LAST_ADMIN_ERROR)

    if "password" in updates:
        try:
            validate_password_policy(
                payload.password or "",
                username=target_user.username,
                email=target_user.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        password_record = hash_password(payload.password or "")
        updates.pop("password")
        updates["password_hash"] = password_record.encoded_hash
        updates["password_salt"] = password_record.salt
        updates["password_updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        updates["must_change_password"] = True

    if "password_hash" in updates:
        try:
            updated_user = store.update_user_and_delete_sessions(user_id, **updates)
        except ValueError as exc:
            raise _map_store_error(exc) from exc
    else:
        try:
            updated_user = store.update_user(user_id, **updates)
        except ValueError as exc:
            raise _map_store_error(exc) from exc

    return {"user": _build_user_response(updated_user)}


def delete_user_for_tenant(store: UserStore, tenant_id: str, user_id: str) -> dict[str, AdminUserResponse]:
    target_user = _get_tenant_user(store, tenant_id, user_id)
    if _would_remove_last_active_admin(store, tenant_id, target_user):
        raise HTTPException(status_code=400, detail=_LAST_ADMIN_ERROR)
    try:
        deleted_user = store.delete_user(user_id)
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return {"user": _build_user_response(deleted_user)}


@router.get("", response_model=dict[str, list[AdminUserResponse]])
def list_users(request: Request) -> dict[str, list[AdminUserResponse]]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return list_users_for_tenant(store, admin_user.tenant_id)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict[str, AdminUserResponse])
def create_user(payload: AdminUserCreate, request: Request) -> dict[str, AdminUserResponse]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return create_user_for_tenant(store, admin_user.tenant_id, payload)


@router.patch("/{user_id}", response_model=dict[str, AdminUserResponse])
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    request: Request,
) -> dict[str, AdminUserResponse]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return update_user_for_tenant(store, admin_user.tenant_id, user_id, payload)


@router.delete("/{user_id}", response_model=dict[str, AdminUserResponse])
def delete_user(user_id: str, request: Request) -> dict[str, AdminUserResponse]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return delete_user_for_tenant(store, admin_user.tenant_id, user_id)
