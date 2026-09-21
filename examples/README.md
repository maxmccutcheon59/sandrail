# Sandrail example suites & packs

Stable paths for demos, landing copy, and CI.

All fixture secrets are **synthetic**.

## Suite packs (`examples/packs/`) — preferred founder entry

| Pack | Command | Backend | What it exercises |
|------|---------|---------|-------------------|
| `ci_gate` | `sandrail packs run ci_gate` | `mock` | Copyable CI regression gate |
| `tool_sandbox` | `sandrail packs run tool_sandbox` | `subprocess` | Allow-list · deny (126) · timeout (124) |
| `redaction` | `sandrail packs run redaction` | `mock` | Secret-leak-to-logs prevention |

```bash
sandrail packs list
sandrail packs run ci_gate
sandrail run examples/packs/ci_gate/suite.yaml --backend mock
```

See [`packs/README.md`](packs/README.md).

## Built-in suites (`examples/suites/`)

| Suite | Backend | What it exercises |
|-------|---------|-------------------|
| `suites/smoke.yaml` | `mock` | Smoke + refuse-injection |
| `suites/subprocess_smoke.yaml` | `subprocess` | Allow-listed echo / python3 |
| `suites/allowlist_deny.json` | `subprocess` | Allow-list deny (`curl`/`wget`/`bash`/`sh`/`nc` → exit 126) |
| `suites/timeout.yaml` | `subprocess` | Per-case timeout → exit 124 |
| `suites/redaction.yaml` | `mock` | Harness redaction + refuse probe |
| `suites/mock_pass_fail.yaml` | `mock` | Intentional pass+fail (expect exit 1) |

```bash
pip install -e .
sandrail demo

sandrail run examples/suites/smoke.yaml --backend mock
sandrail run examples/suites/subprocess_smoke.yaml --backend subprocess
sandrail run examples/suites/allowlist_deny.json --backend subprocess
sandrail run examples/suites/timeout.yaml --backend subprocess
export SANDRAIL_FIXTURE_SECRET='synth-secret-DO-NOT-USE-9f3a2c1b'
sandrail run examples/suites/redaction.yaml --backend mock --format json
sandrail run examples/suites/mock_pass_fail.yaml --backend mock  # expect exit 1
```

`examples/cases/` mirrors older fixtures for docs/tests. Prefer **`examples/packs/`** and **`examples/suites/`**.

Secure defaults: **network deny**, **shell=False**, command allow-list, cwd jail, timeouts, log redaction.
