#!/usr/bin/env bash
# Install vnpy extras and compile vnpy_ctp from source on macOS (not editable).
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "scripts/install_macos.sh 仅用于 macOS。Linux 请运行 ./scripts/install_linux.sh" >&2
  exit 1
fi

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
# Python bindings come from vnpy_ctp 6.7.7.2; Mac CTP dylibs/headers are overlaid
# from SimNow official v6.7.13 (merged production/eval, Create* production mode).
CTP_TAG="6.7.7.2"
if [[ ! -d "${DEPS}/vnpy_ctp/.git" ]]; then
  git clone --depth 1 --branch "${CTP_TAG}" https://github.com/vnpy/vnpy_ctp.git "${DEPS}/vnpy_ctp"
fi

bash "${ROOT}/scripts/load_simnow_ctp.sh"

uv pip install "${DEPS}/vnpy_ctp"

echo "依赖已就绪（SimNow Mac CTP v6.7.13 + vnpy_ctp）。产品入口是 Web：./start.sh"
