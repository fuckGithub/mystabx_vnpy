#!/usr/bin/env bash
# Install vnpy extras and compile vnpy_ctp from source on Linux (not editable).
# Uses Linux CTP .so — never Mac .framework / Darwin patches.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "scripts/install_linux.sh 仅用于 Linux。macOS 请运行 ./scripts/install_macos.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
DEPS="${ROOT}/.deps"
ARCH="$(uname -m)"

_die() {
  echo "$1" >&2
  exit 1
}

_need_cmd() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    _die "缺少 ${cmd}。${hint}"
  fi
}

if [[ "${ARCH}" != "x86_64" && "${ARCH}" != "amd64" ]]; then
  _die "官方 CTP Linux 动态库仅支持 x86_64，当前是 ${ARCH}。不要拷贝 Mac .framework。"
fi

_need_cmd git "Ubuntu/Debian: sudo apt-get install -y git"
_need_cmd python3 "Ubuntu/Debian: sudo apt-get install -y python3 python3-venv python3-dev"
_need_cmd g++ "编译 vnpy_ctp 需要 GCC。Ubuntu/Debian: sudo apt-get install -y build-essential"

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  _die "需要 Python ≥ 3.10（pyproject.toml）。当前: $(python3 --version 2>&1)"
fi

if [[ ! -x "${PY}" ]]; then
  echo "未找到 ${PY}，正在创建虚拟环境 ..."
  python3 -m venv "${ROOT}/.venv"
fi
if [[ ! -x "${PY}" ]]; then
  _die "无法创建虚拟环境：${PY}。请安装 python3-venv 后重试。"
fi

# Linux 常见 TA-Lib 路径；不要假设 Homebrew。
if [[ -z "${TA_INCLUDE_PATH:-}" ]]; then
  for cand in /usr/include /usr/local/include; do
    if [[ -f "${cand}/ta-lib/ta_libc.h" ]]; then
      export TA_INCLUDE_PATH="${cand}"
      break
    fi
  done
fi
if [[ -z "${TA_LIBRARY_PATH:-}" ]]; then
  for cand in /usr/lib /usr/lib64 /usr/local/lib /usr/lib/x86_64-linux-gnu; do
    if [[ -f "${cand}/libta_lib.so" || -f "${cand}/libta-lib.so" ]]; then
      export TA_LIBRARY_PATH="${cand}"
      break
    fi
  done
fi

PIP=()
if command -v uv >/dev/null 2>&1; then
  PIP=(uv pip)
elif [[ -x "${ROOT}/.venv/bin/uv" ]]; then
  PIP=("${ROOT}/.venv/bin/uv" pip)
else
  PIP=("${PY}" -m pip)
  "${PY}" -m pip install -U pip
fi

"${PIP[@]}" install -e "${ROOT}"

mkdir -p "${DEPS}"
# Python 封装用 vnpy_ctp 6.7.7.2；Linux 用其自带 .so，或覆盖 vendor/simnow-ctp/linux。
CTP_TAG="6.7.7.2"
if [[ ! -d "${DEPS}/vnpy_ctp/.git" ]]; then
  git clone --depth 1 --branch "${CTP_TAG}" https://github.com/vnpy/vnpy_ctp.git "${DEPS}/vnpy_ctp"
fi

bash "${ROOT}/scripts/load_simnow_ctp.sh"

"${PIP[@]}" install "${DEPS}/vnpy_ctp"

echo "依赖已就绪（Linux CTP .so + vnpy_ctp）。产品入口是 Web：./start.sh"
echo "不要把 Mac 的 .framework 或本机编译产物拷到服务器。"
