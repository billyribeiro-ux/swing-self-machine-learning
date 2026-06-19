#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

printf "Paste your FMP API key, then press Return. It will not be displayed: "
IFS= read -r -s FMP_KEY
printf "\n"

if [[ -z "${FMP_KEY}" ]]; then
  echo "No key was entered. Nothing changed."
  exit 1
fi

umask 077
printf 'FMP_API_KEY=%s\nFMP_BASE_URL=https://financialmodelingprep.com/stable\n' "$FMP_KEY" > .env
chmod 600 .env
unset FMP_KEY

echo "FMP configuration saved locally in .env with owner-only permissions."
echo "The .env file is excluded from Git and project ZIP files."

if [[ -x .venv/bin/python ]]; then
  .venv/bin/python -m swing_rsi.cli doctor
  echo
  echo "Testing FMP access with a small AAPL request..."
  .venv/bin/python -m swing_rsi.cli fmp-check
else
  echo "Run ./scripts/bootstrap_mac.sh next, then run:"
  echo "source .venv/bin/activate"
  echo "python -m swing_rsi.cli fmp-check"
fi
