"""Persistent settings file management.

Reads and writes ``~/.tradingagents/settings.json`` so users can configure
API keys, LLM preferences, and data vendors through the web UI instead of
manually editing ``.env`` files.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SETTINGS_DIR = Path.home() / ".tradingagents"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"

# Maps LLM provider key → environment variable that holds its API key.
# ``None`` means the provider does not need an API key (e.g. ollama, bedrock).
PROVIDER_API_KEY_MAP: dict[str, str | None] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "qwen-cn": "DASHSCOPE_CN_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "glm-cn": "ZHIPU_CN_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "minimax-cn": "MINIMAX_CN_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "groq": "GROQ_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "openai_compatible": "OPENAI_COMPATIBLE_API_KEY",
    "ollama": None,
    "bedrock": None,
}

# All known API key env vars (for bulk export to os.environ).
ALL_API_KEY_ENV_VARS: list[str] = [
    v for v in PROVIDER_API_KEY_MAP.values() if v is not None
] + [
    "FRED_API_KEY",
    "AWS_DEFAULT_REGION",
    "AWS_PROFILE",
    "OLLAMA_BASE_URL",
]


def ensure_settings_dir() -> None:
    """Ensure the ``~/.tradingagents/`` directory exists."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    """Read settings.json and return its contents.

    Returns an empty dict if the file does not exist or is invalid JSON.
    """
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read settings file %s: %s", SETTINGS_PATH, exc)
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """Atomically write settings to disk.

    Writes to a temporary file first, then renames — avoids partial writes
    if the process is killed mid-save.
    """
    ensure_settings_dir()
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(SETTINGS_DIR), suffix=".tmp", prefix="settings_"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, str(SETTINGS_PATH))
    except OSError:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_setting(key_path: str, default: Any = None) -> Any:
    """Read a nested value using a dot-separated path.

    Example::

        get_setting("llm.provider", "openai")
    """
    settings = load_settings()
    keys = key_path.split(".")
    node = settings
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
        if node is None:
            return default
    return node


def set_setting(key_path: str, value: Any) -> None:
    """Write a nested value using a dot-separated path.

    Creates intermediate dicts as needed.
    """
    settings = load_settings()
    keys = key_path.split(".")
    node = settings
    for key in keys[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    node[keys[-1]] = value
    save_settings(settings)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    """Merge *patch* into the existing settings and save.

    Performs a one-level-deep merge for dict-valued keys (same semantics as
    ``set_config`` in dataflows/config.py).  Returns the merged settings.
    """
    existing = load_settings()
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(existing.get(key), dict):
            existing[key].update(value)
        else:
            existing[key] = value
    save_settings(existing)
    return existing


def export_api_keys_to_env() -> None:
    """Push API keys from settings.json into ``os.environ``.

    Only sets env vars that are **not already set** — explicit environment
    variables (and ``.env`` files loaded earlier) take precedence.
    """
    settings = load_settings()
    api_keys: dict[str, str] = settings.get("api_keys", {})
    for provider, key_name in PROVIDER_API_KEY_MAP.items():
        if key_name and api_keys.get(provider) and not os.environ.get(key_name):
            os.environ[key_name] = api_keys[provider]
    # Extra service keys
    for key_name in ("FRED_API_KEY", "AWS_DEFAULT_REGION", "AWS_PROFILE", "OLLAMA_BASE_URL"):
        val = api_keys.get(key_name.lower(), "")
        if val and not os.environ.get(key_name):
            os.environ[key_name] = val


def mask_api_keys(api_keys: dict[str, str]) -> dict[str, str]:
    """Return a copy where non-empty values are replaced with ``***``."""
    return {k: ("***" if v else "") for k, v in api_keys.items()}
