#!/usr/bin/env bash
# Install vnpy extras and compile vnpy_ctp from source (not editable).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
DEPS="${ROOT}/.deps"

export PATH="/opt/homebrew/bin:${PATH}"
export TA_INCLUDE_PATH="${TA_INCLUDE_PATH:-/opt/homebrew/opt/ta-lib/include}"
export TA_LIBRARY_PATH="${TA_LIBRARY_PATH:-/opt/homebrew/opt/ta-lib/lib}"

if [[ ! -x "${PY}" ]]; then
  echo "missing venv python: ${PY}" >&2
  exit 1
fi

uv pip install -e "${ROOT}"

mkdir -p "${DEPS}"
# Mac CTP official API is 6.7.7; 6.7.11 headers do not compile on darwin.
CTP_TAG="6.7.7.2"
if [[ ! -d "${DEPS}/vnpy_ctp/.git" ]]; then
  git clone --depth 1 --branch "${CTP_TAG}" https://github.com/vnpy/vnpy_ctp.git "${DEPS}/vnpy_ctp"
fi

uv pip install "${DEPS}/vnpy_ctp"
