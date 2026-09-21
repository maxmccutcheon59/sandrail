"""Sandrail CLI — local-first AI eval harness."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from sandrail import __version__
from sandrail.backends import get_backend
from sandrail.loader import load_suite
from sandrail.paths import examples_dir
from sandrail.report import write_json, write_junit_xml, write_table
from sandrail.runner import default_policy, run_suite

_EPILOG = """
examples:
  pip install -e .
  sandrail demo
  sandrail run examples/suites/smoke.yaml --backend mock
  sandrail run examples/suites/timeout.yaml --backend subprocess
  sandrail run examples/suites/allowlist_deny.json --backend subprocess
  sandrail run examples/suites/redaction.yaml --backend mock --format json
  sandrail run examples/suites/smoke.yaml --backend mock --junit-xml junit.xml

secure defaults:
  network DENY · shell=False · command allow-list · cwd jail · timeouts · log redaction

authorized local use only — see SECURITY.md
""".strip()

_RUN_EPILOG = """
examples:
  sandrail run examples/suites/smoke.yaml
  sandrail run examples/suites/smoke.yaml --backend mock --format both
  sandrail run examples/suites/timeout.yaml -b subprocess
  sandrail run examples/suites/allowlist_deny.json -b subprocess
  sandrail run examples/suites/smoke.yaml --junit-xml out.xml

exit codes:
  0  all cases passed
  1  one or more cases failed
  2  usage / load / configuration error
""".strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sandrail",
        description=(
            "Local-first AI eval harness / agent sandbox CLI. "
            "Network denied by default; secrets via env only. "
            "Not a hosted SaaS — runs on your machine or CI."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"sandrail {__version__}")

    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser(
        "run",
        help="Run an eval suite against a backend",
        epilog=_RUN_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_p.add_argument("suite", type=str, help="Path to suite JSON/YAML")
    run_p.add_argument(
        "--backend",
        "-b",
        default="mock",
        choices=["mock", "subprocess", "openai"],
        help="Agent backend (default: mock — no network)",
    )
    run_p.add_argument(
        "--cwd-root",
        type=str,
        default=None,
        help="Sandbox cwd jail root (default: suite parent directory)",
    )
    run_p.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Default per-case timeout seconds (default: 30)",
    )
    run_p.add_argument(
        "--allow-network",
        action="store_true",
        default=False,
        help="Allow network in sandbox (default: deny). Required for openai backend.",
    )
    run_p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report to stdout",
    )
    run_p.add_argument(
        "--format",
        choices=["table", "json", "both"],
        default=None,
        help="Report format (default: table, or json if --json)",
    )
    run_p.add_argument(
        "--junit-xml",
        type=str,
        default=None,
        metavar="PATH",
        help="Write a JUnit XML report to PATH (for CI consumers; optional)",
    )

    demo_p = sub.add_parser(
        "demo",
        help="60-second founder wow path — run built-in suites, print a crisp report",
    )
    demo_p.add_argument(
        "--junit-xml",
        type=str,
        default=None,
        metavar="PATH",
        help="Optional directory or file prefix for per-suite JUnit XML",
    )
    demo_p.add_argument(
        "--skip-fail-demo",
        action="store_true",
        help="Skip the intentional mock pass/fail suite (keeps overall exit 0)",
    )

    sub.add_parser("backends", help="List available backends")
    sub.add_parser("version", help="Print version")

    return p


def _err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def _hint(msg: str) -> None:
    print(f"hint: {msg}", file=sys.stderr)


def _run_one_suite(
    *,
    suite_path: Path,
    backend_name: str,
    cwd_root: Path,
    timeout: float,
    allow_network: bool,
    fmt: str,
    junit_xml: str | None,
) -> int:
    if not suite_path.exists():
        _err(f"suite not found: {suite_path}")
        _hint("pass a path to a .yaml/.json suite, or run: sandrail demo")
        return 2
    if not suite_path.is_file():
        _err(f"suite path is not a file: {suite_path}")
        return 2
    if timeout <= 0:
        _err(f"--timeout must be positive (got {timeout})")
        return 2

    try:
        name, cases, _meta = load_suite(suite_path)
    except FileNotFoundError as exc:
        _err(str(exc))
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        _err(f"failed to load suite: {exc}")
        _hint("suite must be JSON/YAML with a 'cases' list (or a bare list of cases)")
        return 2

    if backend_name == "openai" and not allow_network:
        _err("openai backend requires --allow-network (and OPENAI_BASE_URL in the env)")
        _hint(
            "Sandrail defaults to network deny. Opt in explicitly only for APIs you own "
            "or are authorized to call."
        )
        return 2

    policy = default_policy(
        cwd_root,
        timeout_sec=timeout,
        allow_network=bool(allow_network),
    )

    try:
        backend = get_backend(backend_name)
    except KeyError as exc:
        _err(str(exc))
        _hint("choose: mock | subprocess | openai  (see: sandrail backends)")
        return 2

    report = run_suite(name, cases, backend, policy)

    if fmt in {"table", "both"}:
        write_table(report)
    if fmt in {"json", "both"}:
        write_json(report)

    if junit_xml:
        try:
            write_junit_xml(report, path=junit_xml)
        except OSError as exc:
            _err(f"failed to write JUnit XML: {exc}")
            return 2

    return 0 if report.ok else 1


def _demo(args: argparse.Namespace) -> int:
    """Run built-in suites and print a crisp founder-facing summary."""
    try:
        ex = examples_dir()
    except FileNotFoundError as exc:
        _err(str(exc))
        return 2

    # Synthetic fixture secret for redaction suite (never a real credential)
    os.environ.setdefault("SANDRAIL_FIXTURE_SECRET", "synth-secret-DO-NOT-USE-9f3a2c1b")

    suites = ex / "suites"
    steps: list[tuple[str, Path, str, bool]] = [
        ("1/5  mock smoke", suites / "smoke.yaml", "mock", False),
        ("2/5  subprocess allow-list smoke", suites / "subprocess_smoke.yaml", "subprocess", False),
        ("3/5  allow-list deny (curl/bash/…)", suites / "allowlist_deny.json", "subprocess", False),
        ("4/5  timeout enforcement", suites / "timeout.yaml", "subprocess", False),
        ("5/5  redaction / prompt-injection", suites / "redaction.yaml", "mock", False),
    ]

    print("=" * 72)
    print(f"  SANDRAIL DEMO  v{__version__}  — local-first agent eval harness")
    print("  Secure defaults: network DENY · shell=False · allow-list · cwd jail")
    print("  Authorized local use only. Not a hosted SaaS. No telemetry.")
    print(f"  examples: {ex}")
    print("=" * 72)
    print()

    t0 = time.perf_counter()
    results: list[tuple[str, int, float]] = []
    worst = 0

    for label, path, backend, allow_net in steps:
        print(f"── {label}")
        net = "allow" if allow_net else "deny"
        print(f"   suite={path.name}  backend={backend}  network={net}")
        junit = None
        if args.junit_xml:
            jpath = Path(args.junit_xml)
            if jpath.suffix.lower() == ".xml":
                junit = str(jpath.parent / f"{jpath.stem}-{path.stem}.xml")
            else:
                junit = str(jpath / f"{path.stem}.xml")
        step_t0 = time.perf_counter()
        code = _run_one_suite(
            suite_path=path,
            backend_name=backend,
            cwd_root=path.resolve().parent,
            timeout=30.0,
            allow_network=allow_net,
            fmt="table",
            junit_xml=junit,
        )
        elapsed = time.perf_counter() - step_t0
        status = "PASS" if code == 0 else ("FAIL" if code == 1 else "ERROR")
        results.append((label, code, elapsed))
        print(f"   → {status} ({elapsed:.2f}s)")
        print()
        if code == 2:
            worst = 2
            break
        if code == 1 and worst < 1:
            worst = 1

    fail_demo_code: int | None = None
    if worst != 2 and not args.skip_fail_demo:
        fail_path = ex / "suites" / "mock_pass_fail.yaml"
        print("── bonus  intentional mock pass/fail (shows CI gate)")
        print(f"   suite={fail_path.name}  backend=mock  (expect suite FAIL / exit 1)")
        fail_demo_code = _run_one_suite(
            suite_path=fail_path,
            backend_name="mock",
            cwd_root=fail_path.resolve().parent,
            timeout=30.0,
            allow_network=False,
            fmt="table",
            junit_xml=None,
        )
        if fail_demo_code == 1:
            print("   → expected FAIL (gate works — one case passed, one regressed)")
        elif fail_demo_code == 0:
            print("   → unexpected PASS (pass/fail fixture may have changed)")
            worst = max(worst, 1)
        else:
            worst = 2
        print()

    total = time.perf_counter() - t0
    print("=" * 72)
    print("  DEMO SUMMARY")
    for label, code, elapsed in results:
        mark = "ok" if code == 0 else ("FAIL" if code == 1 else "ERR")
        print(f"    [{mark:>4}]  {label}  ({elapsed:.2f}s)")
    if fail_demo_code is not None:
        print(
            f"    [{'ok' if fail_demo_code == 1 else 'WARN'}]  "
            f"bonus intentional fail demo  (exit {fail_demo_code})"
        )
    print(f"  wall time: {total:.2f}s")
    print()
    if worst == 0:
        print("  All built-in control suites passed under secure defaults.")
        print("  Next: `sandrail run examples/suites/smoke.yaml --backend mock` and wire it in CI.")
        print("  Optional: --junit-xml for dashboards. See README + SECURITY.md.")
    elif worst == 1:
        print("  One or more control suites failed — check output above.")
    else:
        print("  Demo aborted on configuration/load error — see messages above.")
    print("=" * 72)

    # Demo exit: 0 if control suites passed (intentional fail demo does not fail the demo)
    return 0 if worst == 0 else worst


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0

    if args.command == "backends":
        print("mock        — deterministic local agent (default, no network)")
        print("subprocess  — allow-listed argv under cwd jail / timeout / net deny")
        print("openai      — optional OpenAI-compatible API if OPENAI_BASE_URL set")
        print()
        print("defaults: network deny · shell=False · never pass user strings to a shell")
        return 0

    if args.command == "demo":
        return _demo(args)

    if args.command == "run":
        suite_path = Path(args.suite)
        cwd_root = Path(args.cwd_root) if args.cwd_root else suite_path.resolve().parent
        fmt = args.format
        if fmt is None:
            fmt = "json" if args.json else "table"
        return _run_one_suite(
            suite_path=suite_path,
            backend_name=args.backend,
            cwd_root=cwd_root,
            timeout=float(args.timeout),
            allow_network=bool(args.allow_network),
            fmt=fmt,
            junit_xml=args.junit_xml,
        )

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
