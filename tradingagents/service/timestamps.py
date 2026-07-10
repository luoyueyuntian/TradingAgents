"""Helpers for normalizing persisted timestamps to Unix milliseconds."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_SECONDS_CUTOFF = 10_000_000_000


def _normalize_numeric_timestamp(value: int | float) -> int:
    normalized = int(value)
    if abs(normalized) < _SECONDS_CUTOFF:
        return normalized * 1000
    return normalized


def current_timestamp_ms(now: datetime | None = None) -> int:
    resolved = now or datetime.now()
    return int(resolved.timestamp() * 1000)


def local_timestamp_text(now: datetime | None = None) -> str:
    resolved = now or datetime.now().astimezone()
    if resolved.tzinfo is None:
        resolved = resolved.astimezone()
    return resolved.strftime("%Y-%m-%d %H:%M:%S")


def coerce_timestamp_ms(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _normalize_numeric_timestamp(value)
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            return _normalize_numeric_timestamp(int(trimmed))
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(trimmed.replace("Z", "+00:00"))
        except ValueError:
            return None
        return int(parsed.timestamp() * 1000)
    return None


def require_timestamp_ms(value: Any, *, field_name: str) -> int:
    normalized = coerce_timestamp_ms(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be a Unix millisecond timestamp")
    return normalized


def timestamp_ms_to_datetime(value: Any) -> datetime | None:
    normalized = coerce_timestamp_ms(value)
    if normalized is None:
        return None
    return datetime.fromtimestamp(normalized / 1000)


def timestamp_ms_to_date_text(value: Any) -> str | None:
    resolved = timestamp_ms_to_datetime(value)
    if resolved is None:
        return None
    return resolved.date().isoformat()


def timestamp_ms_to_filename_text(value: Any) -> str:
    resolved = timestamp_ms_to_datetime(value) or datetime.now()
    return resolved.strftime("%Y-%m-%dT%H-%M-%S")
