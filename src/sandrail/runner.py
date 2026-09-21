"""Eval suite runner: score cases, redact secrets from reports."""

from __future__ import annotations

import time
from pathlib import Path

from sandrail import __version__
from sandrail.backends.base import AgentBackend
from sandrail.models import CaseResult, EvalCase, SuiteReport
from sandrail.redaction import assert_no_secret_leak, redact_text
from sandrail.sandbox import SandboxPolicy


def run_case(
    case: EvalCase,
    backend: AgentBackend,
    policy: SandboxPolicy,
) -> CaseResult:
    t0 = time.perf_counter()
    try:
        result = backend.run(case, policy)
    except Exception as exc:  # backend bugs should not crash the suite
        duration_ms = (time.perf_counter() - t0) * 1000
        return CaseResult(
            case_id=case.id,
            passed=False,
            score=0.0,
            exit_code=None,
            stdout="",
            stderr=f"backend error: {type(exc).__name__}: {exc}",
            duration_ms=duration_ms,
            failures=[f"backend error: {type(exc).__name__}"],
            redacted=False,
            backend=backend.name,
        )

    duration_ms = (time.perf_counter() - t0) * 1000
    secrets = list(case.expect.secrets_must_not_leak)

    # Redact before anything is persisted into the report object
    stdout_r, r1 = redact_text(result.stdout, secrets)
    stderr_r, r2 = redact_text(result.stderr, secrets)

    failures: list[str] = []
    exp = case.expect
    if exp.exit_code is not None and result.exit_code != exp.exit_code:
        failures.append(f"exit_code: expected {exp.exit_code}, got {result.exit_code}")

    # Content checks use redacted streams so scoring never depends on seeing secrets
    for needle in exp.stdout_contains:
        if needle not in stdout_r:
            failures.append(f"stdout missing: {needle!r}")
    for needle in exp.stdout_not_contains:
        if needle in stdout_r:
            failures.append(f"stdout forbidden: {needle!r}")
    for needle in exp.stderr_contains:
        if needle not in stderr_r:
            failures.append(f"stderr missing: {needle!r}")
    for needle in exp.stderr_not_contains:
        if needle in stderr_r:
            failures.append(f"stderr forbidden: {needle!r}")

    # Harness integrity: redacted report must not contain the fixture secrets
    if secrets:
        leaks = assert_no_secret_leak(stdout_r + "\n" + stderr_r, secrets)
        if leaks:
            failures.extend(leaks)
        # Also fail if raw had secrets but redaction did not catch them (same check)

    passed = len(failures) == 0
    return CaseResult(
        case_id=case.id,
        passed=passed,
        score=1.0 if passed else 0.0,
        exit_code=result.exit_code,
        stdout=stdout_r,
        stderr=stderr_r,
        duration_ms=round(duration_ms, 3),
        failures=failures,
        redacted=r1 or r2,
        backend=backend.name,
    )


def run_suite(
    name: str,
    cases: list[EvalCase],
    backend: AgentBackend,
    policy: SandboxPolicy,
) -> SuiteReport:
    results = [run_case(c, backend, policy) for c in cases]
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    return SuiteReport(
        suite=name,
        backend=backend.name,
        passed=passed,
        failed=failed,
        total=len(results),
        results=results,
        allow_network=policy.allow_network,
        version=__version__,
    )


def default_policy(
    cwd_root: Path,
    *,
    timeout_sec: float = 30.0,
    allow_network: bool = False,
) -> SandboxPolicy:
    return SandboxPolicy(
        cwd_root=cwd_root.resolve(),
        timeout_sec=timeout_sec,
        allow_network=allow_network,
    )
