"""Tests for file-based run claim helpers."""

from __future__ import annotations

from tradingagents.service.run_claims import acquire_run_claim, release_run_claim


def test_acquire_and_release_run_claim(tmp_path):
    claim = acquire_run_claim("run-1", claims_dir=tmp_path)
    assert claim is not None
    assert claim.exists()

    second = acquire_run_claim("run-1", claims_dir=tmp_path)
    assert second is None

    release_run_claim(claim)
    assert not claim.exists()


def test_release_run_claim_is_idempotent(tmp_path):
    claim = tmp_path / "run-1.lock"
    release_run_claim(claim)
    assert not claim.exists()
