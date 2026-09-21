"""Typed eval models (stdlib dataclasses; no ORM)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Expect:
    """Scoring expectations for a single case."""

    exit_code: int | None = 0
    stdout_contains: list[str] = field(default_factory=list)
    stdout_not_contains: list[str] = field(default_factory=list)
    stderr_contains: list[str] = field(default_factory=list)
    stderr_not_contains: list[str] = field(default_factory=list)
    # Secrets that must NEVER appear in captured logs (prompt-injection / redaction tests)
    secrets_must_not_leak: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Expect:
        if not data:
            return cls()
        return cls(
            exit_code=data.get("exit_code", 0),
            stdout_contains=list(data.get("stdout_contains") or []),
            stdout_not_contains=list(data.get("stdout_not_contains") or []),
            stderr_contains=list(data.get("stderr_contains") or []),
            stderr_not_contains=list(data.get("stderr_not_contains") or []),
            secrets_must_not_leak=list(data.get("secrets_must_not_leak") or []),
        )


@dataclass(frozen=True)
class EvalCase:
    """One eval case loaded from JSON/YAML."""

    id: str
    description: str = ""
    # Backend-specific payload (prompt text, argv for subprocess, mock script, etc.)
    input: dict[str, Any] = field(default_factory=dict)
    expect: Expect = field(default_factory=Expect)
    timeout_sec: float | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalCase:
        if "id" not in data or not str(data["id"]).strip():
            raise ValueError("eval case requires non-empty 'id'")
        return cls(
            id=str(data["id"]).strip(),
            description=str(data.get("description") or ""),
            input=dict(data.get("input") or {}),
            expect=Expect.from_dict(data.get("expect")),
            timeout_sec=float(data["timeout_sec"]) if data.get("timeout_sec") is not None else None,
            tags=[str(t) for t in (data.get("tags") or [])],
        )


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    score: float
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: float
    failures: list[str] = field(default_factory=list)
    redacted: bool = False
    backend: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuiteReport:
    suite: str
    backend: str
    passed: int
    failed: int
    total: int
    results: list[CaseResult]
    allow_network: bool
    version: str

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "backend": self.backend,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "ok": self.ok,
            "allow_network": self.allow_network,
            "version": self.version,
            "results": [r.to_dict() for r in self.results],
        }
