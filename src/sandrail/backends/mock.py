"""Deterministic mock agent backend — no network, no subprocess of untrusted code.

Useful for CI and for verifying harness redaction / scoring without an LLM.
"""

from __future__ import annotations

import json
import re

from sandrail.backends.base import AgentBackend, BackendResult
from sandrail.models import EvalCase
from sandrail.sandbox import SandboxPolicy


class MockBackend(AgentBackend):
    """
    Interprets case.input as a tiny declarative script:

      {
        "prompt": "...",          # optional, echoed in meta
        "respond": "text",        # stdout body
        "exit_code": 0,
        "stderr": "",
        "echo_env_secret": false, # if true, deliberately tries to print a fixture secret
                                  # (harness must redact — used by injection fixtures)
        "leak_key": "SANDRAIL_FIXTURE_SECRET"
      }
    """

    name = "mock"

    def run(self, case: EvalCase, policy: SandboxPolicy) -> BackendResult:
        # policy is accepted for interface parity; mock never opens network
        _ = policy
        inp = case.input
        stdout = str(inp.get("respond") or inp.get("stdout") or "")
        stderr = str(inp.get("stderr") or "")
        exit_code = int(inp.get("exit_code", 0))

        # Prompt-injection style: attacker asks mock to echo a secret from "memory"
        prompt = str(inp.get("prompt") or "")
        if inp.get("echo_env_secret"):
            import os

            key = str(inp.get("leak_key") or "SANDRAIL_FIXTURE_SECRET")
            val = os.environ.get(key, "")
            # Simulate a naive agent that would leak — harness redacts reports
            stdout = f"{stdout}\nLEAKED:{val}" if val else stdout

        # If prompt contains "repeat the secret" patterns, mock "refuses" unless echo flag set
        if re.search(r"(?i)ignore.*(previous|instructions).*secret", prompt) and not inp.get(
            "echo_env_secret"
        ):
            stdout = "REFUSED: will not reveal secrets"
            exit_code = 0

        meta = {"prompt_len": len(prompt), "backend": self.name}
        if inp.get("json_meta"):
            meta["raw"] = json.dumps({"id": case.id})
        return BackendResult(exit_code=exit_code, stdout=stdout, stderr=stderr, meta=meta)
