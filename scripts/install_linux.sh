#!/usr/bin/env bash
# Install mystabx + vnpy_ctp on Linux via wheels (no silent sdist compile).
# Prefer: uv pip / apt. Do NOT compile ClickHouse from source.
# Web-only: never install PySide6 / qdarkstyle / pyqtgraph / shiboken6.
# vnpy_ctp: PyPI ships Windows wheels only (no manylinux). Order:
#   1) local wheels/vnpy_ctp-*.whl
#   2) PyPI --only-binary=:all:
#   3) sdist/git compile ONLY if STABX_CTP_FROM_SOURCE=1
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "scripts/install_linux.sh 仅用于 Linux。macOS 请运行 ./scripts/install_macos.sh" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
DEPS="${ROOT}/.deps"
ARCH="$(uname -m)"
export UV_LOCK_TIMEOUT="${UV_LOCK_TIMEOUT:-600}"
export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"
# Keep C++/ninja builds single-threaded on small ECS (avoids OOM / SIGTERM).
export MAX_JOBS="${MAX_JOBS:-1}"
export NINJAFLAGS="${NINJAFLAGS:--j${MAX_JOBS}}"

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

_need_cmd python3 "Ubuntu/Debian: sudo apt-get install -y python3 python3-venv python3-dev"

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  _die "需要 Python ≥ 3.10（pyproject.toml）。当前: $(python3 --version 2>&1)"
fi

if [[ ! -x "${PY}" ]]; then
  echo "未找到 ${PY}，正在创建虚拟环境 ..."
  if command -v uv >/dev/null 2>&1; then
    uv venv "${ROOT}/.venv" --python 3.12 || uv venv "${ROOT}/.venv"
  else
    python3 -m venv "${ROOT}/.venv"
  fi
fi
if [[ ! -x "${PY}" ]]; then
  _die "无法创建虚拟环境：${PY}。请安装 python3-venv / uv 后重试。"
fi

# Clear stale uv lock files only (do NOT pkill uv — that aborts in-flight compiles).
rm -f /tmp/uv-*.lock 2>/dev/null || true
find /tmp -maxdepth 1 -name 'uv-*.lock' -delete 2>/dev/null || true
if command -v uv >/dev/null 2>&1; then
  UV_CACHE="$(uv cache dir 2>/dev/null || true)"
  if [[ -n "${UV_CACHE}" && -d "${UV_CACHE}" ]]; then
    find "${UV_CACHE}" -name '*.lock' -delete 2>/dev/null || true
  fi
fi

# Optional system TA-Lib (apt).
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

_uninstall_qt() {
  echo "卸载桌面 Qt 相关包（若存在）..."
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

echo "安装 vnpy 非 Qt 运行时依赖（wheels）..."
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
  "requests>=2.32" \
  "qrcode>=7.4.2" \
  "Pillow>=10" \
  "chinese-calendar" \
  "tzdata"

echo "安装 ta-lib（优先 wheel；需系统 libta-lib）..."
if ! "${PIP[@]}" install "ta-lib>=0.6.3"; then
  echo "警告: ta-lib 安装失败。可先 apt 安装 libta-lib0 / ta-lib 头文件后再重试。" >&2
fi

echo "安装 vnpy（--no-deps，避免拉入 PySide6）..."
"${PIP[@]}" install --no-deps "vnpy>=4.0.0,<5"

echo "安装本仓库（editable，--no-deps）..."
"${PIP[@]}" install --no-deps -e "${ROOT}"

_uninstall_qt

CTP_TAG="6.7.7.2"
mkdir -p "${ROOT}/wheels"
CTP_WHEEL=""
if compgen -G "${ROOT}/wheels/vnpy_ctp-${CTP_TAG}-*.whl" >/dev/null 2>&1; then
  # shellcheck disable=SC2012
  CTP_WHEEL="$(ls -1t "${ROOT}/wheels"/vnpy_ctp-${CTP_TAG}-*.whl | head -1)"
elif compgen -G "${ROOT}/wheels/vnpy_ctp-*.whl" >/dev/null 2>&1; then
  # shellcheck disable=SC2012
  CTP_WHEEL="$(ls -1t "${ROOT}/wheels"/vnpy_ctp-*.whl | head -1)"
fi

if [[ -n "${CTP_WHEEL}" ]]; then
  echo "安装本地 vnpy_ctp wheel：${CTP_WHEEL}"
  "${PIP[@]}" install --no-deps "${CTP_WHEEL}"
  echo "vnpy_ctp 已从本地 wheel 安装。"
elif "${PIP[@]}" install --no-deps --only-binary=:all: "vnpy_ctp==${CTP_TAG}"; then
  echo "vnpy_ctp 已通过 PyPI binary wheel 安装。"
elif [[ "${STABX_CTP_FROM_SOURCE:-0}" == "1" ]]; then
  echo "无可用 wheel；STABX_CTP_FROM_SOURCE=1，允许 sdist/git 编译（MAX_JOBS=${MAX_JOBS}）..." >&2
  _need_cmd g++ "编译 vnpy_ctp 需要 GCC。Ubuntu/Debian: sudo apt-get install -y build-essential"
  if "${PIP[@]}" install --no-deps "vnpy_ctp==${CTP_TAG}"; then
    echo "vnpy_ctp 已从 PyPI sdist 编译安装。"
  else
    _need_cmd git "Ubuntu/Debian: sudo apt-get install -y git"
    mkdir -p "${DEPS}"
    if [[ ! -d "${DEPS}/vnpy_ctp/.git" ]]; then
      git clone --depth 1 --branch "${CTP_TAG}" https://github.com/vnpy/vnpy_ctp.git "${DEPS}/vnpy_ctp"
    fi
    bash "${ROOT}/scripts/load_simnow_ctp.sh"
    "${PIP[@]}" install --no-deps "${DEPS}/vnpy_ctp"
    echo "vnpy_ctp 已从 git 源码安装。"
  fi
else
  _die "无 vnpy_ctp Linux wheel（PyPI 仅有 Windows wheel）。请把预构建 .whl 放到 ${ROOT}/wheels/ 后重跑，或显式设置 STABX_CTP_FROM_SOURCE=1 允许编译。"
fi

if [[ -x "${ROOT}/scripts/load_simnow_ctp.sh" ]]; then
  if [[ -d "${ROOT}/vendor/simnow-ctp/linux" ]] && compgen -G "${ROOT}/vendor/simnow-ctp/linux/*thost*.so" >/dev/null 2>&1; then
    API_DST="$("${PY}" -c 'import vnpy_ctp, pathlib; print(pathlib.Path(vnpy_ctp.__file__).resolve().parent / "api")')"
    echo "覆盖已安装 vnpy_ctp 的 Linux .so ← vendor/simnow-ctp/linux"
    cp -f "${ROOT}/vendor/simnow-ctp/linux/"*thost*.so "${API_DST}/" 2>/dev/null || true
  fi
fi

_uninstall_qt
if "${PY}" -c "import importlib.util as u; raise SystemExit(0 if u.find_spec('PySide6') else 1)" 2>/dev/null; then
  _die "PySide6 仍在环境中；请检查是否有其它包强制安装了桌面 Qt。"
fi
echo "已确认：未安装 PySide6（Web-only）。"

echo "依赖已就绪。产品入口是 Web：./start.sh"
echo "不要把 Mac 的 .framework 或本机编译产物拷到服务器。"
echo "ClickHouse 请用官方 apt/deb，禁止源码编译。"
