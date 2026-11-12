from contextlib import contextmanager
from contextvars import Context, ContextVar, copy_context
from copy import deepcopy

import tradingagents.default_config as default_config

# Use default config but allow it to be overridden
_config_var: ContextVar[dict | None] = ContextVar("tradingagents_config", default=None)

# The config of the run in progress. A graph binds its own for the length of a
# run, so the data tools it calls read that graph's vendors even when several
# graphs share a process. LangGraph carries the context into tool calls.
_run_config: ContextVar[dict | None] = ContextVar("tradingagents_run_config", default=None)


def initialize_config():
    """Initialize the configuration with default values."""
    _config_var.set(deepcopy(default_config.DEFAULT_CONFIG))


def _merge(base: dict, config: dict) -> dict:
    """Merge ``config`` into ``base``: dict-valued keys one level deep, scalars replaced."""
    for key, value in deepcopy(config).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value
    return base


def set_config(config: dict):
    """Update the configuration with custom values.

    Dict-valued keys (e.g. ``data_vendors``) are merged one level deep so a
    partial update like ``{"data_vendors": {"core_stock_apis": "alpha_vantage"}}``
    keeps the other nested keys from the default; scalar keys are replaced.
    """
    if _config_var.get() is None:
        initialize_config()
    _config_var.set(_merge(deepcopy(_config_var.get()), config))


@contextmanager
def run_config(config: dict):
    """Serve ``config``, over the defaults, to every read made inside the block."""
    token = _run_config.set(_merge(deepcopy(default_config.DEFAULT_CONFIG), config))
    try:
        yield
    finally:
        _run_config.reset(token)


def run_config_context(config: dict) -> Context:
    """A context serving ``config``, over the defaults, to every read run in it.

    For a run that yields between steps, where a ``run_config`` block would
    stay open in the caller's context while it holds the results.
    """
    context = copy_context()
    context.run(_run_config.set, _merge(deepcopy(default_config.DEFAULT_CONFIG), config))
    return context


def get_config() -> dict:
    """Get the configuration of the run in progress, else the context-local one."""
    scoped = _run_config.get()
    if scoped is not None:
        return deepcopy(scoped)
    if _config_var.get() is None:
        initialize_config()
    return deepcopy(_config_var.get())


initialize_config()
