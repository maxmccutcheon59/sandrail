# Pack: `ci_gate`

Mock **regression gate** to copy into a repo and wire to CI.

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

## Copy into a repo

1. Copy this directory (or just `suite.yaml`) next to the prompts you want to lock.
2. Lock needles that must not regress.
3. Install the CLI from git. There is no PyPI package named `sandrail`.

   ```bash
   pip install "sandrail @ git+https://github.com/maxmccutcheon59/sandrail.git"
   sandrail run path/to/suite.yaml --backend mock
   ```

   From a Sandrail checkout, `pip install -e .` and `sandrail packs run ci_gate` are the same gate. `sandrail demo` and `sandrail packs` need that checkout (they read `examples/`).
4. Keep **network deny** (default). Do not add `--allow-network` for this gate.

Secure defaults: network DENY · mock only · no shell · log redaction.
