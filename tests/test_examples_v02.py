"""v0.2 built-in example suites: timeout, allow-list deny, redaction."""

from __future__ import annotations

import json
from pathlib import Path

from sandrail.backends.mock import MockBackend
from sandrail.backends.subprocess_backend import SubprocessBackend
from sandrail.cli import main
from sandrail.loader import load_suite
from sandrail.redaction import REDACTED
from sandrail.runner import default_policy, run_suite


def test_timeout_suite(examples_dir: Path):
    name, cases, _ = load_suite(examples_dir / "cases" / "timeout.yaml")
    backend = SubprocessBackend()
    policy = default_policy(examples_dir.resolve(), allow_network=False, timeout_sec=30)
    report = run_suite(name, cases, backend, policy)
    assert report.ok, [(r.case_id, r.failures, r.stderr) for r in report.results]
    by_id = {r.case_id: r for r in report.results}
    assert by_id["timeout-sleep"].exit_code == 124
    assert by_id["timeout-fast-ok"].passed


def test_expanded_deny_suite(examples_dir: Path):
    name, cases, _ = load_suite(examples_dir / "cases" / "subprocess_deny.json")
    assert len(cases) >= 5
    backend = SubprocessBackend()
    policy = default_policy(examples_dir.resolve(), allow_network=False)
    report = run_suite(name, cases, backend, policy)
    assert report.ok, [(r.case_id, r.failures, r.stderr) for r in report.results]
    for r in report.results:
        assert r.exit_code == 126
        assert "not allow-listed" in r.stderr


def test_expanded_redaction_suite(examples_dir: Path, tmp_path: Path, fixture_secret: str):
    name, cases, _ = load_suite(examples_dir / "cases" / "prompt_injection_redaction.yaml")
    assert len(cases) >= 4
    backend = MockBackend()
    policy = default_policy(tmp_path, allow_network=False)
    report = run_suite(name, cases, backend, policy)
    assert report.ok, [(r.case_id, r.failures, r.stdout, r.stderr) for r in report.results]
    blob = json.dumps(report.to_dict())
    assert fixture_secret not in blob
    assert "sk-abcdefghijklmnopqrstuvwxyz012345" not in blob
    assert REDACTED in blob


def test_cli_junit_xml(examples_dir: Path, tmp_path: Path):
    junit = tmp_path / "sandrail-junit.xml"
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
            "--junit-xml",
            str(junit),
        ]
    )
    assert code == 0
    assert junit.is_file()
    text = junit.read_text(encoding="utf-8")
    assert "<testsuites>" in text
    assert "mock-hello" in text
    assert 'allow_network="false"' in text


def test_network_still_denied_by_default(examples_dir: Path, tmp_path: Path, capsys):
    """Secure default: allow_network false in JSON report."""
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
    assert data["allow_network"] is False
