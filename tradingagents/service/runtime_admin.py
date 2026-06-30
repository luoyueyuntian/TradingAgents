"""Runtime-maintenance helpers for checkpoint and memory discovery."""

from __future__ import annotations

from pathlib import Path

from tradingagents.agents.utils.memory import TradingMemoryLog


def _coerce_path(path: str | Path) -> Path:
    return Path(path).expanduser()


def _checkpoint_dir(state_root: str | Path) -> Path:
    return _coerce_path(state_root) / "cache" / "checkpoints"

def _memory_log_path(state_root: str | Path) -> Path:
    return _coerce_path(state_root) / "memory" / "trading_memory.md"


def list_runtime_checkpoints(*, state_root: str | Path) -> list[dict[str, object]]:
    """Return checkpoint DB files currently stored under tenant-shared cache."""
    items: list[dict[str, object]] = []
    checkpoint_dir = _checkpoint_dir(state_root)
    if not checkpoint_dir.exists():
        return items
    for db_path in sorted(checkpoint_dir.glob("*.db"), key=lambda entry: entry.name):
        items.append({
            "run_id": None,
            "ticker": db_path.stem,
            "path": str(db_path),
            "size_bytes": db_path.stat().st_size,
        })
    return items


def clear_runtime_checkpoints(*, state_root: str | Path, ticker: str | None = None) -> int:
    """Delete checkpoint DB files and return the number removed."""
    deleted = 0
    for item in list_runtime_checkpoints(state_root=state_root):
        if ticker is not None and str(item["ticker"]).upper() != ticker.upper():
            continue
        path = Path(str(item["path"]))
        if path.exists():
            path.unlink()
            deleted += 1
    return deleted


def list_runtime_memory_entries(*, state_root: str | Path) -> list[dict[str, object]]:
    """Return parsed decision-memory entries from the tenant-shared log."""
    items: list[dict[str, object]] = []
    log_path = _memory_log_path(state_root)
    if not log_path.exists():
        return items
    log = TradingMemoryLog({"memory_log_path": str(log_path)})
    for entry in log.load_entries():
        items.append({
            "run_id": None,
            "date": entry["date"],
            "ticker": entry["ticker"],
            "rating": entry["rating"],
            "pending": entry["pending"],
            "raw": entry["raw"],
            "alpha": entry["alpha"],
            "holding": entry["holding"],
            "decision": entry["decision"],
            "reflection": entry["reflection"],
        })
    items.sort(
        key=lambda item: (str(item["date"]), str(item["ticker"])),
        reverse=True,
    )
    return items


def clear_runtime_memory_logs(*, state_root: str | Path) -> int:
    """Delete the tenant-shared decision-memory log and return the number removed."""
    log_path = _memory_log_path(state_root)
    if not log_path.exists():
        return 0
    log_path.unlink()
    return 1
