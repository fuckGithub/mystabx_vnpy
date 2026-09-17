#!/usr/bin/env bash
# Install mystabx Web stack + compile vnpy_ctp from source on macOS (not editable).
# Web-only: does not install PySide6 / qdarkstyle / pyqtgraph.
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

PIP=(uv pip)

_uninstall_qt() {
  "${PIP[@]}" uninstall -y \
    pyside6 pyside6-essentials pyside6-addons qdarkstyle shiboken6 pyqtgraph \
    2>/dev/null || true
}

echo "安装 Web 依赖（不含桌面 Qt / PySide6）..."
"${PIP[@]}" install \
  "fastapi>=0.115" \
  "uvicorn[standard]>=0.32" \
  "sqlalchemy>=2.0" \
  "pyjwt>=2.9" \
  "bcrypt>=4.2" \
  "cryptography>=43" \
  "python-multipart>=0.0.12" \
  "httpx>=0.27" \
  "orjson>=3.10" \
  "pymysql>=1.1"

"${PIP[@]}" install \
  "deap>=1.4.2" \
  "loguru>=0.7.3" \
  "nbformat>=5.10.4" \
  "numpy>=2.2.3" \
  "pandas>=2.2.3" \
  "plotly>=6.0.0" \
  "pyzmq>=26.3.0" \
  "tqdm>=4.67.1" \
  "tzlocal>=5.3.1" \
  "ta-lib>=0.6.3"

"${PIP[@]}" install --no-deps "vnpy>=4.0.0,<5"
"${PIP[@]}" install --no-deps -e "${ROOT}"
_uninstall_qt

mkdir -p "${DEPS}"
# Python bindings come from vnpy_ctp 6.7.7.2; Mac CTP dylibs/headers are overlaid
# from SimNow official v6.7.13 (merged production/eval, Create* production mode).
CTP_TAG="6.7.7.2"
if [[ ! -d "${DEPS}/vnpy_ctp/.git" ]]; then
  git clone --depth 1 --branch "${CTP_TAG}" https://github.com/vnpy/vnpy_ctp.git "${DEPS}/vnpy_ctp"
fi

bash "${ROOT}/scripts/load_simnow_ctp.sh"

uv pip install "${DEPS}/vnpy_ctp"
_uninstall_qt

echo "依赖已就绪（SimNow Mac CTP v6.7.13 + vnpy_ctp）。产品入口是 Web：./start.sh"
echo "本仓库不安装 PySide6；默认入口是 Web，不是桌面 Qt。"
