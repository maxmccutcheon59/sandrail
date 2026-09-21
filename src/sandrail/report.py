"""Human table + JSON + optional JUnit XML report writers."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TextIO
from xml.dom import minidom

from sandrail.models import SuiteReport


def write_json(report: SuiteReport, stream: TextIO | None = None) -> None:
    out = stream or sys.stdout
    json.dump(report.to_dict(), out, indent=2, ensure_ascii=False)
    out.write("\n")


def write_table(report: SuiteReport, stream: TextIO | None = None) -> None:
    out = stream or sys.stdout
    out.write(
        f"Suite: {report.suite}  backend={report.backend}  "
        f"network={'allow' if report.allow_network else 'deny'}  "
        f"sandrail={report.version}\n"
    )
    out.write(f"{'ID':<32} {'PASS':<6} {'EXIT':<6} {'ms':>8}  failures\n")
    out.write("-" * 80 + "\n")
    for r in report.results:
        mark = "ok" if r.passed else "FAIL"
        exit_s = "-" if r.exit_code is None else str(r.exit_code)
        fail_s = "; ".join(r.failures) if r.failures else ""
        if len(fail_s) > 40:
            fail_s = fail_s[:37] + "..."
        out.write(f"{r.case_id:<32} {mark:<6} {exit_s:<6} {r.duration_ms:>8.1f}  {fail_s}\n")
    out.write("-" * 80 + "\n")
    out.write(f"{report.passed}/{report.total} passed")
    if report.failed:
        out.write(f", {report.failed} failed")
    out.write("\n")


def _xml_escape_text(value: str, *, limit: int = 4000) -> str:
    """Truncate then rely on ElementTree text escaping for XML safety."""
    if len(value) > limit:
        return value[: limit - 3] + "..."
    return value


def build_junit_tree(report: SuiteReport) -> ET.Element:
    """
    Build a JUnit-compatible XML tree for CI consumers (GitHub Actions,
    Jenkins, GitLab, etc.). Case stdout/stderr are already redacted by the runner.
    """
    total_sec = sum(r.duration_ms for r in report.results) / 1000.0
    suites = ET.Element("testsuites")
    suite = ET.SubElement(
        suites,
        "testsuite",
        {
            "name": report.suite,
            "tests": str(report.total),
            "failures": str(report.failed),
            "errors": "0",
            "skipped": "0",
            "time": f"{total_sec:.3f}",
            "package": "sandrail",
        },
    )
    # Non-standard but useful for CI dashboards; safe attributes only
    suite.set("backend", report.backend)
    suite.set("sandrail_version", report.version)
    suite.set("allow_network", "true" if report.allow_network else "false")

    classname = f"sandrail.{report.backend}.{report.suite}"
    for r in report.results:
        case_el = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": classname,
                "name": r.case_id,
                "time": f"{r.duration_ms / 1000.0:.3f}",
            },
        )
        if not r.passed:
            msg = "; ".join(r.failures) if r.failures else "case failed"
            fail_el = ET.SubElement(
                case_el,
                "failure",
                {
                    "message": _xml_escape_text(msg, limit=500),
                    "type": "AssertionError",
                },
            )
            detail_parts = [
                f"failures: {msg}",
                f"exit_code: {r.exit_code}",
            ]
            if r.stderr:
                detail_parts.append(f"stderr:\n{_xml_escape_text(r.stderr)}")
            if r.stdout:
                detail_parts.append(f"stdout:\n{_xml_escape_text(r.stdout)}")
            fail_el.text = "\n".join(detail_parts)
        # Optional system-out / system-err (already redacted)
        if r.stdout:
            so = ET.SubElement(case_el, "system-out")
            so.text = _xml_escape_text(r.stdout)
        if r.stderr:
            se = ET.SubElement(case_el, "system-err")
            se.text = _xml_escape_text(r.stderr)
    return suites


def write_junit_xml(
    report: SuiteReport,
    path: str | Path | None = None,
    stream: TextIO | None = None,
) -> str:
    """
    Write JUnit XML to a file and/or stream. Returns the XML string.

    Prefer writing to a file path for CI artifact upload; stdout is optional.
    """
    root = build_junit_tree(report)
    rough = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    # minidom adds an XML declaration; keep it

    if path is not None:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(pretty, encoding="utf-8")
    if stream is not None:
        stream.write(pretty)
        if not pretty.endswith("\n"):
            stream.write("\n")
    return pretty
