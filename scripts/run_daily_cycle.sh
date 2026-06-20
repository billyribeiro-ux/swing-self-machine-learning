#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${ROOT_DIR}/.venv/bin/python"

if [ ! -x "${PYTHON}" ]; then
  echo "Missing .venv. Run ./scripts/bootstrap_mac.sh first."
  exit 1
fi

cd "${ROOT_DIR}"
exec "${PYTHON}" -m swing_rsi.cli daily-cycle "$@"
