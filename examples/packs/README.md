# Sandrail suite packs

Copyable, real-world **suite packs** under `examples/packs/`. Each pack has a
`pack.yaml`, one or more suites, and a short README.

| Pack | Default backend | What it exercises |
|------|-----------------|-------------------|
| `ci_gate` | `mock` | CI regression gate founders can copy |
| `tool_sandbox` | `subprocess` | Allow-list smoke · deny (126) · timeout (124) |
| `redaction` | `mock` | Secret-leak-to-logs prevention |

## Commands

```bash
sandrail packs list
sandrail packs run ci_gate
sandrail packs run tool_sandbox
sandrail packs run redaction --format json

# Equivalent direct paths:
sandrail run examples/packs/ci_gate/suite.yaml --backend mock
sandrail run examples/packs/tool_sandbox/deny.yaml --backend subprocess
sandrail run examples/packs/redaction/suite.yaml --backend mock
```

Secure defaults unchanged: **network DENY**, **shell=False**, allow-list, cwd jail,
timeouts, log redaction. Authorized local use only — see `SECURITY.md`.
