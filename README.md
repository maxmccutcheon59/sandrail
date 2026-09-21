# Sandrail

**Local-first AI eval harness / agent sandbox CLI** — the kind of engineering software AI startups use to score agents safely on a laptop or in CI.

Sandrail runs JSON/YAML eval suites against pluggable backends (deterministic **mock**, allow-listed **subprocess**, optional **OpenAI-compatible** local API). Sandbox defaults are secure: **no network**, timeout, cwd jail, stdout/stderr capture, exit-code scoring, and **secret redaction** so prompt-injection fixtures cannot leak credentials into logs. Optional **JUnit XML** output plugs into existing CI dashboards.

> Not a full LLM. No training. Optional API hook only when `OPENAI_BASE_URL` is set; secrets via environment variables only.

| Sibling (portfolio) | Focus |
|---------------------|--------|
| **[Watchwire](https://github.com/maxmccutcheon59/watchwire)** | Local secret scanning |
| **[Sysguard](https://github.com/maxmccutcheon59/sysguard)** | Defensive host checks |
| **Sandrail** (this repo) | Agent eval + sandbox harness |

---

## Why startups care

AI product teams need **repeatable, local, CI-friendly evals** before they trust an agent in production:

1. **Regression gates** — lock behavior with YAML/JSON cases; fail the build when a prompt change regresses.
2. **Sandbox by default** — deny network unless opted in; cwd jail; allow-listed commands; never `shell=True` with user strings.
3. **Harness integrity** — prompt-injection fixtures assert secrets do not appear in reports (redaction).
4. **Pluggable backends** — start with a mock (fast CI), graduate to subprocess tools, optionally hit a local OpenAI-compatible server.
5. **CI exit codes + JUnit** — `0` all pass, `1` failures, `2` usage/load errors; optional `--junit-xml` for artifact upload.

---

## Install

```bash
git clone https://github.com/maxmccutcheon59/sandrail.git
cd sandrail
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Console script: **`sandrail`**. Runtime deps: **PyYAML** (+ stdlib).

---

## Quick start

```bash
# Deterministic mock suite (no network)
sandrail run examples/suite.yaml --backend mock

# Human table + JSON
sandrail run examples/suite.yaml --backend mock --format both

# Allow-listed subprocess under sandbox (network still denied)
sandrail run examples/cases/subprocess_smoke.yaml --backend subprocess

# Allow-list deny fixtures (curl/wget/bash/sh/nc → exit 126)
sandrail run examples/cases/subprocess_deny.json --backend subprocess

# Timeout fixtures (slow sleep → exit 124)
sandrail run examples/cases/timeout.yaml --backend subprocess

# Prompt-injection / redaction fixtures (synthetic secret via env)
export SANDRAIL_FIXTURE_SECRET='synth-secret-DO-NOT-USE-9f3a2c1b'
sandrail run examples/cases/prompt_injection_redaction.yaml --backend mock --format json

# Optional JUnit XML for CI consumers
sandrail run examples/suite.yaml --backend mock --junit-xml junit.xml

# Optional local OpenAI-compatible API (explicit network opt-in)
# export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
# export OPENAI_API_KEY=...          # from env only — never commit
# export OPENAI_MODEL=llama3.2
# sandrail run path/to/llm_suite.yaml --backend openai --allow-network
```

Exit codes: **0** pass · **1** one or more cases failed · **2** bad suite / usage.

See [`examples/README.md`](examples/README.md) for the full built-in suite index.

---

## Suite format

JSON or YAML. Object with `cases`, or a bare list:

```yaml
name: demo-suite
cases:
  - id: mock-hello
    description: Greeting
    input:
      prompt: "Say hello"
      respond: "hello from mock"
    expect:
      exit_code: 0
      stdout_contains: ["hello from mock"]
      secrets_must_not_leak: []   # optional list of literal secrets
    timeout_sec: 10               # optional per-case override
    tags: [smoke]
```

**Subprocess** backend expects `input.argv` as a **list of strings** (argument array — never a shell string):

```yaml
input:
  argv: ["python3", "-c", "print(2+2)"]
```

---

## Sandbox defaults

| Control | Default | Notes |
|---------|---------|--------|
| Network | **Deny** | Opt in with `--allow-network`. When denied, uses `unshare --net` if the kernel allows it; otherwise scrub proxy env (best-effort on restricted hosts). |
| Timeout | 30s | `--timeout` / per-case `timeout_sec` (timeout → exit `124`) |
| Cwd jail | Suite parent dir | `--cwd-root`; resolved paths must stay under root |
| Commands | Allow-list | `python3`, `echo`, `true`, `false`, `cat`, … — not `curl`/`bash`/`sh`/`wget`/`nc` |
| Shell | **Off** | `subprocess` with `shell=False` only |
| Logs | Redacted | Patterns + `secrets_must_not_leak` + known env secret values |

Full threat model: **[SECURITY.md](SECURITY.md)**.

---

## Reports

| Format | Flag | Use |
|--------|------|-----|
| Table | default / `--format table` | Human terminal |
| JSON | `--format json` or `--json` | Machine / scripting |
| Both | `--format both` | Table then JSON on stdout |
| JUnit XML | `--junit-xml PATH` | CI dashboards / artifacts (optional; combines with any format above) |

---

## Backends

| Name | Use |
|------|-----|
| `mock` | Deterministic local agent — CI default |
| `subprocess` | Allow-listed argv under the sandbox |
| `openai` | POST to `$OPENAI_BASE_URL/chat/completions` if set; requires `--allow-network` |

```bash
sandrail backends
```

---

## Security

See **[SECURITY.md](SECURITY.md)** and **[COMPLIANCE_NOTES.md](COMPLIANCE_NOTES.md)**.

- Authorized **local** use only — do not point this harness at third-party systems you do not own or lack written permission to test.
- Never commit `.env` / API keys. Use `.env.example` as a template.
- Fixture secrets are **synthetic**.

---

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

CI reference workflows (gitleaks + pip-audit + pytest) live under [`ci/`](ci/) when the pushing credential lacks the GitHub `workflow` scope — copy into `.github/workflows/` once that scope is available.

---

## License

MIT © Max McCutcheon (`MaxMcCutcheon1@outlook.com`)
