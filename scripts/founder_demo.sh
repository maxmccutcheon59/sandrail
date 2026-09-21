#!/usr/bin/env bash
# Stable landing / founder wow path (documented in README).
# Exact commands the GTM landing expects:
#   pip install -e .
#   sandrail demo
#   sandrail run examples/suites/...
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export SANDRAIL_FIXTURE_SECRET="${SANDRAIL_FIXTURE_SECRET:-synth-secret-DO-NOT-USE-9f3a2c1b}"
export SANDRAIL_EXAMPLES="${SANDRAIL_EXAMPLES:-$ROOT/examples}"

echo "==> Sandrail founder demo"
echo "    repo: $ROOT"
echo "    commands: pip install -e . && sandrail demo"
echo

if [[ ! -x "$ROOT/.venv/bin/sandrail" ]] && ! command -v sandrail >/dev/null 2>&1; then
  echo "→ creating .venv and running: pip install -e ."
  python3 -m venv "$ROOT/.venv"
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  pip install -e . -q
fi

if command -v sandrail >/dev/null 2>&1; then
  SANDRAIL_BIN=(sandrail)
elif [[ -x "$ROOT/.venv/bin/sandrail" ]]; then
  SANDRAIL_BIN=("$ROOT/.venv/bin/sandrail")
else
  echo "error: sandrail not found; run: pip install -e ." >&2
  exit 2
fi

echo "→ ${SANDRAIL_BIN[*]} demo"
"${SANDRAIL_BIN[@]}" demo "$@"
echo
echo "→ example suite commands (stable paths):"
echo "    sandrail run examples/suites/smoke.yaml --backend mock"
echo "    sandrail run examples/suites/timeout.yaml --backend subprocess"
echo "    sandrail run examples/suites/allowlist_deny.json --backend subprocess"
echo "    sandrail run examples/suites/redaction.yaml --backend mock"
