"""Pluggable agent backends for Sandrail."""

from __future__ import annotations

from sandrail.backends.base import AgentBackend, BackendResult
from sandrail.backends.mock import MockBackend
from sandrail.backends.openai_compat import OpenAICompatBackend
from sandrail.backends.subprocess_backend import SubprocessBackend

BACKENDS: dict[str, type[AgentBackend]] = {
    "mock": MockBackend,
    "subprocess": SubprocessBackend,
    "openai": OpenAICompatBackend,
}


def get_backend(name: str, **kwargs: object) -> AgentBackend:
    key = name.strip().lower()
    if key not in BACKENDS:
        raise KeyError(f"unknown backend {name!r}; choose from {sorted(BACKENDS)}")
    cls = BACKENDS[key]
    return cls(**kwargs)  # type: ignore[arg-type]


__all__ = [
    "AgentBackend",
    "BackendResult",
    "MockBackend",
    "SubprocessBackend",
    "OpenAICompatBackend",
    "BACKENDS",
    "get_backend",
]
