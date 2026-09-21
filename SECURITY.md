# Security Policy

## Supported versions

Security fixes are applied on the latest release of **Sandrail** on `main`. Older tags are not backported unless noted in a release.

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

- Network **denied** unless `--allow-network` is set.
- Subprocess execution uses **argument arrays** only (`shell=False`); never shell interpolation of user strings.
- Command **allow-list** for the subprocess backend.
- **Cwd jail** — resolved working directories must stay under `--cwd-root`.
- **Timeouts** on sandboxed processes.
- **Secret redaction** in reports (literal fixture secrets, common key patterns, known env secret values).
- Optional OpenAI-compatible calls use **`OPENAI_BASE_URL` / `OPENAI_API_KEY` from the environment only** — no per-case URL override (SSRF mitigation).

## Secrets and credentials

- Never commit secrets (`.env`, API keys, tokens, private keys).
- Use environment variables or a secrets manager.
- If a secret is exposed: **rotate it first**, then clean history if needed.

## Preferred disclosure process

1. Email the contact above with details.
2. Allow reasonable time for a fix before public disclosure.
3. Coordinated disclosure is appreciated; please do not weaponize findings.
