"""Sandrail CLI — local-first AI eval harness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sandrail import __version__
from sandrail.backends import get_backend
from sandrail.loader import load_suite
from sandrail.report import write_json, write_table
from sandrail.runner import default_policy, run_suite


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sandrail",
        description=(
            "Local-first AI eval harness / agent sandbox CLI. "
            "Network denied by default; secrets via env only."
        ),
    )
    p.add_argument("--version", action="version", version=f"sandrail {__version__}")

    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run an eval suite against a backend")
    run_p.add_argument("suite", type=str, help="Path to suite JSON/YAML")
    run_p.add_argument(
        "--backend",
        "-b",
        default="mock",
        choices=["mock", "subprocess", "openai"],
        help="Agent backend (default: mock)",
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

    sub.add_parser("backends", help="List available backends")
    sub.add_parser("version", help="Print version")

    return p


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
        return 0

    if args.command == "run":
        suite_path = Path(args.suite)
        try:
            name, cases, _meta = load_suite(suite_path)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"error: failed to load suite: {exc}", file=sys.stderr)
            return 2

        cwd_root = Path(args.cwd_root) if args.cwd_root else suite_path.resolve().parent
        policy = default_policy(
            cwd_root,
            timeout_sec=args.timeout,
            allow_network=bool(args.allow_network),
        )

        try:
            backend = get_backend(args.backend)
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        report = run_suite(name, cases, backend, policy)

        fmt = args.format
        if fmt is None:
            fmt = "json" if args.json else "table"

        if fmt in {"table", "both"}:
            write_table(report)
        if fmt in {"json", "both"}:
            write_json(report)

        return 0 if report.ok else 1

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
