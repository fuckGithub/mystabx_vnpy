#!/usr/bin/env bash
# 监视本地代码改动，防抖后调用 scripts/deploy_ecs.sh。
# 优先 fswatch，其次 entr，否则轮询 mtime。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEBOUNCE_SEC="${DEPLOY_ECS_DEBOUNCE:-45}"
SCHEDULE="${ROOT}/scripts/schedule_deploy_ecs.sh"
LOG="${ROOT}/.cache/deploy_ecs.log"

WATCH_PATHS=(
  "${ROOT}/core"
  "${ROOT}/features"
  "${ROOT}/ui"
  "${ROOT}/start.sh"
  "${ROOT}/main.py"
  "${ROOT}/pyproject.toml"
  "${ROOT}/package.json"
  "${ROOT}/vite.config.ts"
  "${ROOT}/scripts/mystabx-vnpy.service"
)

mkdir -p "${ROOT}/.cache"

if [[ ! -x "${SCHEDULE}" ]]; then
  echo "缺少可执行 ${SCHEDULE}" >&2
  exit 1
fi

echo "监视路径（改动后 ${DEBOUNCE_SEC}s 防抖再部署）："
printf '  %s\n' "${WATCH_PATHS[@]}"
echo "日志: ${LOG}"
echo "手动部署: ${ROOT}/scripts/deploy_ecs.sh"
echo "停止监视: Ctrl+C"

if command -v fswatch >/dev/null 2>&1; then
  echo "使用 fswatch"
  fswatch -o "${WATCH_PATHS[@]}" | while read -r _; do
    "${SCHEDULE}" watch
  done
  exit 0
fi

if command -v entr >/dev/null 2>&1; then
  echo "使用 entr"
  # shellcheck disable=SC2086
  find "${WATCH_PATHS[@]}" \( -type f -o -type l \) \
    ! -path '*/node_modules/*' ! -path '*/__pycache__/*' ! -path '*/dist/*' \
    2>/dev/null | entr -n "${SCHEDULE}" watch
  exit 0
fi

echo "未找到 fswatch/entr，改用 5s 轮询 mtime（可 brew install fswatch）"
_stamp() {
  find "${WATCH_PATHS[@]}" \( -type f -o -type l \) \
    ! -path '*/node_modules/*' ! -path '*/__pycache__/*' ! -path '*/dist/*' \
    -print0 2>/dev/null \
    | xargs -0 stat -f '%m' 2>/dev/null \
    | sort -n \
    | tail -1
}

last="$(_stamp || echo 0)"
while true; do
  sleep 5
  now="$(_stamp || echo 0)"
  if [[ -n "${now}" && "${now}" != "${last}" ]]; then
    last="${now}"
    "${SCHEDULE}" watch
  fi
done
