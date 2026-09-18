#!/usr/bin/env bash
# 在 ECS 上安装/刷新 Nginx：公网 80 → 本机 18080（mystabx.com）。
# 凭据来自仓库根 .env.ecs（ECS_HOST / ECS_USER / ECS_PASSWORD）。
# 注意：仍须在阿里云安全组放行 TCP 80，否则公网访问会超时。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env.ecs"
CONF_SRC="${ROOT}/scripts/nginx-mystabx.conf"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 ${ENV_FILE}" >&2
  exit 1
fi
if [[ ! -f "${CONF_SRC}" ]]; then
  echo "缺少 ${CONF_SRC}" >&2
  exit 1
fi
if ! command -v sshpass >/dev/null 2>&1; then
  echo "需要 sshpass" >&2
  exit 1
fi

_env_get() {
  local key="$1"
  ECS_ENV_FILE="${ENV_FILE}" KEY="$key" python3 -c '
import os
from pathlib import Path
env = {}
for line in Path(os.environ["ECS_ENV_FILE"]).read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'\''":
        v = v[1:-1]
    env[k.strip()] = v
print(env.get(os.environ["KEY"], ""), end="")
'
}

HOST="$(_env_get ECS_HOST)"
USER="$(_env_get ECS_USER)"
PASS="$(_env_get ECS_PASSWORD)"
USER="${USER:-root}"
if [[ -z "${HOST}" || -z "${PASS}" ]]; then
  echo "ECS_HOST / ECS_PASSWORD 未配置" >&2
  exit 1
fi

export SSHPASS="${PASS}"
SSH=(sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 "${USER}@${HOST}")
SCP=(sshpass -e scp -o StrictHostKeyChecking=accept-new)

echo "==> 上传 nginx 配置到 ${HOST}"
"${SCP[@]}" "${CONF_SRC}" "${USER}@${HOST}:/tmp/nginx-mystabx.conf"

echo "==> 安装并启用 Nginx"
"${SSH[@]}" bash -s <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
if ! command -v nginx >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq nginx
fi
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
install -m 0644 /tmp/nginx-mystabx.conf /etc/nginx/sites-available/mystabx
rm -f /etc/nginx/sites-enabled/default
ln -sfn /etc/nginx/sites-available/mystabx /etc/nginx/sites-enabled/mystabx
nginx -t
systemctl enable nginx
systemctl restart nginx
systemctl is-active nginx
ss -lntp | grep -E ':80\s' || true
curl -sS -o /dev/null -w 'local80_health:%{http_code}\n' -H 'Host: mystabx.com' http://127.0.0.1/health
REMOTE

echo
echo "本机反代已就绪。请在阿里云控制台为该 ECS 安全组添加入站规则："
echo "  协议 TCP，端口 80，授权对象 0.0.0.0/0（或你的办公网段）"
echo "放行后验证："
echo "  curl -I http://mystabx.com/"
echo "  curl -s http://mystabx.com/health"
