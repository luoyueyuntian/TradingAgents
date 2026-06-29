"""Standalone worker entrypoint for external-worker mode."""

from __future__ import annotations

import os
import time

from tradingagents.service.web_state import list_web_tenant_ids

from .runner import get_service


def get_worker_tenant_ids() -> list[str | None]:
    """Return the tenant namespaces this worker should process."""
    explicit = os.environ.get("TRADINGAGENTS_WEB_TENANT_ID", "").strip()
    if explicit:
        return [explicit]
    return [None, *list_web_tenant_ids()]


def process_worker_iteration() -> bool:
    """Process one polling iteration across all configured tenants."""
    processed_any = False
    for tenant_id in get_worker_tenant_ids():
        service = get_service(tenant_id)
        service.load_runs_index()
        service.resume_incomplete_runs()
        processed_any = service.process_next_queued_run() or processed_any
    return processed_any


def main() -> None:
    """Run the polling worker loop."""
    while True:
        processed = process_worker_iteration()
        if processed:
            continue
        time.sleep(1.0)


if __name__ == "__main__":
    main()
