#!/usr/bin/env bash
# 将本机代码同步到 ECS，并重启 Web 应用（先停后启，端口 18080）。
# 凭据仅从仓库根目录 .env.ecs 读取（已 gitignore）；勿 source（密码可能含 # &）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env.ecs"
REMOTE_DIR_DEFAULT="/stabx/mystabx_vnpy"
PORT_DEFAULT="18080"
LOG_DIR="${ROOT}/.cache"
LOG_FILE="${LOG_DIR}/deploy_ecs.log"

mkdir -p "${LOG_DIR}"

_usage() {
  cat <<'EOF'
用法: ./scripts/deploy_ecs.sh [--dry-run] [--no-build] [--wait-ready SECS]

  从 .env.ecs 读取 ECS_HOST / ECS_USER / ECS_PASSWORD（及可选 ECS_REMOTE_DIR、STABX_PORT）
  rsync 到远端后：先 stop 旧进程，再 start（systemd 优先，否则 ./start.sh）

  --dry-run      只打印将执行的动作，不传文件、不重启
  --no-build     远端跳过 npm run build（依赖已有 dist/；对应 start.sh --skip-build）
  --wait-ready N 若远端 .venv 暂不可用，最多等待 N 秒（默认 60；不重装依赖）
EOF
}

DRY_RUN=0
DO_BUILD=1
WAIT_READY=60

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      _usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-build)
      DO_BUILD=0
      shift
      ;;
    --wait-ready)
      WAIT_READY="${2:?--wait-ready 需要秒数}"
      shift 2
      ;;
    *)
      echo "未知参数: $1" >&2
      _usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 ${ENV_FILE}。请复制 .env.ecs.example 并填写 ECS_* 后重试。" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "需要 rsync" >&2
  exit 1
fi
if ! command -v sshpass >/dev/null 2>&1; then
  echo "需要 sshpass（macOS: brew install sshpass / hudochenkov/sshpass/sshpass）" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "需要 python3（用于安全解析 .env.ecs）" >&2
  exit 1
fi

# 安全解析 KEY=VALUE：整行值保留（含 # & 空格）；仅去掉首尾成对引号。不 source。
_env_get() {
  local key="$1"
  ECS_ENV_FILE="${ENV_FILE}" python3 -c '
import os, re, sys
key = sys.argv[1]
path = os.environ["ECS_ENV_FILE"]
with open(path, "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if not m or m.group(1) != key:
            continue
        val = m.group(2)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'\''":
            val = val[1:-1]
        sys.stdout.write(val)
        break
' "${key}"
}

ECS_HOST="$(_env_get ECS_HOST)"
ECS_USER="$(_env_get ECS_USER)"
ECS_PASSWORD="$(_env_get ECS_PASSWORD)"
REMOTE_DIR="$(_env_get ECS_REMOTE_DIR)"
REMOTE_PORT="$(_env_get STABX_PORT)"

ECS_HOST="${ECS_HOST:-47.102.208.231}"
ECS_USER="${ECS_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-${REMOTE_DIR_DEFAULT}}"
REMOTE_PORT="${REMOTE_PORT:-${PORT_DEFAULT}}"

if [[ -z "${ECS_PASSWORD}" ]]; then
  echo "ECS_PASSWORD 为空：请在 .env.ecs 填写（勿提交该文件）。" >&2
  exit 1
fi

export SSHPASS="${ECS_PASSWORD}"
SSH_BASE=(sshpass -e ssh
  -o StrictHostKeyChecking=accept-new
  -o PreferredAuthentications=password
  -o PubkeyAuthentication=no
  -o ConnectTimeout=15
  "${ECS_USER}@${ECS_HOST}"
)
RSYNC_RSH="sshpass -e ssh -o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ConnectTimeout=15"

_log() {
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "[${ts}] $*" | tee -a "${LOG_FILE}"
}

_log "部署开始 → ${ECS_USER}@${ECS_HOST}:${REMOTE_DIR}（端口 ${REMOTE_PORT}）"

if [[ "${DRY_RUN}" == "1" ]]; then
  _log "[dry-run] 将 rsync 排除 .venv/node_modules/.git/.env/.env.ecs 等，并远端 stop→start"
  exit 0
fi

_log "确保远端目录存在"
"${SSH_BASE[@]}" "mkdir -p '${REMOTE_DIR}'"

_log "rsync 同步代码（保留远端 .env，不覆盖密钥）"
# --delete 不会删除被 exclude 的远端文件（未使用 --delete-excluded）
rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'node_modules/' \
  --exclude 'ui/node_modules' \
  --exclude '.env' \
  --exclude '.env.ecs' \
  --exclude '.env.local' \
  --exclude '.cache/' \
  --exclude '__pycache__/' \
  --exclude '*.py[cod]' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.ruff_cache/' \
  --exclude 'docs/ecs-rds.local.md' \
  --exclude 'docs/ecs&rds.md' \
  --exclude '.DS_Store' \
  -e "${RSYNC_RSH}" \
  "${ROOT}/" "${ECS_USER}@${ECS_HOST}:${REMOTE_DIR}/"

_log "远端：停止旧应用 →（可选）构建 → 启动"
# shellcheck disable=SC2029
"${SSH_BASE[@]}" "REMOTE_DIR='${REMOTE_DIR}' REMOTE_PORT='${REMOTE_PORT}' DO_BUILD='${DO_BUILD}' WAIT_READY='${WAIT_READY}' bash -s" <<'REMOTE'
set -euo pipefail

cd "${REMOTE_DIR}" || {
  echo "远端目录 ${REMOTE_DIR} 不存在（安装可能未完成）" >&2
  exit 2
}

_listen_pids() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -H -lptn "sport = :${port}" 2>/dev/null \
      | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' \
      | awk 'NF && !seen[$1]++' || true
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | awk 'NF && !seen[$1]++' || true
    return 0
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "${port}/tcp" 2>/dev/null | tr -s '[:space:]' '\n' | awk '/^[0-9]+$/ && !seen[$1]++' || true
  fi
}

_stop_port_listeners() {
  local port="$1" pid leftover retries
  leftover="$(_listen_pids "${port}")"
  [[ -z "${leftover}" ]] && return 0
  while read -r pid; do
    [[ -z "${pid}" ]] && continue
    echo "停止占用端口 ${port} 的 PID ${pid}"
    kill "${pid}" 2>/dev/null || true
  done <<< "${leftover}"
  retries=20
  while [[ "${retries}" -gt 0 ]]; do
    leftover="$(_listen_pids "${port}")"
    [[ -z "${leftover}" ]] && return 0
    if [[ "${retries}" -le 10 ]]; then
      while read -r pid; do
        [[ -z "${pid}" ]] && continue
        kill -9 "${pid}" 2>/dev/null || true
      done <<< "${leftover}"
    fi
    sleep 0.25
    retries=$((retries - 1))
  done
}

_py() {
  if [[ -x "${REMOTE_DIR}/.venv/bin/python" ]]; then
    echo "${REMOTE_DIR}/.venv/bin/python"
  elif [[ -x "${REMOTE_DIR}/.venv/bin/python3" ]]; then
    echo "${REMOTE_DIR}/.venv/bin/python3"
  else
    return 1
  fi
}

_venv_import_ok() {
  local py
  py="$(_py)" || return 1
  "${py}" -c 'import uvicorn' >/dev/null 2>&1
}

# 仅等待已有 .venv 可用；不在此脚本里 uv sync / pip install / install_linux
elapsed=0
while true; do
  if _venv_import_ok; then
    break
  fi
  if [[ "${elapsed}" -ge "${WAIT_READY}" ]]; then
    echo "远端 .venv 未就绪（${WAIT_READY}s）。代码已同步；请先在服务器完成 ./scripts/install_linux.sh，再 deploy。" >&2
    exit 3
  fi
  if ! _py >/dev/null; then
    echo "尚无可用 .venv，等待中… (${elapsed}/${WAIT_READY}s)"
  else
    echo ".venv 存在但 import uvicorn 失败，等待中… (${elapsed}/${WAIT_READY}s)"
  fi
  sleep 5
  elapsed=$((elapsed + 5))
done
echo "远端 Python 运行时就绪：$(_py)"

has_systemd=0
if command -v systemctl >/dev/null 2>&1; then
  if [[ -f /etc/systemd/system/mystabx-vnpy.service ]] \
    || systemctl cat mystabx-vnpy.service >/dev/null 2>&1; then
    has_systemd=1
  fi
fi

echo "停止旧应用…"
if [[ "${has_systemd}" == "1" ]]; then
  systemctl stop mystabx-vnpy.service 2>/dev/null || systemctl stop mystabx-vnpy 2>/dev/null || true
fi
# 兜底：start.sh / uvicorn / 占用 18080 的残留
pkill -f "${REMOTE_DIR}/start.sh" 2>/dev/null || true
pkill -f "uvicorn core.main:app" 2>/dev/null || true
_stop_port_listeners "${REMOTE_PORT}"

if [[ -f "${REMOTE_DIR}/scripts/mystabx-vnpy.service" ]] && command -v systemctl >/dev/null 2>&1; then
  cp "${REMOTE_DIR}/scripts/mystabx-vnpy.service" /etc/systemd/system/mystabx-vnpy.service
  systemctl daemon-reload
  has_systemd=1
fi

if [[ "${DO_BUILD}" == "1" ]]; then
  if [[ ! -d "${REMOTE_DIR}/node_modules" ]]; then
    echo "远端缺少 node_modules，执行 npm install（仅构建需要）…"
    (cd "${REMOTE_DIR}" && npm install)
  fi
  echo "远端 npm run build…"
  (cd "${REMOTE_DIR}" && npm run build)
else
  echo "跳过远端构建（--no-build；不跑 npm install）"
  if [[ ! -f "${REMOTE_DIR}/dist/index.html" ]]; then
    echo "警告：远端无 dist/index.html，--no-build 启动可能无前端静态页" >&2
  fi
fi

echo "启动应用…"
if [[ "${has_systemd}" == "1" ]]; then
  systemctl enable mystabx-vnpy.service >/dev/null 2>&1 || true
  systemctl start mystabx-vnpy.service
  sleep 2
  systemctl --no-pager -l status mystabx-vnpy.service || true
else
  # 无 systemd 时后台起 start.sh（有 dist 则 --skip-build）
  mkdir -p /var/log
  if [[ -f "${REMOTE_DIR}/dist/index.html" ]]; then
    nohup "${REMOTE_DIR}/start.sh" --skip-build >>/var/log/mystabx-vnpy.log 2>&1 &
  else
    nohup "${REMOTE_DIR}/start.sh" >>/var/log/mystabx-vnpy.log 2>&1 &
  fi
  echo "已 nohup ./start.sh（日志 /var/log/mystabx-vnpy.log）"
fi

# 简单健康探测（不阻断：启动可能仍在 build/warmup）
if command -v curl >/dev/null 2>&1; then
  for i in 1 2 3 4 5 6; do
    if curl -fsS --max-time 2 "http://127.0.0.1:${REMOTE_PORT}/health" >/dev/null 2>&1 \
      || curl -fsS --max-time 2 "http://127.0.0.1:${REMOTE_PORT}/" >/dev/null 2>&1; then
      echo "健康检查通过 http://127.0.0.1:${REMOTE_PORT}/"
      exit 0
    fi
    sleep 5
  done
  echo "警告：启动后暂未通过健康检查（应用可能仍在启动）" >&2
fi
REMOTE

_log "部署完成。公网: http://${ECS_HOST}:${REMOTE_PORT}/"
unset SSHPASS
