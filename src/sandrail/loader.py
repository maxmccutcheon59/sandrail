"""Load eval suites from JSON or YAML (safe_load only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sandrail.models import EvalCase

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def _load_raw(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML suites")
        # NEVER yaml.load — safe_load only
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        # Try JSON then YAML
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            if yaml is None:
                raise
            data = yaml.safe_load(text)
    return data


def load_suite(path: str | Path) -> tuple[str, list[EvalCase], dict[str, Any]]:
    """
    Load a suite file.

    Accepts either:
      - a list of cases
      - an object { "name": "...", "cases": [ ... ], "defaults": {...} }
    """
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"suite not found: {p}")
    raw = _load_raw(p)
    meta: dict[str, Any] = {}
    if isinstance(raw, list):
        cases_raw = raw
        name = p.stem
    elif isinstance(raw, dict):
        meta = {k: v for k, v in raw.items() if k != "cases"}
        cases_raw = raw.get("cases")
        if not isinstance(cases_raw, list):
            raise ValueError("suite object must contain a 'cases' list")
        name = str(raw.get("name") or p.stem)
    else:
        raise ValueError("suite must be a list or an object with 'cases'")

    cases: list[EvalCase] = []
    for i, item in enumerate(cases_raw):
        if not isinstance(item, dict):
            raise ValueError(f"case[{i}] must be an object")
        cases.append(EvalCase.from_dict(item))

    if not cases:
        raise ValueError("suite has no cases")
    return name, cases, meta
