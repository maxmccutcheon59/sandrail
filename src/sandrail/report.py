"""Human table + JSON report writers."""

from __future__ import annotations

import json
import sys
from typing import TextIO

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
