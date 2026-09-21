"""Secure-by-default process sandbox helpers.

- Argument arrays only (never shell=True with user strings)
- Optional network deny via `unshare --net` when the kernel allows it
- Cwd jail: resolved path must stay under an allowed root
- Timeouts enforced via subprocess.run
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class SandboxError(ValueError):
    """Raised when a sandbox policy would be violated."""


@dataclass(frozen=True)
class SandboxPolicy:
    cwd_root: Path
    timeout_sec: float = 30.0
    allow_network: bool = False
    # Absolute paths (or basenames resolved via PATH) that may be executed
    allow_commands: frozenset[str] = frozenset(
        {
            "python",
            "python3",
            sys.executable,
            "echo",
            "true",
            "false",
            "cat",
            "printf",
            "ls",
            "head",
            "wc",
        }
    )
    env_allowlist: frozenset[str] = frozenset(
        {
            "PATH",
            "HOME",
            "USER",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "TERM",
            "TMPDIR",
            "TMP",
            "TEMP",
            "PYTHONPATH",
            "VIRTUAL_ENV",
        }
    )


def resolve_jail_cwd(requested: str | Path | None, root: Path) -> Path:
    """Resolve cwd and ensure it is under root (after realpath)."""
    root_r = root.resolve()
    if requested is None:
        return root_r
    cand = Path(requested)
    if not cand.is_absolute():
        cand = root_r / cand
    resolved = cand.resolve()
    try:
        resolved.relative_to(root_r)
    except ValueError as exc:
        raise SandboxError(
            f"cwd jail violation: {resolved} is outside allowed root {root_r}"
        ) from exc
    if not resolved.is_dir():
        raise SandboxError(f"cwd is not a directory: {resolved}")
    return resolved


def _command_allowed(argv0: str, policy: SandboxPolicy) -> bool:
    name = Path(argv0).name
    if argv0 in policy.allow_commands or name in policy.allow_commands:
        return True
    try:
        if Path(argv0).resolve() == Path(sys.executable).resolve():
            return True
    except OSError:
        pass
    return False


def build_env(policy: SandboxPolicy, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Minimal env: allow-listed keys only (+ explicit extras for the child)."""
    env: dict[str, str] = {}
    for key in policy.env_allowlist:
        if key in os.environ:
            env[key] = os.environ[key]
    if extra:
        for k, v in extra.items():
            env[str(k)] = str(v)
    env.setdefault("PATH", os.environ.get("PATH", "/usr/bin:/bin"))
    # Soft network hygiene even without a netns: drop common proxy knobs
    if not policy.allow_network:
        for proxy_key in (
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "all_proxy",
            "NO_PROXY",
            "no_proxy",
        ):
            env.pop(proxy_key, None)
    return env


@lru_cache(maxsize=1)
def unshare_net_works() -> bool:
    """True if `unshare --net` can create a network namespace in this environment."""
    unshare = shutil.which("unshare")
    if unshare is None:
        return False
    try:
        proc = subprocess.run(
            [unshare, "--net", "--", "/bin/true"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def run_sandboxed(
    argv: Sequence[str],
    *,
    policy: SandboxPolicy,
    cwd: str | Path | None = None,
    stdin_data: str | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run argv as an argument array (shell=False always).

    When allow_network is False and `unshare --net` works, wrap so the child
    has an empty network namespace. Otherwise still enforce allow-list, cwd jail,
    timeout, and proxy-env scrubbing (best-effort deny on restricted hosts).
    """
    if not argv:
        raise SandboxError("empty argv")
    if not all(isinstance(a, str) for a in argv):
        raise SandboxError("argv must be a sequence of strings")
    if not _command_allowed(argv[0], policy):
        raise SandboxError(
            f"command not allow-listed: {argv[0]!r} "
            f"(allowed basenames/paths: {sorted(policy.allow_commands)[:12]}…)"
        )

    jail_cwd = resolve_jail_cwd(cwd, policy.cwd_root)
    env = build_env(policy, extra_env)

    exe = argv[0]
    if "/" not in exe:
        which = shutil.which(exe)
        if which is None:
            raise SandboxError(f"command not found on PATH: {exe}")
        exe = which

    final_argv: list[str] = [exe, *list(argv[1:])]
    if not policy.allow_network and unshare_net_works():
        unshare = shutil.which("unshare")
        assert unshare is not None
        final_argv = [unshare, "--net", "--", exe, *list(argv[1:])]

    # CRITICAL: shell=False — never interpolate user strings into a shell
    return subprocess.run(
        final_argv,
        cwd=str(jail_cwd),
        env=env,
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=policy.timeout_sec,
        shell=False,
        check=False,
    )
