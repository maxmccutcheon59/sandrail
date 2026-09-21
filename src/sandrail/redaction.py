"""Secret redaction for harness logs — never leak fixture/env secrets into reports."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable

# Patterns that look like API keys / bearer tokens / common secret shapes.
_DEFAULT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"(?i)bearer\s+[a-z0-9\-._~+/]+=*"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)openai[_-]?api[_-]?key\s*[:=]\s*\S+"),
]

REDACTED = "[REDACTED]"


def _env_secret_values() -> list[str]:
    """Collect non-empty values from known secret env var names (for scrubbing)."""
    names = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "API_KEY",
        "SECRET_TOKEN",
        "SANDRAIL_FIXTURE_SECRET",
    )
    out: list[str] = []
    for name in names:
        val = os.environ.get(name)
        if val and len(val) >= 4:
            out.append(val)
    return out


def redact_text(
    text: str,
    extra_secrets: Iterable[str] | None = None,
    *,
    patterns: list[re.Pattern[str]] | None = None,
) -> tuple[str, bool]:
    """
    Return (possibly redacted text, whether any redaction occurred).

    Literal secret strings (from expect.secrets_must_not_leak, env) are replaced first,
    then regex patterns.
    """
    if not text:
        return text, False
    changed = False
    out = text

    secrets: list[str] = []
    if extra_secrets:
        secrets.extend(s for s in extra_secrets if s)
    secrets.extend(_env_secret_values())
    # Longest first so substrings don't leave fragments
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret and secret in out:
            out = out.replace(secret, REDACTED)
            changed = True

    for pat in patterns if patterns is not None else _DEFAULT_PATTERNS:
        new_out, n = pat.subn(REDACTED, out)
        if n:
            out = new_out
            changed = True

    return out, changed


def assert_no_secret_leak(text: str, secrets: Iterable[str]) -> list[str]:
    """Return list of secret identifiers that still appear in text (should be empty)."""
    leaks: list[str] = []
    for secret in secrets:
        if secret and secret in text:
            # Don't echo the secret back — report a short fingerprint only
            leaks.append(f"secret_leak(len={len(secret)}, prefix={secret[:2]}…)")
    return leaks
