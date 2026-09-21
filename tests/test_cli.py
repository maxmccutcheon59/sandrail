"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

from sandrail.cli import main


def test_version():
    assert main(["version"]) == 0


def test_backends(capsys):
    assert main(["backends"]) == 0
    out = capsys.readouterr().out
    assert "mock" in out
    assert "subprocess" in out


def test_run_mock_suite(examples_dir: Path, tmp_path: Path, capsys):
    code = main(
        [
            "run",
            str(examples_dir / "suite.yaml"),
            "--backend",
            "mock",
            "--cwd-root",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["ok"] is True


def test_run_injection_json(examples_dir: Path, tmp_path: Path, fixture_secret: str, capsys):
    code = main(
        [
            "run",
            str(examples_dir / "cases" / "prompt_injection_redaction.yaml"),
            "--backend",
            "mock",
            "--cwd-root",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert code == 0
    assert data["ok"] is True
    assert fixture_secret not in out


def test_run_subprocess_deny(examples_dir: Path):
    code = main(
        [
            "run",
            str(examples_dir / "cases" / "subprocess_deny.json"),
            "--backend",
            "subprocess",
            "--cwd-root",
            str(examples_dir),
        ]
    )
    assert code == 0


def test_failing_suite_exit_code(tmp_path: Path):
    suite = tmp_path / "fail.yaml"
    suite.write_text(
        "cases:\n"
        "  - id: fail-me\n"
        "    input: {respond: 'nope'}\n"
        "    expect: {stdout_contains: ['yes']}\n",
        encoding="utf-8",
    )
    code = main(["run", str(suite), "--backend", "mock", "--cwd-root", str(tmp_path)])
    assert code == 1
