"""Backend protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sandrail.models import EvalCase
from sandrail.sandbox import SandboxPolicy


@dataclass
class BackendResult:
    exit_code: int
    stdout: str
    stderr: str
    meta: dict = field(default_factory=dict)


class AgentBackend(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, case: EvalCase, policy: SandboxPolicy) -> BackendResult:
        """Execute one eval case under the given sandbox policy."""
