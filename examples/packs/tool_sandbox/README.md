# Pack: `tool_sandbox`

Subprocess **allow-list / timeout / deny** cases under secure defaults.

## Run

```bash
sandrail packs run tool_sandbox
# or run individual suites:
sandrail run examples/packs/tool_sandbox/allowlist_smoke.yaml --backend subprocess
sandrail run examples/packs/tool_sandbox/deny.yaml --backend subprocess
sandrail run examples/packs/tool_sandbox/timeout.yaml --backend subprocess
```

Expect exit **0** when deny/timeout fixtures score correctly (denied commands → 126, timed-out → 124).

Secure defaults: network DENY · shell=False · argv arrays only · cwd jail · timeouts.
