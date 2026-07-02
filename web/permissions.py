"""Central request permission rules for TradingAgents Web."""

from __future__ import annotations

ROLE_ORDER = {
    "viewer": 0,
    "analyst": 1,
    "admin": 2,
}

_ADMIN_PREFIXES = (
    "/api/settings",
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


def is_public_path(path: str, method: str) -> bool:
    normalized_method = method.upper()
    if normalized_method == "OPTIONS":
        return True
    if not path.startswith("/api/"):
        return True
    return path.startswith("/api/auth/")


def required_role_for_request(path: str, method: str) -> str | None:
    if is_public_path(path, method):
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
