"""Administrator tenant management routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, Request, status

from tradingagents.service.web_state import get_web_auth_db_path

from .admin_user_routes import (
    create_user_for_tenant,
    delete_user_for_tenant,
    list_users_for_tenant,
    update_user_for_tenant,
)
from .auth import get_request_user
from .schemas import (
    AdminTenantBatchDisableRequest,
    AdminTenantBatchDisableResponse,
    AdminTenantCreate,
    AdminTenantResponse,
    AdminTenantUpdate,
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
)
from .user_store import (
    DISABLED_TENANT_READ_ONLY_ERROR,
    EXPIRED_TENANT_READ_ONLY_ERROR,
    TenantRecord,
    UserRecord,
    UserStore,
    tenant_is_expired,
)

router = APIRouter(prefix="/api/admin/tenants", tags=["admin-tenants"])

def _get_store() -> UserStore:
    return UserStore(get_web_auth_db_path())


def _require_admin_user(request: Request) -> UserRecord:
    user = get_request_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _tenant_status(tenant: TenantRecord) -> str:
    if tenant.disabled:
        return "disabled"
    if tenant_is_expired(tenant):
        return "expired"
    return "active"


def _build_tenant_response(store: UserStore, tenant: TenantRecord) -> AdminTenantResponse:
    stats = store.get_tenant_stats(tenant.tenant_id)
    return AdminTenantResponse(
        id=tenant.id,
        tenant_id=tenant.tenant_id,
        display_name=tenant.display_name,
        disabled=tenant.disabled,
        expires_at=tenant.expires_at,
        status=_tenant_status(tenant),
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


def _get_writable_tenant(store: UserStore, tenant_id: str) -> TenantRecord:
    tenant = _get_existing_tenant(store, tenant_id)
    if tenant.disabled:
        raise HTTPException(status_code=400, detail=DISABLED_TENANT_READ_ONLY_ERROR)
    if tenant_is_expired(tenant):
        raise HTTPException(status_code=400, detail=EXPIRED_TENANT_READ_ONLY_ERROR)
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


def _parse_created_from(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    trimmed = value.strip()
    try:
        return int(trimmed)
    except ValueError:
        pass
    try:
        dt = datetime.strptime(trimmed, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="created_from must be a Unix millisecond timestamp or YYYY-MM-DD",
        ) from exc
    return int(dt.timestamp() * 1000)


def _parse_created_to(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    trimmed = value.strip()
    try:
        return int(trimmed)
    except ValueError:
        pass
    try:
        dt = datetime.strptime(trimmed, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="created_to must be a Unix millisecond timestamp or YYYY-MM-DD",
        ) from exc
    return int(dt.timestamp() * 1000) + 86_399_999


def _filter_tenants(
    tenants: list[TenantRecord],
    *,
    name: str | None = None,
    status_filter: str | None = None,
    created_from: int | None = None,
    created_to: int | None = None,
) -> list[TenantRecord]:
    normalized_name = (name or "").strip().casefold()
    normalized_status = (status_filter or "").strip().lower()
    if normalized_status and normalized_status not in {"active", "disabled", "expired"}:
        raise HTTPException(status_code=400, detail="status must be one of active, disabled, or expired")

    filtered: list[TenantRecord] = []
    for tenant in tenants:
        if normalized_name:
            haystack = f"{tenant.tenant_id} {tenant.display_name}".casefold()
            if normalized_name not in haystack:
                continue
        if normalized_status and _tenant_status(tenant) != normalized_status:
            continue
        if created_from is not None and tenant.created_at < created_from:
            continue
        if created_to is not None and tenant.created_at > created_to:
            continue
        filtered.append(tenant)
    return filtered


@router.get("", response_model=dict[str, list[AdminTenantResponse]])
def list_tenants(
    request: Request,
    name: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    created_from: str | None = None,
    created_to: str | None = None,
) -> dict[str, list[AdminTenantResponse]]:
    _require_admin_user(request)
    store = _get_store()
    tenants = _filter_tenants(
        store.list_tenants(),
        name=name,
        status_filter=status_filter,
        created_from=_parse_created_from(created_from),
        created_to=_parse_created_to(created_to),
    )
    return {"tenants": [_build_tenant_response(store, tenant) for tenant in tenants]}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict[str, AdminTenantResponse])
def create_tenant(payload: AdminTenantCreate, request: Request) -> dict[str, AdminTenantResponse]:
    _require_admin_user(request)
    store = _get_store()

    try:
        tenant = store.create_tenant_with_generated_id(
            display_name=payload.display_name,
            expires_at=payload.expires_at,
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

    try:
        tenant = store.update_tenant(tenant_id, **updates)
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return {"tenant": _build_tenant_response(store, tenant)}


@router.post("/batch-disable", response_model=AdminTenantBatchDisableResponse)
def batch_disable_tenants(
    payload: AdminTenantBatchDisableRequest,
    request: Request,
) -> AdminTenantBatchDisableResponse:
    _require_admin_user(request)
    store = _get_store()

    updated_count = 0
    skipped_tenant_ids: list[str] = []
    for tenant_id in payload.tenant_ids:
        tenant = _get_existing_tenant(store, tenant_id)
        if tenant.disabled or tenant_is_expired(tenant):
            skipped_tenant_ids.append(tenant.tenant_id)
            continue
        try:
            store.update_tenant(tenant.tenant_id, disabled=True)
            updated_count += 1
        except ValueError:
            skipped_tenant_ids.append(tenant.tenant_id)

    return AdminTenantBatchDisableResponse(
        updated_count=updated_count,
        skipped_count=len(skipped_tenant_ids),
        skipped_tenant_ids=skipped_tenant_ids,
    )


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
    _get_writable_tenant(store, tenant_id)
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
    _get_writable_tenant(store, tenant_id)
    return update_user_for_tenant(store, tenant_id, user_id, payload)


@router.delete("/{tenant_id}/users/{user_id}", response_model=dict[str, AdminUserResponse])
def delete_tenant_user(tenant_id: str, user_id: str, request: Request) -> dict[str, AdminUserResponse]:
    _require_admin_user(request)
    store = _get_store()
    _get_writable_tenant(store, tenant_id)
    return delete_user_for_tenant(store, tenant_id, user_id)
