"""Allow-listed subprocess agent backend (argument arrays only)."""

from __future__ import annotations

import subprocess

from sandrail.backends.base import AgentBackend, BackendResult
from sandrail.models import EvalCase
from sandrail.sandbox import SandboxError, SandboxPolicy, run_sandboxed


class SubprocessBackend(AgentBackend):
    """
    Runs case.input["argv"] as an argument array under the sandbox.

    Example input:
      { "argv": ["python3", "-c", "print('ok')"], "cwd": "." }
    """

    name = "subprocess"

    def run(self, case: EvalCase, policy: SandboxPolicy) -> BackendResult:
        argv = case.input.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
            raise SandboxError("subprocess backend requires input.argv: list[str]")

        cwd = case.input.get("cwd")
        stdin_data = case.input.get("stdin")
        if stdin_data is not None:
            stdin_data = str(stdin_data)

        timeout = case.timeout_sec if case.timeout_sec is not None else policy.timeout_sec
        local_policy = SandboxPolicy(
            cwd_root=policy.cwd_root,
            timeout_sec=timeout,
            allow_network=policy.allow_network,
            allow_commands=policy.allow_commands,
            env_allowlist=policy.env_allowlist,
        )

        try:
            proc = run_sandboxed(
                argv,
                policy=local_policy,
                cwd=cwd if isinstance(cwd, str) else None,
                stdin_data=stdin_data,
            )
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            err = (exc.stderr or "") if isinstance(exc.stderr, str) else "timeout"
            return BackendResult(
                exit_code=124,
                stdout=out,
                stderr=f"timeout after {timeout}s: {err}",
                meta={"timeout": True},
            )
        except SandboxError as exc:
            return BackendResult(
                exit_code=126,
                stdout="",
                stderr=str(exc),
                meta={"sandbox_denied": True},
            )

        return BackendResult(
            exit_code=int(proc.returncode),
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            meta={},
        )
