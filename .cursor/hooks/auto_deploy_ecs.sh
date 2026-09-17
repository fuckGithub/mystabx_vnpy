#!/usr/bin/env bash
# Cursor afterFileEdit：有意义路径变更后防抖触发 ECS 部署。
# 默认关闭：touch .cache/auto_deploy_ecs.enabled 或 export STABX_AUTO_DEPLOY_ECS=1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCHEDULE="${ROOT}/scripts/schedule_deploy_ecs.sh"
ENABLE_FLAG="${ROOT}/.cache/auto_deploy_ecs.enabled"

mkdir -p "${ROOT}/.cache"

if [[ "${STABX_AUTO_DEPLOY_ECS:-}" != "1" && ! -f "${ENABLE_FLAG}" ]]; then
  exit 0
fi

if [[ ! -x "${SCHEDULE}" ]]; then
  exit 0
fi

input="$(cat || true)"

file_path="$(FILE_JSON="${input}" python3 -c '
import json, os, sys
raw = os.environ.get("FILE_JSON") or ""
if not raw.strip():
    sys.exit(0)
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)
for key in ("file_path", "path", "filePath", "file"):
    v = data.get(key)
    if isinstance(v, str) and v:
        print(v)
        break
else:
    edits = data.get("edits") or data.get("files") or []
    if isinstance(edits, list) and edits:
        first = edits[0]
        if isinstance(first, str):
            print(first)
        elif isinstance(first, dict):
            for key in ("file_path", "path", "filePath", "file"):
                v = first.get(key)
                if isinstance(v, str) and v:
                    print(v)
                    break
' 2>/dev/null || true)"

if [[ -z "${file_path}" ]]; then
  exit 0
fi

rel="${file_path}"
case "${rel}" in
  "${ROOT}"/*) rel="${rel#"${ROOT}"/}" ;;
esac
rel="${rel#./}"

case "${rel}" in
  core/*|features/*|ui/*|start.sh|main.py|pyproject.toml|package.json|package-lock.json|vite.config.ts|scripts/mystabx-vnpy.service)
    ;;
  *)
    exit 0
    ;;
esac

case "${rel}" in
  .cache/*|.env|.env.*|.venv/*|node_modules/*|ui/node_modules/*|dist/*)
    exit 0
    ;;
esac

"${SCHEDULE}" "hook:${rel}" >/dev/null 2>&1 || true
exit 0
