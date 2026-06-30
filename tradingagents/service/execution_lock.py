"""Shared process-level execution lock for Web-triggered LLM work."""

from __future__ import annotations

import threading

# Provider credentials and a few runtime knobs still flow through process-wide
# ``os.environ``. Serialize web-triggered LLM execution until every downstream
# client is audited for true per-request isolation.
PROCESS_EXECUTION_LOCK = threading.Lock()
