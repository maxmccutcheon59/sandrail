"""v0.3 suite packs: discovery, CLI, and execution under secure defaults."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sandrail.cli import main
from sandrail.packs import _safe_pack_name, get_pack, list_packs


def test_list_packs_contains_three():
    packs = list_packs()
    names = {p.name for p in packs}
    assert {"ci_gate", "tool_sandbox", "redaction"} <= names


def test_packs_list_cli(capsys):
    assert main(["packs", "list"]) == 0
    out = capsys.readouterr().out
    assert "ci_gate" in out
    assert "tool_sandbox" in out
    assert "redaction" in out
    assert "sandrail packs run" in out


def test_packs_run_ci_gate(tmp_path: Path, capsys):
    code = main(
        [
            "packs",
            "run",
            "ci_gate",
            "--cwd-root",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "ci-gate-green" in out or "gate-greeting" in out


def test_packs_run_tool_sandbox():
    assert main(["packs", "run", "tool_sandbox"]) == 0


def test_packs_run_redaction(fixture_secret: str, capsys):
    code = main(["packs", "run", "redaction", "--format", "json"])
    out = capsys.readouterr().out
    assert code == 0
    assert fixture_secret not in out
    assert "sk-abcdefghijklmnopqrstuvwxyz012345" not in out


def test_run_pack_path_directly(tmp_path: Path):
    assert (
        main(
            [
                "run",
                "examples/packs/ci_gate/suite.yaml",
                "--backend",
                "mock",
                "--cwd-root",
                str(tmp_path),
            ]
        )
        == 0
    )


def test_ci_gate_expected_fail_exit_one():
    assert main(["run", "examples/packs/ci_gate/expected_fail.yaml", "--backend", "mock"]) == 1


def test_pack_rejects_path_traversal_name():
    with pytest.raises(ValueError):
        _safe_pack_name("../etc")
    with pytest.raises(ValueError):
        _safe_pack_name("foo/bar")


def test_get_pack_missing():
    with pytest.raises(FileNotFoundError):
        get_pack("no_such_pack_zzzz")


def test_pack_network_stays_denied(capsys):
    """Bundled packs ignore --allow-network (secure default)."""
    code = main(
        [
            "packs",
            "run",
            "ci_gate",
            "--allow-network",
            "--format",
            "json",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "allow_network=false" in captured.err or "ignoring --allow-network" in captured.err
    assert '"allow_network": false' in captured.out or '"allow_network":false' in captured.out


def test_pack_network_denied_in_report(tmp_path: Path, capsys):
    code = main(
        [
            "packs",
            "run",
            "ci_gate",
            "--cwd-root",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    # Find a JSON object in output
    start = out.find("{")
    assert start >= 0
    data = json.loads(out[start:])
    assert data["allow_network"] is False


def test_demo_mentions_packs(capsys):
    assert main(["demo", "--skip-fail-demo"]) == 0
    out = capsys.readouterr().out
    assert "packs list" in out or "sandrail packs" in out
    assert "ci_gate" in out or "packs run" in out
    assert "maxmccutcheon59.github.io/sandrail-site" in out


def test_help_mentions_packs(capsys):
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert "packs list" in out
    assert "packs run" in out


def test_demo_with_packs(tmp_path: Path):
    # Longer path — exercises pack runner from demo
    assert main(["demo", "--skip-fail-demo", "--with-packs"]) == 0
