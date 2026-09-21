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
from sandrail.packs import get_pack, list_packs
from sandrail.paths import examples_dir
from sandrail.report import write_json, write_junit_xml, write_table
from sandrail.runner import default_policy, run_suite

_EPILOG = """
examples:
  pip install -e .
  sandrail demo
  sandrail packs list
  sandrail packs run ci_gate
  sandrail packs run tool_sandbox
  sandrail packs run redaction
  sandrail run examples/packs/ci_gate/suite.yaml --backend mock
  sandrail run examples/suites/smoke.yaml --backend mock
  sandrail run examples/suites/timeout.yaml --backend subprocess
  sandrail run examples/suites/allowlist_deny.json --backend subprocess
  sandrail run examples/suites/redaction.yaml --backend mock --format json
  sandrail run examples/suites/smoke.yaml --backend mock --junit-xml junit.xml

secure defaults:
  network DENY · shell=False · command allow-list · cwd jail · timeouts · log redaction

authorized local use only — see SECURITY.md
landing: https://maxmccutcheon59.github.io/sandrail-site/
""".strip()

_RUN_EPILOG = """
examples:
  sandrail run examples/packs/ci_gate/suite.yaml --backend mock
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

_PACKS_EPILOG = """
examples:
  sandrail packs list
  sandrail packs run ci_gate
  sandrail packs run tool_sandbox --format table
  sandrail packs run redaction --format json --junit-xml redaction.xml

  # equivalent direct paths:
  sandrail run examples/packs/ci_gate/suite.yaml --backend mock
  sandrail run examples/packs/tool_sandbox/deny.yaml --backend subprocess
  sandrail run examples/packs/redaction/suite.yaml --backend mock

exit codes (packs run):
  0  all pack suites passed
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
    _add_run_flags(run_p)
    run_p.add_argument("suite", type=str, help="Path to suite JSON/YAML")

    packs_p = sub.add_parser(
        "packs",
        help="List or run bundled suite packs under examples/packs/",
        epilog=_PACKS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    packs_sub = packs_p.add_subparsers(dest="packs_command", required=True)
    packs_sub.add_parser("list", help="List available suite packs")
    packs_run = packs_sub.add_parser(
        "run",
        help="Run a suite pack by name (e.g. ci_gate, tool_sandbox, redaction)",
        epilog=_PACKS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    packs_run.add_argument("name", type=str, help="Pack name (directory under examples/packs/)")
    _add_run_flags(packs_run, include_backend_default=False)
    packs_run.add_argument(
        "--backend",
        "-b",
        default=None,
        choices=["mock", "subprocess", "openai"],
        help="Override pack/suite default backend",
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
    demo_p.add_argument(
        "--with-packs",
        action="store_true",
        help="Also run suite packs (ci_gate, tool_sandbox, redaction) after control suites",
    )

    sub.add_parser("backends", help="List available backends")
    sub.add_parser("version", help="Print version")

    return p


def _add_run_flags(
    parser: argparse.ArgumentParser,
    *,
    include_backend_default: bool = True,
) -> None:
    if include_backend_default:
        parser.add_argument(
            "--backend",
            "-b",
            default="mock",
            choices=["mock", "subprocess", "openai"],
            help="Agent backend (default: mock — no network)",
        )
    parser.add_argument(
        "--cwd-root",
        type=str,
        default=None,
        help="Sandbox cwd jail root (default: suite parent directory)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Default per-case timeout seconds (default: 30)",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        default=False,
        help="Allow network in sandbox (default: deny). Required for openai backend.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report to stdout",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "both"],
        default=None,
        help="Report format (default: table, or json if --json)",
    )
    parser.add_argument(
        "--junit-xml",
        type=str,
        default=None,
        metavar="PATH",
        help="Write a JUnit XML report to PATH (for CI consumers; optional)",
    )


def _err(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)


def _hint(msg: str) -> None:
    print(f"hint: {msg}", file=sys.stderr)


def _resolve_format(args: argparse.Namespace) -> str:
    fmt = getattr(args, "format", None)
    if fmt is None:
        return "json" if getattr(args, "json", False) else "table"
    return fmt


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
        _hint("pass a path to a .yaml/.json suite, or: sandrail packs list / sandrail demo")
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


def _packs_list() -> int:
    try:
        packs = list_packs()
    except FileNotFoundError as exc:
        _err(str(exc))
        return 2
    if not packs:
        print("No suite packs found under examples/packs/.")
        _hint("expected ci_gate, tool_sandbox, redaction in a Sandrail checkout")
        return 0
    print(f"Sandrail suite packs  (v{__version__})")
    print(f"{'NAME':<16} {'BACKEND':<12} {'SUITES':<6} DESCRIPTION")
    print("-" * 72)
    for pack in packs:
        desc = pack.description.replace("\n", " ").strip()
        if len(desc) > 42:
            desc = desc[:39] + "..."
        print(
            f"{pack.name:<16} {pack.default_backend:<12} {len(pack.suites):<6} {desc}"
        )
    print()
    print("Run:  sandrail packs run <name>")
    print("Or:   sandrail run examples/packs/<name>/suite.yaml --backend <backend>")
    print("Docs: examples/packs/README.md")
    return 0


def _packs_run(args: argparse.Namespace) -> int:
    try:
        pack = get_pack(args.name)
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))
        _hint("sandrail packs list")
        return 2

    # Synthetic fixture secret for redaction pack (never a real credential)
    if pack.name == "redaction" or "redaction" in pack.tags:
        os.environ.setdefault(
            "SANDRAIL_FIXTURE_SECRET", "synth-secret-DO-NOT-USE-9f3a2c1b"
        )

    fmt = _resolve_format(args)
    timeout = float(args.timeout)
    # Packs never opt into network unless caller passes --allow-network AND pack allows
    allow_network = bool(args.allow_network) and bool(pack.allow_network)
    if args.allow_network and not pack.allow_network:
        _hint(
            f"pack {pack.name!r} keeps allow_network=false (secure default); "
            "ignoring --allow-network for this pack"
        )

    quiet_json = fmt == "json"
    if not quiet_json:
        print(
            f"pack: {pack.name}  suites={len(pack.suites)}  network="
            f"{'allow' if allow_network else 'deny'}"
        )
        if pack.description:
            one = pack.description.replace("\n", " ").strip()
            if len(one) > 100:
                one = one[:97] + "..."
            print(f"  {one}")
        print()

    worst = 0
    for i, ref in enumerate(pack.suites, start=1):
        suite_path = pack.suite_path(ref)
        backend = args.backend or ref.backend or pack.default_backend
        cwd_root = Path(args.cwd_root) if args.cwd_root else suite_path.resolve().parent
        junit = None
        if args.junit_xml:
            jpath = Path(args.junit_xml)
            if jpath.suffix.lower() == ".xml" and len(pack.suites) == 1:
                junit = str(jpath)
            elif jpath.suffix.lower() == ".xml":
                junit = str(jpath.parent / f"{jpath.stem}-{suite_path.stem}.xml")
            else:
                junit = str(jpath / f"{pack.name}-{suite_path.stem}.xml")

        if not quiet_json:
            print(f"── {i}/{len(pack.suites)}  {ref.file}  backend={backend}")
        code = _run_one_suite(
            suite_path=suite_path,
            backend_name=backend,
            cwd_root=cwd_root,
            timeout=timeout,
            allow_network=allow_network,
            fmt=fmt,
            junit_xml=junit,
        )
        if ref.expect_fail:
            if code == 1:
                if not quiet_json:
                    print("   → expected FAIL (ok for this suite)")
                code = 0
            elif code == 0:
                if not quiet_json:
                    print("   → unexpected PASS (expect_fail suite should have failed)")
                code = 1
        if not quiet_json:
            status = "PASS" if code == 0 else ("FAIL" if code == 1 else "ERROR")
            print(f"   → {status}")
            print()
        if code == 2:
            return 2
        if code == 1:
            worst = 1

    return worst


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
    print("  packs:    sandrail packs list  |  sandrail packs run ci_gate")
    print("  landing:  https://maxmccutcheon59.github.io/sandrail-site/")
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

    pack_results: list[tuple[str, int]] = []
    if worst != 2 and getattr(args, "with_packs", False):
        for pname in ("ci_gate", "tool_sandbox", "redaction"):
            print(f"── pack  {pname}")
            ns = argparse.Namespace(
                name=pname,
                backend=None,
                cwd_root=None,
                timeout=30.0,
                allow_network=False,
                json=False,
                format="table",
                junit_xml=None,
            )
            pcode = _packs_run(ns)
            pack_results.append((pname, pcode))
            if pcode == 2:
                worst = 2
                break
            if pcode == 1 and worst < 1:
                worst = 1

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
    for pname, pcode in pack_results:
        mark = "ok" if pcode == 0 else ("FAIL" if pcode == 1 else "ERR")
        print(f"    [{mark:>4}]  pack {pname}")
    print(f"  wall time: {total:.2f}s")
    print()
    if worst == 0:
        print("  All built-in control suites passed under secure defaults.")
        print("  Next: sandrail packs list  →  sandrail packs run ci_gate")
        print("  Or:   sandrail run examples/packs/ci_gate/suite.yaml --backend mock")
        print("  Suites: sandrail run examples/suites/smoke.yaml --backend mock")
        print("  Optional: --junit-xml for dashboards. See README + SECURITY.md.")
        print("  Landing: https://maxmccutcheon59.github.io/sandrail-site/")
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

    if args.command == "packs":
        if args.packs_command == "list":
            return _packs_list()
        if args.packs_command == "run":
            return _packs_run(args)
        parser.error(f"unknown packs command {args.packs_command}")
        return 2

    if args.command == "run":
        suite_path = Path(args.suite)
        cwd_root = Path(args.cwd_root) if args.cwd_root else suite_path.resolve().parent
        return _run_one_suite(
            suite_path=suite_path,
            backend_name=args.backend,
            cwd_root=cwd_root,
            timeout=float(args.timeout),
            allow_network=bool(args.allow_network),
            fmt=_resolve_format(args),
            junit_xml=args.junit_xml,
        )

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
