# Security Policy

## Supported versions

Security fixes are applied on the latest release of **Sandrail** on `main`. Older tags are not backported unless noted in a release.

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes |
| 0.1.x   | Best-effort until 0.2 is adopted |
| < 0.1   | No |

## Reporting a vulnerability

Please report security issues privately — do **not** open a public GitHub issue for undisclosed vulnerabilities.

- **Contact:** [MaxMcCutcheon1@outlook.com](mailto:MaxMcCutcheon1@outlook.com)
- Include: affected version/commit, reproduction steps, impact, and any suggested fix.
- You should receive an acknowledgment within a few business days.

We will work with you to understand and remediate the issue, then credit reporters who want acknowledgment (optional).

## Authorized testing only

Sandrail is a **local-first eval / sandbox harness** for systems and code **you own** or for which you have **explicit written authorization**.

Unauthorized scanning, access, or testing of third-party systems may violate the Computer Fraud and Abuse Act (CFAA), similar laws, and site Terms of Service. Do not use this software to attack, probe, or exfiltrate from systems without permission.

## Secure-by-default controls

These defaults are intentional and must not be weakened for convenience:

| Control | Default | Notes |
|---------|---------|--------|
| Network | **Deny** | Opt in only with `--allow-network`. When denied, prefer `unshare --net` if the kernel allows it; otherwise scrub proxy env (best-effort). |
| Shell | **Off** | `subprocess` always uses `shell=False` and argument arrays — never shell-string interpolation of user/suite data. |
| Commands | Allow-list | Subprocess backend only runs allow-listed basenames/paths (`python3`, `echo`, `true`, `false`, `cat`, …). Not `curl`/`wget`/`bash`/`sh`/`nc`. |
| Cwd jail | On | Resolved working directories must stay under `--cwd-root` after `realpath`. |
| Timeouts | On | Default 30s; per-case `timeout_sec` override; timed-out cases score exit `124`. |
| Log redaction | On | Literal fixture secrets, common key patterns, and known env secret values are scrubbed before reports (table/JSON/JUnit). |
| OpenAI URL | Env only | Optional openai backend uses **`OPENAI_BASE_URL` / `OPENAI_API_KEY` from the environment only** — no per-case URL override (SSRF mitigation). |
| Suite parsing | Safe | YAML via `yaml.safe_load` only; never `yaml.load` / unsafe deserialize. |

## Threat model

Sandrail assumes a **developer laptop or CI runner** executing eval suites against mock agents, allow-listed local tools, or an explicitly configured OpenAI-compatible endpoint. It is **not** a multi-tenant cloud sandbox, container escape mitigator, or exploit framework.

### Assets

- Eval suite files and captured agent stdout/stderr (may contain secrets if an agent misbehaves).
- Host filesystem under the cwd jail root.
- Environment secrets (`OPENAI_API_KEY`, fixture secrets, etc.).
- Integrity of CI reports (JSON / JUnit) used as merge gates.

### Trust boundaries

1. **Suite author → harness:** Suite YAML/JSON is treated as untrusted structured input. It is schema-validated into typed cases; YAML uses `safe_load` only.
2. **Harness → child process:** Subprocess argv is allow-listed; `shell=False`; cwd jailed; timeout enforced; network denied unless opted in.
3. **Harness → optional HTTP API:** Only when `--allow-network` **and** `OPENAI_BASE_URL` are set. Base URL comes from env, never from case fields.
4. **Harness → report consumers:** Table/JSON/JUnit must not re-emit raw fixture/env secrets (redaction before serialize).

### STRIDE-oriented summary

| Category | Risk | Mitigations in Sandrail |
|----------|------|-------------------------|
| **Spoofing** | Fake “backend” or forged API host | Backends are selected by CLI enum; openai URL from env only (no case override). |
| **Tampering** | Suite or report rewrite mid-run | Local single-process run; reports written after scoring; no remote suite fetch. |
| **Repudiation** | Unclear which case failed in CI | Stable case `id`s; optional JUnit XML with failures + redacted streams. |
| **Information disclosure** | Secrets in logs / CI artifacts | Redaction of literals + patterns + env secret values; synthetic fixtures in examples. |
| **Denial of service** | Hung agent blocks CI | Timeouts (default + per-case); timeout → exit 124. |
| **Elevation of privilege** | Escape to shell / network / parent dirs | `shell=False`; command allow-list; cwd jail; network deny / netns when available. |

### Out of scope (explicit non-goals)

- Isolating a **malicious** binary with kernel-level guarantees on every host (netns may be unavailable in restricted CI; deny is then best-effort via allow-list + proxy scrub).
- Preventing a deliberately allow-listed `python3 -c` payload from reading files the OS user can already read (cwd jail + allow-list reduce accident surface; they are not a VM).
- Multi-tenant SaaS isolation, browser sandboxing, or malware analysis.
- Offensive scanning of third-party networks or unauthorized systems.

### Residual risks (operator responsibility)

- Expanding `allow_commands` or passing `--allow-network` increases blast radius — treat as a security-sensitive change.
- Archiving unredacted raw agent output outside Sandrail bypasses harness controls.
- Pointing `OPENAI_BASE_URL` at an untrusted host can exfiltrate prompts; keep it loopback / org-approved.

## Secrets and credentials

- Never commit secrets (`.env`, API keys, tokens, private keys).
- Use environment variables or a secrets manager.
- If a secret is exposed: **rotate it first**, then clean history if needed.
- Example fixture secret (`SANDRAIL_FIXTURE_SECRET`) is synthetic and must never be a real credential.

## Preferred disclosure process

1. Email the contact above with details.
2. Allow reasonable time for a fix before public disclosure.
3. Coordinated disclosure is appreciated; please do not weaponize findings.

## Incident response (lightweight)

1. Acknowledge the report and confirm severity.
2. Reproduce on a clean checkout; patch secure defaults first where applicable.
3. Rotate any exposed credentials before public discussion.
4. Ship a fixed release; note the issue in `CHANGELOG.md` without enabling abuse.
5. If personal data was involved in a real deployment built on this CLI, follow applicable breach-notification law (operator responsibility — see `COMPLIANCE_NOTES.md`).
