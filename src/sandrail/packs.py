"""Discover and resolve bundled suite packs under examples/packs/."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sandrail.loader import _load_raw
from sandrail.paths import examples_dir


@dataclass(frozen=True)
class PackSuiteRef:
    """One suite file belonging to a pack."""

    file: str
    backend: str | None = None
    # If True, suite is expected to exit 1 (demo / regression illustration)
    expect_fail: bool = False
    description: str = ""


@dataclass(frozen=True)
class Pack:
    """A copyable suite pack founders can run or vendor into their repo."""

    name: str
    path: Path
    description: str = ""
    default_backend: str = "mock"
    allow_network: bool = False
    suites: list[PackSuiteRef] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def suite_path(self, ref: PackSuiteRef) -> Path:
        p = (self.path / ref.file).resolve()
        try:
            p.relative_to(self.path.resolve())
        except ValueError as exc:
            raise ValueError(
                f"pack suite path escapes pack root: {ref.file!r} (pack={self.name})"
            ) from exc
        return p


def packs_dir() -> Path:
    """Return examples/packs/ (must exist for pack commands)."""
    d = examples_dir() / "packs"
    if not d.is_dir():
        raise FileNotFoundError(
            f"packs directory not found: {d}. "
            "Run from a Sandrail checkout or set SANDRAIL_EXAMPLES."
        )
    return d.resolve()


def _safe_pack_name(name: str) -> str:
    n = (name or "").strip()
    if not n or n in {".", ".."} or "/" in n or "\\" in n or ".." in n:
        raise ValueError(f"invalid pack name: {name!r}")
    # Allow founders to use simple identifiers only
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if any(c not in allowed for c in n):
        raise ValueError(
            f"invalid pack name {name!r}: use letters, digits, underscore, hyphen only"
        )
    return n


def _default_suite_file(pack_path: Path) -> str | None:
    for cand in ("suite.yaml", "suite.yml", "suite.json"):
        if (pack_path / cand).is_file():
            return cand
    return None


def _parse_pack_yaml(pack_path: Path, name: str) -> Pack:
    meta_path = pack_path / "pack.yaml"
    if not meta_path.is_file():
        meta_path = pack_path / "pack.yml"
    meta: dict[str, Any] = {}
    if meta_path.is_file():
        raw = _load_raw(meta_path)
        if raw is None:
            meta = {}
        elif not isinstance(raw, dict):
            raise ValueError(f"pack.yaml must be a mapping: {meta_path}")
        else:
            meta = raw

    description = str(meta.get("description") or "").strip()
    default_backend = str(meta.get("default_backend") or "mock").strip() or "mock"
    allow_network = bool(meta.get("allow_network", False))
    tags = [str(t) for t in (meta.get("tags") or [])]
    pack_name = str(meta.get("name") or name).strip() or name

    suites_raw = meta.get("suites")
    refs: list[PackSuiteRef] = []
    if isinstance(suites_raw, list) and suites_raw:
        for i, item in enumerate(suites_raw):
            if isinstance(item, str):
                refs.append(PackSuiteRef(file=item))
            elif isinstance(item, dict):
                f = item.get("file") or item.get("path") or item.get("suite")
                if not f:
                    raise ValueError(f"pack {name}: suites[{i}] missing 'file'")
                refs.append(
                    PackSuiteRef(
                        file=str(f),
                        backend=str(item["backend"]) if item.get("backend") else None,
                        expect_fail=bool(item.get("expect_fail", False)),
                        description=str(item.get("description") or ""),
                    )
                )
            else:
                raise ValueError(f"pack {name}: suites[{i}] must be a string or object")
    else:
        default_file = _default_suite_file(pack_path)
        if default_file is None:
            raise ValueError(
                f"pack {name}: no pack.yaml suites and no suite.yaml/json in {pack_path}"
            )
        refs.append(PackSuiteRef(file=default_file))

    # Path traversal guard on every declared suite file
    pack = Pack(
        name=pack_name,
        path=pack_path.resolve(),
        description=description,
        default_backend=default_backend,
        allow_network=allow_network,
        suites=refs,
        tags=tags,
    )
    for ref in pack.suites:
        sp = pack.suite_path(ref)
        if not sp.is_file():
            raise FileNotFoundError(f"pack {name}: suite file missing: {ref.file}")
    return pack


def list_packs() -> list[Pack]:
    """List installed suite packs (sorted by name)."""
    root = packs_dir()
    packs: list[Pack] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        try:
            packs.append(_parse_pack_yaml(child, child.name))
        except (OSError, ValueError, RuntimeError, FileNotFoundError):
            # Skip broken pack dirs; list still returns valid ones
            continue
    return packs


def get_pack(name: str) -> Pack:
    """Load a single pack by directory name."""
    safe = _safe_pack_name(name)
    root = packs_dir()
    pack_path = (root / safe).resolve()
    try:
        pack_path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"pack path escapes packs root: {name!r}") from exc
    if not pack_path.is_dir():
        available = ", ".join(p.name for p in list_packs()) or "(none)"
        raise FileNotFoundError(f"pack not found: {safe!r}. available: {available}")
    return _parse_pack_yaml(pack_path, safe)
