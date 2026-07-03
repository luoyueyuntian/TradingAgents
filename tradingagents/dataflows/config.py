"""Thread-safe configuration store for the dataflows layer.

Uses ``contextvars.ContextVar`` so each thread (e.g. a concurrent web request)
gets its own isolated config without passing a dict through every function
signature.  ``set_config()`` / ``get_config()`` remain the public API; callers
do not need to change.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from typing import Any

import tradingagents.default_config as default_config

# Each context (thread / async task) gets its own config dict.  The default
# factory returns a fresh deep copy of DEFAULT_CONFIG on first access.
_config_var: ContextVar[dict[str, Any]] = ContextVar(
    "tradingagents_config",
    default=None,  # type: ignore[arg-type]  — sentinel, checked in _ensure
)

_SENTINEL = object()


def _ensure() -> dict[str, Any]:
    """Return the context-local config, initialising from defaults if needed."""
    cfg = _config_var.get(_SENTINEL)
    if cfg is _SENTINEL:
        cfg = deepcopy(default_config.DEFAULT_CONFIG)
        _config_var.set(cfg)
    return cfg


def initialize_config():
    """Reset the configuration to default values."""
    _config_var.set(deepcopy(default_config.DEFAULT_CONFIG))


def set_config(config: dict[str, Any]):
    """Update the configuration with custom values.

    Dict-valued keys (e.g. ``data_vendors``) are merged one level deep so a
    partial update like ``{"data_vendors": {"core_stock_apis": "alpha_vantage"}}``
    keeps the other nested keys from the default; scalar keys are replaced.
    """
    existing = _ensure()
    incoming = deepcopy(config)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            existing[key].update(value)
        else:
            existing[key] = value


def get_config() -> dict[str, Any]:
    """Get the current configuration (deep copy)."""
    return deepcopy(_ensure())
