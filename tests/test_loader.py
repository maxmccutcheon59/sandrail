"""Suite loader tests."""

from __future__ import annotations

from pathlib import Path

from sandrail.loader import load_suite


def test_load_yaml_suite(examples_dir: Path):
    name, cases, meta = load_suite(examples_dir / "suite.yaml")
    assert name == "demo-suite"
    assert len(cases) >= 2
    assert cases[0].id == "mock-hello"


def test_load_json_suite(examples_dir: Path):
    name, cases, _ = load_suite(examples_dir / "cases" / "subprocess_deny.json")
    assert name == "subprocess-deny"
    assert cases[0].id == "deny-curl"
