"""Resolve bundled / checkout example suites for demos and docs."""

from __future__ import annotations

import os
from pathlib import Path


def examples_dir() -> Path:
    """
    Locate the examples/ directory.

    Order:
      1. SANDRAIL_EXAMPLES env (explicit override)
      2. Repo checkout (editable install: src/sandrail/../../examples)
      3. Current working directory ./examples
    """
    env = os.environ.get("SANDRAIL_EXAMPLES")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
        raise FileNotFoundError(
            f"SANDRAIL_EXAMPLES is set but not a directory: {p}"
        )

    # cli.py / paths.py live at src/sandrail/ → parents[2] is repo root
    repo = Path(__file__).resolve().parents[2] / "examples"
    if repo.is_dir():
        return repo

    cwd = Path.cwd() / "examples"
    if cwd.is_dir():
        return cwd.resolve()

    raise FileNotFoundError(
        "examples/ not found. Run from a Sandrail checkout, or set "
        "SANDRAIL_EXAMPLES=/path/to/sandrail/examples, or: "
        "git clone https://github.com/maxmccutcheon59/sandrail"
    )
