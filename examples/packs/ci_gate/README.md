# Pack: `ci_gate`

Mock **regression gate** founders can copy into a product repo and wire to CI.

## Run

```bash
sandrail packs run ci_gate
# or:
sandrail run examples/packs/ci_gate/suite.yaml --backend mock
```

Green gate exit codes: **0** pass · **1** regression · **2** load/usage error.

Optional JUnit for CI artifacts:

```bash
sandrail packs run ci_gate --junit-xml junit-ci-gate.xml
```

## See a red gate (local demo only)

```bash
sandrail run examples/packs/ci_gate/expected_fail.yaml --backend mock
# expect exit 1
```

## Copy into your repo

1. Copy this directory (or just `suite.yaml`) next to your agent prompts.
2. Lock needles that must not regress.
3. Run in CI after `pip install sandrail` (or `pip install -e .` from a checkout).
4. Keep **network deny** (default). Do not add `--allow-network` for this gate.

Secure defaults: network DENY · mock only · no shell · log redaction.
