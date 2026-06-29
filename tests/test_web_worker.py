"""Tests for the standalone worker entrypoint helpers."""

from __future__ import annotations

from web import worker as worker_module


def test_get_worker_tenant_ids_uses_explicit_env_tenant(monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_WEB_TENANT_ID", "tenant-a")

    assert worker_module.get_worker_tenant_ids() == ["tenant-a"]


def test_get_worker_tenant_ids_includes_default_and_discovered(monkeypatch):
    monkeypatch.delenv("TRADINGAGENTS_WEB_TENANT_ID", raising=False)
    monkeypatch.setattr(worker_module, "list_web_tenant_ids", lambda: ["tenant-a", "tenant-b"])

    assert worker_module.get_worker_tenant_ids() == [None, "tenant-a", "tenant-b"]


def test_process_worker_iteration_calls_each_tenant_service(monkeypatch):
    calls: list[tuple[str | None, str]] = []

    class FakeService:
        def __init__(self, tenant_id):
            self.tenant_id = tenant_id

        def load_runs_index(self):
            calls.append((self.tenant_id, "load"))

        def resume_incomplete_runs(self):
            calls.append((self.tenant_id, "resume"))

        def process_next_queued_run(self):
            calls.append((self.tenant_id, "process"))
            return False

    monkeypatch.setattr(worker_module, "get_worker_tenant_ids", lambda: [None, "tenant-a"])
    monkeypatch.setattr(worker_module, "get_service", lambda tenant_id=None: FakeService(tenant_id))

    processed = worker_module.process_worker_iteration()

    assert processed is False
    assert calls == [
        (None, "load"),
        (None, "resume"),
        (None, "process"),
        ("tenant-a", "load"),
        ("tenant-a", "resume"),
        ("tenant-a", "process"),
    ]
