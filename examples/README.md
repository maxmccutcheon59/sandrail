# Sandrail example suites

Built-in eval fixtures for local demos and CI. All fixture secrets are **synthetic**.

| Suite | Backend | What it exercises |
|-------|---------|-------------------|
| `suite.yaml` | `mock` | Smoke + refuse-injection |
| `cases/subprocess_smoke.yaml` | `subprocess` | Allow-listed echo / python3 |
| `cases/subprocess_deny.json` | `subprocess` | Allow-list deny (`curl`/`wget`/`bash`/`sh`/`nc` → exit 126) |
| `cases/timeout.yaml` | `subprocess` | Per-case timeout → exit 124 |
| `cases/prompt_injection_redaction.yaml` | `mock` | Harness redaction + refuse probe |

```bash
export SANDRAIL_FIXTURE_SECRET='synth-secret-DO-NOT-USE-9f3a2c1b'

sandrail run examples/suite.yaml --backend mock
sandrail run examples/cases/subprocess_smoke.yaml --backend subprocess
sandrail run examples/cases/subprocess_deny.json --backend subprocess
sandrail run examples/cases/timeout.yaml --backend subprocess
sandrail run examples/cases/prompt_injection_redaction.yaml --backend mock --format json

# Optional JUnit XML for CI
sandrail run examples/suite.yaml --backend mock --junit-xml /tmp/sandrail-junit.xml
```

Secure defaults remain: **network deny**, **shell=False**, command allow-list, cwd jail, timeouts, log redaction.
