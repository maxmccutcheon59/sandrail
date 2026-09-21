"""JUnit XML report writer tests."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from sandrail.models import CaseResult, SuiteReport
from sandrail.redaction import REDACTED
from sandrail.report import build_junit_tree, write_junit_xml


def _sample_report(*, failed: bool = False, secret: str | None = None) -> SuiteReport:
    stdout = f"hello {REDACTED}" if secret else "hello"
    failures = ["stdout missing: 'yes'"] if failed else []
    results = [
        CaseResult(
            case_id="case-a",
            passed=not failed,
            score=0.0 if failed else 1.0,
            exit_code=0,
            stdout=stdout,
            stderr="",
            duration_ms=12.5,
            failures=failures,
            redacted=bool(secret),
            backend="mock",
        )
    ]
    return SuiteReport(
        suite="demo",
        backend="mock",
        passed=0 if failed else 1,
        failed=1 if failed else 0,
        total=1,
        results=results,
        allow_network=False,
        version="0.2.0",
    )


def test_junit_pass_structure(tmp_path: Path):
    report = _sample_report()
    path = tmp_path / "out.xml"
    xml_text = write_junit_xml(report, path=path)
    assert path.is_file()
    assert "testcase" in xml_text
    root = ET.parse(path).getroot()
    assert root.tag == "testsuites"
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.get("tests") == "1"
    assert suite.get("failures") == "0"
    assert suite.get("allow_network") == "false"
    case = suite.find("testcase")
    assert case is not None
    assert case.get("name") == "case-a"
    assert case.find("failure") is None


def test_junit_failure_element(tmp_path: Path):
    report = _sample_report(failed=True)
    path = tmp_path / "fail.xml"
    write_junit_xml(report, path=path)
    suite = ET.parse(path).getroot().find("testsuite")
    assert suite is not None
    assert suite.get("failures") == "1"
    fail = suite.find("testcase/failure")
    assert fail is not None
    assert "stdout missing" in (fail.get("message") or "")


def test_junit_does_not_embed_raw_secret(tmp_path: Path):
    secret = "synth-secret-DO-NOT-USE-9f3a2c1b"
    # Simulate runner-already-redacted streams
    report = _sample_report(secret=secret)
    # Ensure we didn't put the raw secret in the CaseResult
    assert secret not in report.results[0].stdout
    xml_text = write_junit_xml(report, path=tmp_path / "r.xml")
    assert secret not in xml_text
    assert REDACTED in xml_text


def test_build_junit_tree_backend_attr():
    tree = build_junit_tree(_sample_report())
    suite = tree.find("testsuite")
    assert suite is not None
    assert suite.get("backend") == "mock"
    assert suite.get("sandrail_version") == "0.2.0"
