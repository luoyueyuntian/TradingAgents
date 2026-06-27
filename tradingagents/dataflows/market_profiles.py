"""Market-profile helpers.

Profiles let the same high-level tool surface adopt different data semantics
without rewriting the graph. ``default`` preserves the current behavior;
``cn_a`` switches selected vendor defaults to mainland-China-aware sources.
"""

from __future__ import annotations

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.config import get_config

DEFAULT_PROFILE = "default"
CHINA_A_PROFILE = "cn_a"

CHINA_A_VENDOR_DEFAULTS = {
    "news_data": "cn_news",
    "macro_data": "cn_macro",
    "prediction_markets": "cn_market_signals",
}


def normalize_market_profile(profile: str | None) -> str:
    """Return a normalized market profile value."""
    if not isinstance(profile, str):
        return DEFAULT_PROFILE
    cleaned = profile.strip().lower()
    return cleaned or DEFAULT_PROFILE


def get_market_profile() -> str:
    """Return the active runtime market profile."""
    return normalize_market_profile(get_config().get("market_profile"))


def is_china_a_profile(profile: str | None) -> bool:
    """True when the profile selects mainland-China market semantics."""
    return normalize_market_profile(profile) == CHINA_A_PROFILE


def get_profile_data_vendors(profile: str | None) -> dict[str, str]:
    """Vendor defaults implied by ``profile``.

    The returned dict only contains profile-specific overrides, not a full copy
    of the global defaults.
    """
    if is_china_a_profile(profile):
        return dict(CHINA_A_VENDOR_DEFAULTS)
    return {}


def uses_builtin_vendor_default(category: str, configured_vendor: str) -> bool:
    """Whether ``configured_vendor`` is still the repo's built-in default.

    This lets a market profile override only untouched defaults while preserving
    explicit tool-level overrides and category-level non-default user choices.
    """
    default_vendors = DEFAULT_CONFIG.get("data_vendors", {})
    return default_vendors.get(category) == configured_vendor
