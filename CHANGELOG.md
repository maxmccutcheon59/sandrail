# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-09-21

### Added

- **Suite packs** under `examples/packs/` founders can copy:
  - `ci_gate` — mock regression gate (green `suite.yaml` + optional `expected_fail.yaml` demo)
  - `tool_sandbox` — allow-list smoke, deny (exit 126), timeout (exit 124)
  - `redaction` — secret-leak-to-logs prevention (fixture secret, sk-, Bearer, password=, refuse probes)
- CLI: `sandrail packs list` and `sandrail packs run <name>` (path-safe pack names; cwd jail on suite paths).
- Equivalent documented paths: `sandrail run examples/packs/<name>/…`.
- `sandrail demo` mentions packs + landing URL; optional `--with-packs`.
- Mock backend: broader refuse patterns for system-prompt / API-key exfil phrasing (still local-only fixtures).
- Tests for pack discovery, `packs list` / `packs run`, and pack suite execution.
- README landing link: https://maxmccutcheon59.github.io/sandrail-site/

### Changed

- Package version bumped to **0.3.0**.
- Founder demo script prints pack commands.
- `examples/README.md` indexes packs ahead of legacy suites.

### Security

- Secure defaults unchanged: **network deny**, **`shell=False`** / argument arrays only, command allow-list, cwd jail, timeouts, log redaction.
- Packs refuse to honor `--allow-network` unless the pack itself declares `allow_network: true` (bundled packs stay deny).
- Pack suite paths are constrained under the pack directory (no path traversal via `pack.yaml`).

## [0.2.0] — 2026-09-21

### Added
- Stable landing commands: `pip install -e .`, `sandrail demo`, `sandrail run examples/suites/…`.
- `scripts/founder_demo.sh` founder wow wrapper.
- Canonical `examples/suites/` (smoke, timeout, allowlist deny, redaction, mock pass/fail).

- Optional **JUnit XML** reports via `--junit-xml PATH` for CI consumers (GitHub Actions, Jenkins, GitLab, etc.). Streams in the report are already redacted by the runner.
- Expanded built-in eval examples:
  - `examples/cases/timeout.yaml` — per-case timeout → exit `124`
  - richer `examples/cases/subprocess_deny.json` — deny `curl` / `wget` / `bash` / `sh` / `nc`
  - richer `examples/cases/prompt_injection_redaction.yaml` — fixture secret, `sk-` pattern, Bearer pattern, refuse probe
  - `examples/README.md` index of suites
- Stronger **SECURITY.md**: secure-defaults table, STRIDE-oriented **threat model**, trust boundaries, residual risks, lightweight incident response.
- Additional unit/integration tests (JUnit writer, timeout suite, expanded deny/redaction coverage, CLI `--junit-xml`).

### Changed

- Package version bumped to **0.2.0**.
- Demo `examples/suite.yaml` gains a stderr scoring smoke case.
- OpenAI-compat `User-Agent` reports `sandrail/0.2.0`.

### Security

- Secure defaults unchanged and reaffirmed: **network deny**, **`shell=False`** / argument arrays only, command allow-list, cwd jail, timeouts, log redaction, env-only API base URL (no per-case SSRF).

## [0.1.0] — 2026-09-21

### Added

- Initial public release of **Sandrail**: local-first AI eval harness / agent sandbox CLI.
- Backends: `mock`, `subprocess` (allow-listed argv), optional `openai` (env `OPENAI_BASE_URL`).
- Sandbox defaults: deny network, timeout, cwd jail, stdout/stderr capture, exit-code scoring.
- Secret redaction + prompt-injection fixtures verifying harness log integrity.
- Reports: human table + JSON; CI-friendly exit codes.
- Docs: README, SECURITY.md, COMPLIANCE_NOTES.md, MIT license, CI templates under `ci/`.
