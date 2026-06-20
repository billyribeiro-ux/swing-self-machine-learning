#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export HOME="${ROOT_DIR}"
export STREAMLIT_CONFIG_DIR="${ROOT_DIR}/.streamlit"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_CLIENT_TOOLBAR_MODE=minimal
mkdir -p "${STREAMLIT_CONFIG_DIR}"
printf '[browser]\ngatherUsageStats = false\n\n[client]\ntoolbarMode = "minimal"\n' > "${STREAMLIT_CONFIG_DIR}/config.toml"
if [[ ! -f "${STREAMLIT_CONFIG_DIR}/credentials.toml" ]]; then
  printf '[general]\nemail = ""\n' > "${STREAMLIT_CONFIG_DIR}/credentials.toml"
fi

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run: ./scripts/bootstrap_mac.sh"
  exit 1
fi

if [[ ! -x .venv/bin/streamlit ]]; then
  echo "Streamlit is not installed in .venv."
  echo 'Run: .venv/bin/python -m pip install -e ".[all,dev,dashboard]"'
  exit 1
fi

exec .venv/bin/streamlit run dashboard/app.py --server.address localhost
