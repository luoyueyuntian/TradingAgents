"""Administrator user management routes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status

from tradingagents.service.timestamps import current_timestamp_ms
from tradingagents.service.web_state import get_web_auth_db_path

from .auth import get_request_user
from .passwords import hash_password, validate_password_policy
from .schemas import (
    AdminManagedUserCreate,
    AdminMembershipCreate,
    AdminUserBulkDeleteFailure,
    AdminUserBulkDeleteRequest,
    AdminUserBulkDeleteResult,
    AdminUserCreate,
    AdminUserCredentialResult,
    AdminUserResponse,
    AdminUserUpdate,
)
from .user_store import UserRecord, UserStore

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


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


def _get_tenant_user(
    store: UserStore,
    tenant_id: str,
    user_id: str,
    *,
    include_deleted: bool = False,
) -> UserRecord:
    user = store.get_user(user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="User not found")
    if user.deleted_at is not None and not include_deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _map_store_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail in {"username already exists", "email already exists", "username or email already exists"}:
        status_code = 409
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=detail)


def _generate_temporary_password(*, username: str, email: str) -> str:
    for _ in range(10):
        candidate = f"{secrets.token_urlsafe(12)}A1!"
        try:
            validate_password_policy(candidate, username=username, email=email)
        except ValueError:
            continue
        return candidate
    raise RuntimeError("Could not generate temporary password")


def list_users_for_tenant(
    store: UserStore,
    tenant_id: str,
    *,
    name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    status: str = "all",
    deleted_scope: str = "active",
) -> dict[str, list[AdminUserResponse]]:
    users = store.list_users(
        tenant_id=tenant_id,
        name=name,
        email=email,
        role=role,
        status=status,
        deleted_scope=deleted_scope,
    )
    return {"users": [_build_user_response(user) for user in users]}


def create_managed_user_for_tenant(
    store: UserStore,
    tenant_id: str,
    payload: AdminManagedUserCreate,
) -> AdminUserCredentialResult:
    existing = store.get_account_by_identifier(payload.email)
    temporary_password = _generate_temporary_password(username=payload.username, email=payload.email)
    password_record = hash_password(temporary_password)
    try:
        user = store.create_user(
            username=payload.username,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            tenant_id=tenant_id,
            password_hash=password_record.encoded_hash,
            password_salt=password_record.salt,
            password_updated_at=current_timestamp_ms(datetime.now(UTC)),
            must_change_password=True,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return AdminUserCredentialResult(
        user=_build_user_response(user),
        temporary_password="" if existing else temporary_password,
    )


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
            password_updated_at=current_timestamp_ms(datetime.now(UTC)),
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
    try:
        payload.require_non_null_fields()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    # Tenant admins manage memberships; shared identity belongs to the account.
    for field in ("email", "display_name"):
        if field in updates:
            if updates[field] != getattr(target_user, field):
                raise HTTPException(status_code=403, detail="Account identity must be changed by its owner")
            updates.pop(field)
    if "password" in updates:
        raise HTTPException(status_code=403, detail="Account password must be changed by its owner")
    if not updates:
        return {"user": _build_user_response(target_user)}

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
    _get_tenant_user(store, tenant_id, user_id)
    try:
        deleted_user = store.delete_user(user_id)
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return {"user": _build_user_response(deleted_user)}


@router.get("", response_model=dict[str, list[AdminUserResponse]])
def list_users(
    request: Request,
    name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    status: str = "all",
    deleted_scope: str = "active",
) -> dict[str, list[AdminUserResponse]]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    try:
        return list_users_for_tenant(
            store,
            admin_user.tenant_id,
            name=name,
            email=email,
            role=role,
            status=status,
            deleted_scope=deleted_scope,
        )
    except ValueError as exc:
        raise _map_store_error(exc) from exc


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AdminUserCredentialResult)
def create_user(payload: AdminManagedUserCreate, request: Request) -> AdminUserCredentialResult:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return create_managed_user_for_tenant(store, admin_user.tenant_id, payload)


def add_existing_membership(store: UserStore, tenant_id: str, payload: AdminMembershipCreate) -> AdminUserCredentialResult:
    account = store.get_account_by_identifier(payload.email)
    if account is None or account.email.casefold() != payload.email.casefold():
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        member = store.create_user(
            username=account.username, email=account.email, display_name=account.display_name,
            role=payload.role, tenant_id=tenant_id, expires_at=payload.expires_at,
            password_hash=account.password_hash, password_salt=account.password_salt,
            must_change_password=account.must_change_password,
        )
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return AdminUserCredentialResult(user=_build_user_response(member), temporary_password="")


@router.post("/memberships", status_code=201, response_model=AdminUserCredentialResult)
def add_member(payload: AdminMembershipCreate, request: Request):
    user = _require_admin_user(request)
    return add_existing_membership(_get_store(), user.tenant_id, payload)


@router.patch("/{user_id}", response_model=dict[str, AdminUserResponse])
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    request: Request,
) -> dict[str, AdminUserResponse]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return update_user_for_tenant(store, admin_user.tenant_id, user_id, payload)


@router.post("/{user_id}/reset-password", response_model=AdminUserCredentialResult)
def reset_user_password(user_id: str, request: Request) -> AdminUserCredentialResult:
    raise HTTPException(status_code=403, detail="Account password must be changed by its owner")


@router.delete("/{user_id}", response_model=dict[str, AdminUserResponse])
def delete_user(user_id: str, request: Request) -> dict[str, AdminUserResponse]:
    admin_user = _require_admin_user(request)
    store = _get_store()
    return delete_user_for_tenant(store, admin_user.tenant_id, user_id)


@router.post("/bulk-delete", response_model=AdminUserBulkDeleteResult)
def bulk_delete_users(payload: AdminUserBulkDeleteRequest, request: Request) -> AdminUserBulkDeleteResult:
    admin_user = _require_admin_user(request)
    store = _get_store()
    deleted_ids: list[str] = []
    failed: list[AdminUserBulkDeleteFailure] = []
    for user_id in payload.user_ids:
        try:
            delete_user_for_tenant(store, admin_user.tenant_id, user_id)
        except HTTPException as exc:
            failed.append(AdminUserBulkDeleteFailure(user_id=user_id, detail=str(exc.detail)))
        else:
            deleted_ids.append(user_id)
    return AdminUserBulkDeleteResult(deleted_ids=deleted_ids, failed=failed)
