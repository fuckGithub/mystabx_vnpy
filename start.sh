#!/usr/bin/env bash
# Stabx Web 交易台一键启动（Linux / macOS 部署用）。
# 默认生产模式：npm run build 后由单个 uvicorn 托管 REST/WS + Vue dist，无需两个终端。
# 桌面 Qt / main.py 不是产品入口，本脚本不会启动 GUI。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "${ROOT}"

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  echo "缺少 Python 虚拟环境：${PY}" >&2
  echo "请先创建并安装依赖，例如：python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "缺少 Node.js（未找到 node）。请先安装 Node.js 后再运行 ./start.sh" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "缺少 npm（未找到 npm）。请先安装 Node.js/npm 后再运行 ./start.sh" >&2
  exit 1
fi

HOST="${STABX_HOST:-0.0.0.0}"
PORT="${STABX_PORT:-8000}"
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

  （默认）生产模式：构建 Vue，再由 uvicorn 单进程托管 API + SPA
  --dev         本机热更新：同一脚本内启动 uvicorn --reload 与 Vite
  --skip-build  生产模式跳过构建（要求 dist/index.html 已存在）

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
  echo "开发模式：API http://${HOST}:${PORT} ；前端 Vite 默认 http://127.0.0.1:5173"
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

echo "生产模式：单进程托管 API + SPA  →  http://${HOST}:${PORT}"
echo "提示：不要使用 uvicorn --workers，vnpy MainEngine 必须单进程。"
exec "${PY}" -m uvicorn core.main:app --host "${HOST}" --port "${PORT}"
