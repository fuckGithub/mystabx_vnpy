#!/usr/bin/env bash
# 防抖调度：标记 pending，单一后台任务在静默 DEBOUNCE 秒后执行 deploy_ecs.sh。
# 供 Cursor hook 与 watch_deploy_ecs.sh 复用。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY="${ROOT}/scripts/deploy_ecs.sh"
MARKER="${ROOT}/.cache/deploy_ecs.pending"
LOCKDIR="${ROOT}/.cache/deploy_ecs.lock"
LOG="${ROOT}/.cache/deploy_ecs.log"
DEBOUNCE_SEC="${DEPLOY_ECS_DEBOUNCE:-45}"
# 默认跑远端 npm run build（rsync 已排除 dist/，否则源码加宽等前端改动不会进静态资源）。
# 仅同步后端、跳过构建：DEPLOY_ECS_ARGS='--no-build' ./scripts/schedule_deploy_ecs.sh
DEPLOY_ARGS=()
if [[ -n "${DEPLOY_ECS_ARGS+x}" ]]; then
  # shellcheck disable=SC2206
  DEPLOY_ARGS=(${DEPLOY_ECS_ARGS})
fi
REASON="${1:-schedule}"

mkdir -p "${ROOT}/.cache"

if [[ ! -x "${DEPLOY}" ]]; then
  echo "缺少可执行 ${DEPLOY}" >&2
  exit 1
fi

touch "${MARKER}"
if mkdir "${LOCKDIR}" 2>/dev/null; then
  (
    trap 'rmdir "${LOCKDIR}" 2>/dev/null || true' EXIT
    while true; do
      rm -f "${MARKER}"
      sleep "${DEBOUNCE_SEC}"
      if [[ -f "${MARKER}" ]]; then
        continue
      fi
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${REASON}: 防抖 ${DEBOUNCE_SEC}s 结束，开始部署 (${DEPLOY_ARGS[*]:-})" >>"${LOG}"
      if ! "${DEPLOY}" "${DEPLOY_ARGS[@]}" >>"${LOG}" 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${REASON}: 部署失败（见 ${LOG}）" >>"${LOG}"
      fi
      if [[ -f "${MARKER}" ]]; then
        continue
      fi
      break
    done
  ) >/dev/null 2>&1 &
fi
