"""Central request permission rules for TradingAgents Web."""

from __future__ import annotations

ROLE_ORDER = {
    "viewer": 0,
    "analyst": 1,
    "admin": 2,
}

_ADMIN_PREFIXES = (
    "/api/settings",
    "/api/system/settings",
    "/api/system/tenants",
    "/api/system/checkpoints",
    "/api/system/memory",
    "/api/admin/",
)
_PASSWORD_CHANGE_ALLOWED = {
    ("GET", "/api/auth/me"),
    ("POST", "/api/auth/change-password"),
    ("POST", "/api/auth/logout"),
}
_PUBLIC_AUTH_PATHS = {
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/auth/password-reset/request"),
    ("POST", "/api/auth/password-reset/confirm"),
}


def is_public_path(path: str, method: str) -> bool:
    normalized_method = method.upper()
    if normalized_method == "OPTIONS":
        return True
    if not path.startswith("/api/"):
        return True
    return (normalized_method, path) in _PUBLIC_AUTH_PATHS


def is_auth_path(path: str, method: str) -> bool:
    normalized = (method.upper(), path)
    return normalized in _PUBLIC_AUTH_PATHS or normalized in _PASSWORD_CHANGE_ALLOWED


def required_role_for_request(path: str, method: str) -> str | None:
    if is_public_path(path, method) or is_auth_path(path, method):
        return None
    if path.startswith(_ADMIN_PREFIXES):
        return "admin"
    if method.upper() in {"GET", "HEAD"}:
        return "viewer"
    return "analyst"


def has_required_role(user_role: str, required_role: str | None) -> bool:
    if required_role is None:
        return True
    return ROLE_ORDER[user_role] >= ROLE_ORDER[required_role]


def is_password_change_allowed_path(path: str, method: str) -> bool:
    return (method.upper(), path) in _PASSWORD_CHANGE_ALLOWED
