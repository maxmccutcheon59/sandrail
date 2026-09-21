"""Sandbox policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from sandrail.sandbox import SandboxError, SandboxPolicy, resolve_jail_cwd, run_sandboxed


def test_cwd_jail_blocks_escape(tmp_path: Path):
    root = tmp_path / "jail"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(SandboxError, match="cwd jail"):
        resolve_jail_cwd(outside, root)


def test_cwd_jail_allows_inside(tmp_path: Path):
    root = tmp_path / "jail"
    sub = root / "sub"
    sub.mkdir(parents=True)
    assert resolve_jail_cwd("sub", root) == sub.resolve()


def test_run_echo_ok(tmp_path: Path):
    policy = SandboxPolicy(cwd_root=tmp_path, allow_network=False, timeout_sec=10)
    proc = run_sandboxed(["echo", "hi"], policy=policy)
    assert proc.returncode == 0
    assert "hi" in proc.stdout


def test_disallow_unknown_command(tmp_path: Path):
    policy = SandboxPolicy(cwd_root=tmp_path, allow_network=False)
    with pytest.raises(SandboxError, match="not allow-listed"):
        run_sandboxed(["curl", "https://example.com"], policy=policy)


def test_never_shell_true_path(tmp_path: Path):
    """Metacharacters must not be interpreted by a shell."""
    policy = SandboxPolicy(cwd_root=tmp_path, allow_network=False)
    # echo with a string that would expand if shell=True
    proc = run_sandboxed(["echo", "$(whoami)"], policy=policy)
    assert proc.returncode == 0
    assert "$(whoami)" in proc.stdout or "\\$(whoami)" in proc.stdout


def test_timeout_expires(tmp_path: Path):
    policy = SandboxPolicy(cwd_root=tmp_path, allow_network=False, timeout_sec=0.3)
    import subprocess as sp

    with pytest.raises(sp.TimeoutExpired):
        run_sandboxed(
            ["python3", "-c", "import time; time.sleep(5)"],
            policy=policy,
        )


def test_build_env_scrubs_proxy_when_net_denied(tmp_path: Path, monkeypatch):
    from sandrail.sandbox import build_env

    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:9")
    policy = SandboxPolicy(cwd_root=tmp_path, allow_network=False)
    env = build_env(policy)
    assert "HTTP_PROXY" not in env
    assert "https_proxy" not in env


def test_empty_argv_rejected(tmp_path: Path):
    policy = SandboxPolicy(cwd_root=tmp_path)
    with pytest.raises(SandboxError, match="empty argv"):
        run_sandboxed([], policy=policy)
