"""Stable landing demo + examples/suites paths."""

from __future__ import annotations

from pathlib import Path

from sandrail.cli import main


def test_demo_exits_zero():
    assert main(["demo", "--skip-fail-demo"]) == 0


def test_run_suites_smoke(tmp_path: Path, capsys):
    code = main(
        [
            "run",
            "examples/suites/smoke.yaml",
            "--backend",
            "mock",
            "--cwd-root",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out or '"ok":true' in out


def test_run_suites_allowlist_deny():
    assert main(["run", "examples/suites/allowlist_deny.json", "--backend", "subprocess"]) == 0


def test_run_suites_timeout():
    assert main(["run", "examples/suites/timeout.yaml", "--backend", "subprocess"]) == 0


def test_help_mentions_suites(capsys):
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert "examples/suites/smoke.yaml" in out
    assert "sandrail demo" in out
