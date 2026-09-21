"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture
def fixture_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "synth-secret-DO-NOT-USE-9f3a2c1b"
    monkeypatch.setenv("SANDRAIL_FIXTURE_SECRET", secret)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return secret
