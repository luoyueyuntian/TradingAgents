"""Administrator tenant management routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from tradingagents.service.web_state import get_web_auth_db_path

from .auth import get_request_user
from .passwords import hash_password, validate_password_policy
from .schemas import (
    AdminTenantCreate,
    AdminTenantResponse,
    AdminTenantUpdate,
)
from .user_store import TenantRecord, UserRecord, UserStore

router = APIRouter(prefix="/api/admin/tenants", tags=["admin-tenants"])


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
    tenant = store.get_tenant(tenant_id)
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
def list_tenants(request: Request) -> dict[str, list[AdminTenantResponse]]:
    _require_admin_user(request)
    store = _get_store()
    tenants = store.list_tenants()
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

    if store.get_user_by_identifier(payload.admin.username) is not None:
        raise HTTPException(status_code=409, detail="username already exists")
    if store.get_user_by_identifier(payload.admin.email) is not None:
        raise HTTPException(status_code=409, detail="email already exists")

    try:
        tenant = store.create_tenant(
            payload.tenant_id,
            display_name=payload.display_name,
        )
        password_record = hash_password(payload.admin.password)
        store.create_user(
            username=payload.admin.username,
            email=payload.admin.email,
            display_name=payload.admin.display_name,
            role="admin",
            tenant_id=tenant.tenant_id,
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
    _get_existing_tenant(store, tenant_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    try:
        tenant = store.update_tenant(tenant_id, **updates)
    except ValueError as exc:
        raise _map_store_error(exc) from exc
    return {"tenant": _build_tenant_response(store, tenant)}
