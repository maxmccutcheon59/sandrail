"""Mock backend + runner integration."""

from __future__ import annotations

from pathlib import Path

from sandrail.backends.mock import MockBackend
from sandrail.backends.openai_compat import OpenAICompatBackend
from sandrail.backends.subprocess_backend import SubprocessBackend
from sandrail.loader import load_suite
from sandrail.models import EvalCase, Expect
from sandrail.redaction import REDACTED
from sandrail.runner import default_policy, run_case, run_suite


def test_demo_suite_mock(examples_dir: Path, tmp_path: Path):
    name, cases, _ = load_suite(examples_dir / "suite.yaml")
    backend = MockBackend()
    policy = default_policy(tmp_path, allow_network=False)
    report = run_suite(name, cases, backend, policy)
    assert report.ok
    assert report.failed == 0


def test_prompt_injection_redaction(examples_dir: Path, tmp_path: Path, fixture_secret: str):
    name, cases, _ = load_suite(examples_dir / "cases" / "prompt_injection_redaction.yaml")
    backend = MockBackend()
    policy = default_policy(tmp_path, allow_network=False)
    report = run_suite(name, cases, backend, policy)
    assert report.ok, [r.failures for r in report.results]
    text = report.results[0].stdout
    assert fixture_secret not in text
    assert REDACTED in text
    blob = str(report.to_dict())
    assert fixture_secret not in blob


def test_subprocess_cases(examples_dir: Path):
    name, cases, _ = load_suite(examples_dir / "cases" / "subprocess_smoke.yaml")
    root = examples_dir.resolve()
    backend = SubprocessBackend()
    policy = default_policy(root, allow_network=False)
    report = run_suite(name, cases, backend, policy)
    assert report.ok, [(r.case_id, r.failures, r.stderr) for r in report.results]


def test_deny_curl(examples_dir: Path):
    name, cases, _ = load_suite(examples_dir / "cases" / "subprocess_deny.json")
    backend = SubprocessBackend()
    policy = default_policy(examples_dir.resolve(), allow_network=False)
    report = run_suite(name, cases, backend, policy)
    assert report.ok


def test_openai_backend_requires_env(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    backend = OpenAICompatBackend()
    case = EvalCase(id="x", input={"prompt": "hi"}, expect=Expect(exit_code=2))
    policy = default_policy(tmp_path, allow_network=True)
    result = run_case(case, backend, policy)
    assert result.passed
    assert "OPENAI_BASE_URL" in result.stderr


def test_openai_denied_without_allow_network(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
    backend = OpenAICompatBackend()
    case = EvalCase(id="x", input={"prompt": "hi"}, expect=Expect(exit_code=126))
    policy = default_policy(tmp_path, allow_network=False)
    result = run_case(case, backend, policy)
    assert result.passed
    assert "allow-network" in result.stderr
