"""Service-layer run state models."""

from __future__ import annotations

import asyncio
import datetime
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from tradingagents.graph.event_processor import (
    ChunkProcessor,
    build_agent_status_map,
    build_report_sections,
)
from tradingagents.service.runtime_context import RuntimeContext

TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled"}


class RunCancelledError(Exception):
    """Raised when a user cancels an in-flight run."""


@dataclass
class RunState:
    """In-memory state for a single analysis run."""

    run_id: str
    ticker: str
    date: str
    asset_type: str
    config: dict[str, Any]
    selected_analysts: list[str]
    runtime_context: RuntimeContext
    status: str = "pending"
    agents: dict[str, str] = field(default_factory=dict)
    report_sections: dict[str, str | None] = field(default_factory=dict)
    current_report: str | None = None
    final_report: str | None = None
    final_state: dict | None = None
    signal: str | None = None
    error: str | None = None
    report_path: str | None = None
    state_log_path: str | None = None
    event_log_path: str | None = None
    event_history: list[dict[str, Any]] = field(default_factory=list)
    queue_sequence: int | None = None
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)
    _chunk_processor: ChunkProcessor | None = field(default=None, repr=False)
    _event_subscribers: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = field(
        default_factory=dict,
        repr=False,
    )
    _subscriber_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.datetime.now().isoformat()
        self.agents = build_agent_status_map(self.selected_analysts)
        self.report_sections = build_report_sections(self.selected_analysts)
        self._chunk_processor = ChunkProcessor(self.selected_analysts)

    def subscribe_events(self) -> tuple[str, asyncio.Queue]:
        subscriber_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        with self._subscriber_lock:
            self._event_subscribers[subscriber_id] = (loop, queue)
        return subscriber_id, queue

    def unsubscribe_events(self, subscriber_id: str) -> None:
        with self._subscriber_lock:
            self._event_subscribers.pop(subscriber_id, None)

    def snapshot_event_subscribers(self) -> list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]:
        with self._subscriber_lock:
            return list(self._event_subscribers.values())
