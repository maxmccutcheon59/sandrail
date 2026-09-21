"""Optional OpenAI-compatible local API hook (secrets via env only).

Only activates when OPENAI_BASE_URL is set. Uses stdlib urllib — no SDK required.
Does NOT train models. Network is required for this backend; the CLI still
defaults to deny-network for other backends.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from sandrail import __version__
from sandrail.backends.base import AgentBackend, BackendResult
from sandrail.models import EvalCase
from sandrail.sandbox import SandboxPolicy

# SSRF mitigation: only loopback / explicitly configured base URL host is used.
# We do not accept per-case URL overrides.


def _base_url() -> str | None:
    return os.environ.get("OPENAI_BASE_URL") or None


class OpenAICompatBackend(AgentBackend):
    name = "openai"

    def __init__(self, *, require_base_url: bool = True) -> None:
        self.require_base_url = require_base_url

    def run(self, case: EvalCase, policy: SandboxPolicy) -> BackendResult:
        base = _base_url()
        if not base:
            return BackendResult(
                exit_code=2,
                stdout="",
                stderr=(
                    "OPENAI_BASE_URL is not set. This backend only calls a local "
                    "OpenAI-compatible API when explicitly configured via env."
                ),
                meta={"skipped": True},
            )

        if not policy.allow_network:
            return BackendResult(
                exit_code=126,
                stdout="",
                stderr=(
                    "openai backend requires network; re-run with --allow-network "
                    "(still uses only OPENAI_BASE_URL from the environment)"
                ),
                meta={"sandbox_denied": True},
            )

        api_key = os.environ.get("OPENAI_API_KEY", "")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        prompt = str(case.input.get("prompt") or case.input.get("message") or "")
        system = str(case.input.get("system") or "You are a careful eval assistant.")

        url = base.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(case.input.get("temperature", 0)),
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"sandrail/{__version__}",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        timeout = case.timeout_sec if case.timeout_sec is not None else policy.timeout_sec
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL from env only
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            return BackendResult(
                exit_code=1,
                stdout="",
                stderr=f"HTTP {exc.code}: {err_body[:500]}",
                meta={"http_error": exc.code},
            )
        except Exception as exc:  # network / timeout
            return BackendResult(
                exit_code=1,
                stdout="",
                stderr=f"request failed: {type(exc).__name__}",
                meta={"error": type(exc).__name__},
            )

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError):
            return BackendResult(
                exit_code=1,
                stdout=raw[:2000],
                stderr="unexpected API response shape",
                meta={},
            )

        return BackendResult(exit_code=0, stdout=str(content), stderr="", meta={"model": model})
