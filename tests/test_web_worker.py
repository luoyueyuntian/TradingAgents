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


def test_process_worker_iteration_invokes_one_time_task_processing(monkeypatch):
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

    monkeypatch.setattr(worker_module, "get_worker_tenant_ids", lambda: [None])
    monkeypatch.setattr(worker_module, "get_service", lambda tenant_id=None: FakeService(tenant_id))
    monkeypatch.setattr(
        worker_module,
        "process_due_automation_rules",
        lambda tenant_id=None, start_worker=False: calls.append((tenant_id, "automations")),
    )
    monkeypatch.setattr(
        worker_module,
        "refresh_one_time_tasks",
        lambda tenant_id=None: calls.append((tenant_id, "refresh-one-time")),
    )
    monkeypatch.setattr(
        worker_module,
        "process_due_one_time_tasks",
        lambda tenant_id=None, start_worker=False: calls.append((tenant_id, "process-one-time")),
    )
    monkeypatch.setattr(
        worker_module,
        "process_pending_webhook_notifications",
        lambda tenant_id=None: calls.append((tenant_id, "webhooks")),
    )

    worker_module.process_worker_iteration()

    assert calls == [
        (None, "load"),
        (None, "resume"),
        (None, "automations"),
        (None, "refresh-one-time"),
        (None, "process-one-time"),
        (None, "webhooks"),
        (None, "process"),
    ]
