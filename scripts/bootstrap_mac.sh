#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed or is not on PATH."
  echo "Install Python 3.12 or 3.13, then run this script again."
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ is required; found {sys.version.split()[0]}")
print(f"Using Python {sys.version.split()[0]}")
PY

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all,dev]"
pytest

echo
echo "Setup complete."
echo "Activate later with: source .venv/bin/activate"
echo "Run the demo with: python -m swing_rsi.cli demo"
