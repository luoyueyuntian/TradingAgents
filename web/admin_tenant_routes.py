"""Administrator tenant management routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from tradingagents.service.web_state import get_web_auth_db_path

from .admin_user_routes import (
    create_user_for_tenant,
    delete_user_for_tenant,
    list_users_for_tenant,
    update_user_for_tenant,
)
from .auth import get_request_user
from .passwords import hash_password, validate_password_policy
from .schemas import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    AdminTenantCreate,
    AdminTenantResponse,
    AdminTenantUpdate,
)
from .user_store import TenantRecord, UserRecord, UserStore

router = APIRouter(prefix="/api/admin/tenants", tags=["admin-tenants"])

_LAST_LOGIN_CAPABLE_ADMIN_TENANT_ERROR = (
    "Cannot disable or archive the last tenant with a login-capable admin"
)


def _get_store() -> UserStore:
    return UserStore(get_web_auth_db_path())


def _require_admin_user(request: Request) -> UserRecord:
    user = get_request_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _build_tenant_response(store: UserStore, tenant: TenantRecord) -> AdminTenantResponse:
    stats = store.get_tenant_stats(tenant.tenant_id)
    return AdminTenantResponse(
        id=tenant.id,
        tenant_id=tenant.tenant_id,
        display_name=tenant.display_name,
        disabled=tenant.disabled,
        archived=tenant.archived,
        user_count=stats["user_count"],
        active_admin_count=stats["active_admin_count"],
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


def _get_existing_tenant(store: UserStore, tenant_id: str) -> TenantRecord:
    try:
        tenant = store.get_tenant(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _map_store_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    if detail in {
        "tenant_id already exists",
        "username already exists",
        "email already exists",
        "username or email already exists",
    }:
        status_code = 409
    else:
        status_code = 400
    return HTTPException(status_code=status_code, detail=detail)


@router.get("", response_model=dict[str, list[AdminTenantResponse]])
def list_tenants(request: Request, include_archived: bool = False) -> dict[str, list[AdminTenantResponse]]:
    _require_admin_user(request)
    store = _get_store()
    tenants = store.list_tenants(include_archived=include_archived)
    return {"tenants": [_build_tenant_response(store, tenant) for tenant in tenants]}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict[str, AdminTenantResponse])
def create_tenant(payload: AdminTenantCreate, request: Request) -> dict[str, AdminTenantResponse]:
    _require_admin_user(request)
    store = _get_store()

    try:
        validate_password_policy(
            payload.admin.password,
            username=payload.admin.username,
            email=payload.admin.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        password_record = hash_password(payload.admin.password)
        tenant, _admin_user = store.create_tenant_with_initial_admin(
            tenant_id=payload.tenant_id,
            display_name=payload.display_name,
            username=payload.admin.username,
            email=payload.admin.email,
            admin_display_name=payload.admin.display_name,
            password_hash=password_record.encoded_hash,
            password_salt=password_record.salt,
            password_updated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            must_change_password=True,
        )
    except ValueError as exc:
        raise _map_store_error(exc) from exc

    return {"tenant": _build_tenant_response(store, tenant)}


@router.get("/{tenant_id}", response_model=dict[str, AdminTenantResponse])
def get_tenant(tenant_id: str, request: Request) -> dict[str, AdminTenantResponse]:
    _require_admin_user(request)
    store = _get_store()
    tenant = _get_existing_tenant(store, tenant_id)
    return {"tenant": _build_tenant_response(store, tenant)}


@router.patch("/{tenant_id}", response_model=dict[str, AdminTenantResponse])
def update_tenant(
    tenant_id: str,
    payload: AdminTenantUpdate,
    request: Request,
) -> dict[str, AdminTenantResponse]:
    _require_admin_user(request)
    store = _get_store()
    tenant = _get_existing_tenant(store, tenant_id)
    try:
        payload.require_non_null_fields()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    if (
        (updates.get("disabled") is True and not tenant.disabled)
        or (updates.get("archived") is True and not tenant.archived)
    ) and store.would_disable_last_login_capable_admin_tenant(tenant_id):
        raise HTTPException(status_code=400, detail=_LAST_LOGIN_CAPABLE_ADMIN_TENANT_ERROR)

    try:
        tenant = store.update_tenant(tenant_id, **updates)
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return {"tenant": _build_tenant_response(store, tenant)}


@router.get("/{tenant_id}/users", response_model=dict[str, list[AdminUserResponse]])
def list_tenant_users(tenant_id: str, request: Request) -> dict[str, list[AdminUserResponse]]:
    _require_admin_user(request)
    store = _get_store()
    _get_existing_tenant(store, tenant_id)
    return list_users_for_tenant(store, tenant_id)


@router.post("/{tenant_id}/users", status_code=status.HTTP_201_CREATED, response_model=dict[str, AdminUserResponse])
def create_tenant_user(
    tenant_id: str,
    payload: AdminUserCreate,
    request: Request,
) -> dict[str, AdminUserResponse]:
    _require_admin_user(request)
    store = _get_store()
    _get_existing_tenant(store, tenant_id)
    return create_user_for_tenant(store, tenant_id, payload)


@router.patch("/{tenant_id}/users/{user_id}", response_model=dict[str, AdminUserResponse])
def update_tenant_user(
    tenant_id: str,
    user_id: str,
    payload: AdminUserUpdate,
    request: Request,
) -> dict[str, AdminUserResponse]:
    _require_admin_user(request)
    store = _get_store()
    _get_existing_tenant(store, tenant_id)
    return update_user_for_tenant(store, tenant_id, user_id, payload)


@router.delete("/{tenant_id}/users/{user_id}", response_model=dict[str, AdminUserResponse])
def delete_tenant_user(tenant_id: str, user_id: str, request: Request) -> dict[str, AdminUserResponse]:
    _require_admin_user(request)
    store = _get_store()
    _get_existing_tenant(store, tenant_id)
    return delete_user_for_tenant(store, tenant_id, user_id)
