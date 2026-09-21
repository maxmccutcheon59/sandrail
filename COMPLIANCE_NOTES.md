# Compliance Notes — Sandrail

> Human / lawyer review recommended before any commercial or organizational deployment.
> This file flags legal and compliance-relevant aspects; it is **not** legal advice.

## Product posture

- **Local-first eval harness / agent sandbox CLI** for scoring pluggable agent backends (mock, allow-listed subprocess, optional OpenAI-compatible local API).
- **Not a full LLM** and **does not train models**.
- **Secure-by-default:** network deny unless opted in; no `shell=True` with user strings; argument arrays only; cwd jail; timeouts; log redaction.
- Portfolio / educational project demonstrating eval-harness engineering used by AI startups.

## Authorized systems only

Operators must only run Sandrail against:

1. Agents, scripts, and APIs **they own**, or
2. Environments where they have **written authorization** to run evals / sandboxed commands.

**No unauthorized scanning of third-party systems.** Do not use Sandrail to probe, scrape, or attack hosts you do not control. Unauthorized use can implicate the CFAA and related computer-crime / unauthorized-access laws, as well as contractual Terms of Service. See also `SECURITY.md`.

## Data handled

| Data | Collected? | Stored? | Shared? |
|------|------------|---------|---------|
| Eval suite files (JSON/YAML) | Read locally | Not retained by tool (stdout/files you choose) | No (local only) |
| Captured stdout/stderr of agents | In-memory for scoring/report | Only if you redirect output | No (local only) |
| `OPENAI_API_KEY` / similar | Read from env when openai backend used | Never written by Sandrail | Sent only to `OPENAI_BASE_URL` you configure |
| Telemetry / analytics | **None** | — | — |
| Accounts / cloud sync | **None** | — | — |

Fixture secrets in examples/tests are **synthetic** and must never be real credentials.

## Privacy / regulatory flags

- **No SaaS, no accounts, no intentional PII collection** in the default CLI.
- If an operator’s eval prompts or agent outputs contain personal data, secrets, or regulated content, **the operator** remains responsible for lawful handling (GDPR/CCPA/etc.). The tool does not implement DSAR export/deletion because it does not operate a service that stores user PII.
- **AI disclosure:** optional openai backend calls a user-configured local/compatible API; Sandrail does not itself generate foundation-model weights.
- **Export controls:** general-purpose developer utility; no cryptographic export product claims. Escalate if packaging for sanctioned jurisdictions.

## Security tooling ethics

- Sandbox and scoring aids only — not an exploit framework, scanner for third-party networks, or unauthorized-access tool.
- Prompt-injection fixtures exist to verify **harness redaction**, not to teach attacks against production systems you do not own.

## Items needing human review before commercial use

- [ ] Privacy Policy / Terms if a hosted or multi-user product is built on top of this CLI
- [ ] Organizational acceptable-use policy alignment for internal agent evals
- [ ] Any future network features beyond explicit `--allow-network` + env-configured API base URL — fresh threat model + privacy review
- [ ] Retention policy if reports are archived in shared CI artifact stores
