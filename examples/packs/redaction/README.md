# Pack: `redaction`

**Secret-leak-to-logs prevention** — assert reports never contain raw fixture secrets.

## Run

```bash
export SANDRAIL_FIXTURE_SECRET='synth-secret-DO-NOT-USE-9f3a2c1b'
sandrail packs run redaction
# or:
sandrail run examples/packs/redaction/suite.yaml --backend mock --format json
```

`sandrail packs run redaction` sets the synthetic fixture secret if unset.

Fixture secrets are **synthetic**. Never put real credentials in suites or git.
