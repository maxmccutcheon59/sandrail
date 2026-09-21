# Changelog

## [0.1.0] — 2026-09-21

### Added

- Initial public release of **Sandrail**: local-first AI eval harness / agent sandbox CLI.
- Backends: `mock`, `subprocess` (allow-listed argv), optional `openai` (env `OPENAI_BASE_URL`).
- Sandbox defaults: deny network, timeout, cwd jail, stdout/stderr capture, exit-code scoring.
- Secret redaction + prompt-injection fixtures verifying harness log integrity.
- Reports: human table + JSON; CI-friendly exit codes.
- Docs: README, SECURITY.md, COMPLIANCE_NOTES.md, MIT license, CI templates under `ci/`.
