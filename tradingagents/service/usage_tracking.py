"""LLM usage aggregation helpers for one analysis run."""

from __future__ import annotations

import threading
from collections.abc import Callable
from copy import deepcopy
from typing import Any

try:  # pragma: no cover - import availability depends on runtime extras
    from langchain_core.callbacks import BaseCallbackHandler
except Exception:  # pragma: no cover - lightweight test/runtime fallback
    class BaseCallbackHandler:  # type: ignore[too-many-ancestors]
        """Fallback base so this module imports even without langchain installed."""


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return 0


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "items"):
        try:
            return dict(value.items())
        except Exception:
            return {}
    return {}


def _extract_token_usage(response: Any) -> dict[str, int]:
    llm_output = _as_mapping(getattr(response, "llm_output", None))
    candidates: list[dict[str, Any]] = []
    for key in ("token_usage", "usage"):
        candidate = _as_mapping(llm_output.get(key))
        if candidate:
            candidates.append(candidate)
    if llm_output:
        candidates.append(llm_output)

    for group in getattr(response, "generations", []) or []:
        generations = group if isinstance(group, list) else [group]
        for generation in generations:
            message = getattr(generation, "message", None)
            if message is None:
                continue
            usage_metadata = _as_mapping(getattr(message, "usage_metadata", None))
            if usage_metadata:
                candidates.append(usage_metadata)
            response_metadata = _as_mapping(getattr(message, "response_metadata", None))
            for key in ("token_usage", "usage", "usage_metadata"):
                candidate = _as_mapping(response_metadata.get(key))
                if candidate:
                    candidates.append(candidate)
            if response_metadata:
                candidates.append(response_metadata)

    for candidate in candidates:
        prompt_tokens = _coerce_int(
            candidate.get("prompt_tokens")
            or candidate.get("input_tokens")
            or candidate.get("prompt_token_count")
        )
        completion_tokens = _coerce_int(
            candidate.get("completion_tokens")
            or candidate.get("output_tokens")
            or candidate.get("completion_token_count")
        )
        total_tokens = _coerce_int(
            candidate.get("total_tokens")
            or candidate.get("total_token_count")
        )
        if total_tokens == 0 and (prompt_tokens or completion_tokens):
            total_tokens = prompt_tokens + completion_tokens
        if prompt_tokens or completion_tokens or total_tokens:
            return {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def _extract_model_name(response: Any) -> str:
    llm_output = _as_mapping(getattr(response, "llm_output", None))
    for key in ("model_name", "model", "model_id"):
        value = str(llm_output.get(key) or "").strip()
        if value:
            return value

    for group in getattr(response, "generations", []) or []:
        generations = group if isinstance(group, list) else [group]
        for generation in generations:
            message = getattr(generation, "message", None)
            if message is None:
                continue
            response_metadata = _as_mapping(getattr(message, "response_metadata", None))
            for key in ("model_name", "model", "model_id"):
                value = str(response_metadata.get(key) or "").strip()
                if value:
                    return value
    return ""


def _extract_response_preview(response: Any, *, max_chars: int = 320) -> str:
    for group in getattr(response, "generations", []) or []:
        generations = group if isinstance(group, list) else [group]
        for generation in generations:
            message = getattr(generation, "message", None)
            content = getattr(message, "content", None) if message is not None else getattr(generation, "text", None)
            if isinstance(content, str) and content.strip():
                text = content.strip()
                return text[: max_chars - 1] + "…" if len(text) > max_chars else text
            if isinstance(content, list):
                texts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(str(item.get("text") or ""))
                    elif isinstance(item, str):
                        texts.append(item)
                joined = "\n".join(part for part in texts if part).strip()
                if joined:
                    return joined[: max_chars - 1] + "…" if len(joined) > max_chars else joined
    return ""


def _extract_prompt_preview(messages: Any, *, max_chars: int = 320) -> str:
    batch = messages[0] if isinstance(messages, list) and messages and isinstance(messages[0], list) else messages
    if not isinstance(batch, list):
        return ""
    parts: list[str] = []
    for message in batch[-4:]:
        role = str(getattr(message, "type", getattr(message, "role", "message")) or "message")
        content = getattr(message, "content", "")
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text") or ""))
                elif isinstance(item, str):
                    texts.append(item)
            content_text = "\n".join(part for part in texts if part)
        else:
            content_text = str(content or "")
        content_text = content_text.strip()
        if not content_text:
            continue
        parts.append(f"{role}: {content_text}")
    joined = "\n".join(parts).strip()
    return joined[: max_chars - 1] + "…" if len(joined) > max_chars else joined


class RunUsageTracker(BaseCallbackHandler):
    """Aggregate one run's LLM usage and optionally emit per-call events."""

    raise_error = False

    def __init__(
        self,
        *,
        provider: str,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._provider = provider
        self._event_sink = event_sink
        self._lock = threading.Lock()
        self._summary: dict[str, Any] = {
            "provider": provider,
            "total_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": None,
            "calls_by_model": {},
            "tokens_by_model": {},
        }

    def on_chat_model_start(self, serialized, messages, **kwargs) -> None:  # pragma: no cover - exercised via runtime/tests
        if not callable(self._event_sink):
            return
        invocation_params = _as_mapping(kwargs.get("invocation_params"))
        model = str(
            invocation_params.get("model")
            or invocation_params.get("model_name")
            or _as_mapping(serialized).get("name")
            or "unknown"
        ).strip()
        payload = {
            "provider": self._provider,
            "model": model,
            "prompt_preview": _extract_prompt_preview(messages),
        }
        self._event_sink(payload)

    def on_llm_end(self, response, **kwargs) -> None:  # pragma: no cover - exercised via runtime/tests
        usage = _extract_token_usage(response)
        model = _extract_model_name(response) or "unknown"
        response_preview = _extract_response_preview(response)
        with self._lock:
            self._summary["total_calls"] += 1
            self._summary["prompt_tokens"] += usage["prompt_tokens"]
            self._summary["completion_tokens"] += usage["completion_tokens"]
            self._summary["total_tokens"] += usage["total_tokens"]
            calls_by_model = self._summary["calls_by_model"]
            calls_by_model[model] = int(calls_by_model.get(model, 0)) + 1
            tokens_by_model = self._summary["tokens_by_model"]
            model_tokens = tokens_by_model.setdefault(
                model,
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            model_tokens["prompt_tokens"] += usage["prompt_tokens"]
            model_tokens["completion_tokens"] += usage["completion_tokens"]
            model_tokens["total_tokens"] += usage["total_tokens"]
            event_payload = {
                "provider": self._provider,
                "model": model,
                "response_preview": response_preview,
                **usage,
            }
        if callable(self._event_sink):
            self._event_sink(deepcopy(event_payload))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._summary)
