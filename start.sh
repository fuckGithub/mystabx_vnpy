#!/usr/bin/env bash
# Stabx Web 交易台一键启动（Linux / macOS 部署用）。
# 默认生产模式：npm run build 后由单个 uvicorn 托管 REST/WS + Vue dist，无需两个终端。
# 产品入口：./start.sh、uv run start、python main.py（均不启动桌面 Qt）。
# Linux：不假设 Homebrew / Xcode / Mac CTP .framework；不要对 vnpy 使用 --workers。
set -euo pipefail

# CTP C++ requires a valid locale; invalid LANG crashes after connect.
# Prefer zh_CN.utf8 on minimal Linux images (often no zh_CN.UTF-8 alias).
export LANG="${LANG:-zh_CN.utf8}"
export LC_ALL="${LC_ALL:-zh_CN.utf8}"
export LC_CTYPE="${LC_CTYPE:-zh_CN.utf8}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "${ROOT}"

OS="$(uname -s)"
ARCH="$(uname -m)"
case "${OS}" in
  Linux|Darwin) ;;
  *)
    echo "不支持的系统：${OS}（./start.sh 仅 Linux / macOS）。" >&2
    echo "Windows：用 WSL2 + ./scripts/install_linux.sh，或见 docs/CTP分平台搭建.md（install_windows.ps1 + uvicorn）。" >&2
    exit 1
    ;;
esac

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

# Linux：系统/nvm 路径。不要把 Homebrew 加进 Linux PATH。
# systemd 可能未设 HOME；set -u 下必须用默认值。
if [[ "${OS}" == "Linux" ]]; then
  export PATH="/usr/local/bin:/usr/bin:${PATH}"
  export HOME="${HOME:-/root}"
  if [[ -z "${NVM_DIR:-}" && -d "${HOME}/.nvm" ]]; then
    NVM_DIR="${HOME}/.nvm"
  fi
  if [[ -n "${NVM_DIR:-}" && -s "${NVM_DIR}/nvm.sh" ]]; then
    # shellcheck disable=SC1091
    source "${NVM_DIR}/nvm.sh"
  fi
fi

_die() {
  echo "$1" >&2
  exit 1
}

_linux_dep_hint() {
  echo "Ubuntu/Debian 示例：sudo apt-get install -y python3 python3-venv python3-dev build-essential nodejs npm git"
}

resolve_python() {
  local cand
  for cand in "${ROOT}/.venv/bin/python" "${ROOT}/.venv/bin/python3"; do
    if [[ -x "${cand}" ]]; then
      echo "${cand}"
      return 0
    fi
  done
  return 1
}

PY=""
if ! PY="$(resolve_python)"; then
  echo "缺少 Python 虚拟环境：${ROOT}/.venv/bin/python" >&2
  if [[ "${OS}" == "Linux" ]]; then
    echo "请先：python3 -m venv .venv && ./scripts/install_linux.sh" >&2
    _linux_dep_hint >&2
  else
    echo "请先：python3 -m venv .venv && ./scripts/install_macos.sh" >&2
  fi
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  if [[ "${OS}" == "Linux" ]]; then
    _die "缺少 Node.js（未找到 node）。$(_linux_dep_hint)"
  fi
  _die "缺少 Node.js（未找到 node）。请先安装 Node.js 后再运行 ./start.sh"
fi

if ! command -v npm >/dev/null 2>&1; then
  if [[ "${OS}" == "Linux" ]]; then
    _die "缺少 npm（未找到 npm）。$(_linux_dep_hint)"
  fi
  _die "缺少 npm（未找到 npm）。请先安装 Node.js/npm 后再运行 ./start.sh"
fi

if [[ "${OS}" == "Linux" && "${ARCH}" != "x86_64" && "${ARCH}" != "amd64" ]]; then
  echo "警告：官方 CTP Linux 动态库仅支持 x86_64，当前是 ${ARCH}。Web 可启动，但 CTP 网关可能无法加载。" >&2
fi

# Linux 运行时让 vnpy_ctp 能找到同目录 .so（meson 已设 $ORIGIN，这里再兜一层）。
if [[ "${OS}" == "Linux" ]]; then
  CTP_API_DIR="$("${PY}" -c 'import vnpy_ctp, pathlib; print(pathlib.Path(vnpy_ctp.__file__).resolve().parent / "api")' 2>/dev/null || true)"
  if [[ -n "${CTP_API_DIR}" && -d "${CTP_API_DIR}" ]]; then
    if [[ -d "${CTP_API_DIR}/thostmduserapi_se.framework" && ! -f "${CTP_API_DIR}/libthostmduserapi_se.so" ]]; then
      _die "当前 vnpy_ctp 只有 Mac .framework，没有 Linux .so。请在本机运行 ./scripts/install_linux.sh，不要拷贝 Mac 编译产物。"
    fi
    export LD_LIBRARY_PATH="${CTP_API_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
  fi
fi

HOST="${STABX_HOST:-0.0.0.0}"
PORT="${STABX_PORT:-18080}"
MODE="prod"
SKIP_BUILD="${STABX_SKIP_BUILD:-0}"

for arg in "$@"; do
  case "${arg}" in
    --dev|dev)
      MODE="dev"
      ;;
    --skip-build)
      SKIP_BUILD=1
      ;;
    -h|--help)
      cat <<'EOF'
用法: ./start.sh [--dev] [--skip-build]
      uv run start [--dev] [--skip-build]
      python main.py [--dev] [--skip-build]

  （默认）生产模式：构建 Vue，再由 uvicorn 单进程托管 API + SPA
  --dev         本机热更新：同一脚本内启动 uvicorn --reload 与 Vite
  --skip-build  生产模式跳过构建（要求 dist/index.html 已存在）

平台：
  macOS   本机开发可用 --dev；CTP 用 ./scripts/install_macos.sh
  Linux   服务器默认走生产模式（build + uvicorn）；CTP 用 ./scripts/install_linux.sh
          不要使用 Mac .framework / Homebrew / Xcode 路径

环境变量见仓库根目录 .env.example。
不要把真实 SimNow 密码写入仓库。
不要对 vnpy 引擎使用 uvicorn --workers（MainEngine 在进程内）。
EOF
      exit 0
      ;;
    *)
      echo "未知参数: ${arg}（可用 --dev / --skip-build / --help）" >&2
      exit 1
      ;;
  esac
done

# 仅处理 STABX_PORT 上的 LISTEN 占用，释放后才能绑定。不碰其它端口。
_listen_pids_on_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | awk 'NF && !seen[$1]++' || true
    return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -H -lptn "sport = :${port}" 2>/dev/null \
      | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' \
      | awk 'NF && !seen[$1]++' || true
    return 0
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "${port}/tcp" 2>/dev/null | tr -s '[:space:]' '\n' | awk '/^[0-9]+$/ && !seen[$1]++' || true
    return 0
  fi
}

_pid_command() {
  local pid="$1"
  ps -p "${pid}" -o args= 2>/dev/null || ps -p "${pid}" -o command= 2>/dev/null || echo "(unknown)"
}

_skip_own_pid() {
  local pid="$1"
  [[ "${pid}" == "1" || "${pid}" == "$$" || "${pid}" == "${PPID}" ]]
}

_dump_listen_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >&2 || true
  elif command -v ss >/dev/null 2>&1; then
    ss -lptn "sport = :${port}" >&2 || true
  else
    echo "（未安装 lsof/ss，无法列出占用进程）" >&2
  fi
}

free_stabx_listen_port() {
  local port="$1"
  local pid cmd leftover retries

  if ! command -v lsof >/dev/null 2>&1 && ! command -v ss >/dev/null 2>&1 && ! command -v fuser >/dev/null 2>&1; then
    echo "未找到 lsof/ss/fuser，跳过端口 ${port} 占用检查" >&2
    return 0
  fi

  leftover="$(_listen_pids_on_port "${port}")"
  if [[ -z "${leftover}" ]]; then
    return 0
  fi

  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    if _skip_own_pid "${pid}"; then
      continue
    fi
    cmd="$(_pid_command "${pid}")"
    echo "端口 ${port} 已被占用：PID ${pid}  ${cmd}"
    if echo "${cmd}" | grep -Eqi 'uvicorn|python[[:space:]].*core\.main:app|[[:space:]]start\.sh([[:space:]]|$)'; then
      echo "正在停止本项目先前的服务进程 ${pid} ..."
    else
      echo "占用者不是 uvicorn/python，但仍将释放 STABX_PORT=${port} 上的监听进程 ${pid}"
    fi
    kill "${pid}" 2>/dev/null || true
  done <<< "${leftover}"

  retries=20
  while [[ "${retries}" -gt 0 ]]; do
    leftover="$(_listen_pids_on_port "${port}")"
    if [[ -z "${leftover}" ]]; then
      echo "端口 ${port} 已释放，继续启动"
      return 0
    fi
    if [[ "${retries}" -le 10 ]]; then
      while read -r pid; do
        [[ -z "${pid}" ]] && continue
        if _skip_own_pid "${pid}"; then
          continue
        fi
        echo "进程 ${pid} 仍占用端口 ${port}，发送 SIGKILL"
        kill -9 "${pid}" 2>/dev/null || true
      done <<< "${leftover}"
    fi
    sleep 0.25
    retries=$((retries - 1))
  done

  echo "端口 ${port} 仍被占用，无法启动：" >&2
  _dump_listen_port "${port}"
  exit 1
}

probe_clickhouse() {
  local url host port db ping
  url="${STABX_CLICKHOUSE_URL:-http://${STABX_CLICKHOUSE_HOST:-127.0.0.1}:${STABX_CLICKHOUSE_PORT:-8123}}"
  url="${url%/}"
  host="${STABX_CLICKHOUSE_HOST:-}"
  port="${STABX_CLICKHOUSE_PORT:-}"
  db="${STABX_CLICKHOUSE_DATABASE:-mystabx_vnpy}"
  if [[ -z "${host}" || -z "${port}" ]]; then
    host="${url#*://}"
    host="${host%%/*}"
    if [[ "${host}" == *:* ]]; then
      port="${host##*:}"
      host="${host%%:*}"
    else
      port="8123"
    fi
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "ClickHouse 未探测 ${host}:${port} database=${db}（未找到 curl，启动后由 FastAPI lifespan 再查）"
    return 0
  fi
  ping="$(curl -fsS --max-time 2 "${url}/ping" 2>/dev/null || true)"
  if [[ "${ping}" == Ok* ]]; then
    echo "ClickHouse 可达 ${host}:${port} database=${db}"
    return 0
  fi
  echo "ClickHouse 不可达 ${host}:${port} database=${db}（不阻止启动，今日分时走内存）"
  return 0
}

ensure_node_modules() {
  if [[ ! -d "${ROOT}/node_modules" ]]; then
    echo "未找到 node_modules，正在 npm install ..."
    npm install
  fi
  # Vite root 是 ui/，IDE 会在该目录找 vite；依赖实际装在仓库根。
  if [[ ! -e "${ROOT}/ui/node_modules" ]]; then
    ln -s ../node_modules "${ROOT}/ui/node_modules"
  fi
}

if [[ "${MODE}" == "dev" ]]; then
  ensure_node_modules
  echo "开发模式（${OS}）：API http://${HOST}:${PORT} ；前端 Vite 默认 http://127.0.0.1:5173"
  UVICORN_PID=""
  VITE_PID=""
  cleanup() {
    if [[ -n "${UVICORN_PID}" ]]; then
      kill "${UVICORN_PID}" 2>/dev/null || true
    fi
    if [[ -n "${VITE_PID}" ]]; then
      kill "${VITE_PID}" 2>/dev/null || true
    fi
  }
  trap cleanup EXIT INT TERM
  probe_clickhouse
  free_stabx_listen_port "${PORT}"
  "${PY}" -m uvicorn core.main:app --reload --host "${HOST}" --port "${PORT}" &
  UVICORN_PID=$!
  npm run dev &
  VITE_PID=$!
  while kill -0 "${UVICORN_PID}" 2>/dev/null && kill -0 "${VITE_PID}" 2>/dev/null; do
    sleep 1
  done
  cleanup
  trap - EXIT INT TERM
  wait || true
  echo "开发进程已退出" >&2
  exit 1
fi

ensure_node_modules
if [[ "${SKIP_BUILD}" == "1" ]]; then
  if [[ ! -f "${ROOT}/dist/index.html" ]]; then
    echo "已设置跳过构建，但缺少 dist/index.html。请先 npm run build 或去掉 --skip-build" >&2
    exit 1
  fi
  echo "跳过前端构建（已有 dist/）"
else
  echo "正在构建 Vue（npm run build）..."
  npm run build
fi

if [[ ! -f "${ROOT}/dist/index.html" ]]; then
  echo "构建后仍缺少 dist/index.html" >&2
  exit 1
fi

echo "生产模式（${OS}）：单进程托管 API + SPA  →  http://${HOST}:${PORT}"
echo "提示：不要使用 uvicorn --workers，vnpy MainEngine 必须单进程。"
probe_clickhouse
free_stabx_listen_port "${PORT}"
exec "${PY}" -m uvicorn core.main:app --host "${HOST}" --port "${PORT}"
