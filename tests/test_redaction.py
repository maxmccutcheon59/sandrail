"""Redaction unit tests."""

from __future__ import annotations

from sandrail.redaction import REDACTED, assert_no_secret_leak, redact_text


def test_literal_secret_redacted():
    secret = "synth-secret-DO-NOT-USE-9f3a2c1b"
    text = f"leak {secret} end"
    out, changed = redact_text(text, [secret])
    assert changed
    assert secret not in out
    assert REDACTED in out
    assert assert_no_secret_leak(out, [secret]) == []


def test_sk_pattern_redacted():
    text = "key=sk-abcdefghijklmnopqrstuvwxyz012345"
    out, changed = redact_text(text)
    assert changed
    assert "sk-abcdef" not in out
    assert REDACTED in out


def test_env_secret_scrubbed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-testkeytestkeytestkey12")
    out, changed = redact_text("Authorization uses sk-testkeytestkeytestkey12 here")
    assert changed
    assert "sk-testkeytestkeytestkey12" not in out
