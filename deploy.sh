#!/bin/bash
# ============================================
# 一键部署 & 管理工具（两种运行方式，自动探测）
#
#  方式 A 全套 Docker（在仓库内执行）
#    bash deploy.sh                 完整部署（环境检查→构建→证书→启动）
#    bash deploy.sh start           启动全部服务
#    bash deploy.sh restart:backend 构建镜像并重启后端，输出启动日志
#    bash deploy.sh image:export    构建并导出后端镜像 tar.gz（交给服务器）
#    bash deploy.sh cert:init       签发 SSL 证书
#    bash deploy.sh cert:renew      续签 SSL 证书
#
#  方式 B 只跑后端镜像（在服务器上执行，目录内只有编排文件与配置）
#    bash deploy.sh image:load      加载离线镜像包
#    bash deploy.sh db:migrate      执行数据库迁移
#    bash deploy.sh start [--local-deps]   启动后端容器
#
#  通用：stop / restart / status / logs [服务] / help
# ============================================
set -e

# ==================== 路径与模式探测 ====================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
CERT_DOMAIN="service.xxcdjl.xyz"
CERT_EMAIL="admin@xxcdjl.xyz"

if [ -f "${SCRIPT_DIR}/docker/docker-compose.yaml" ]; then
  MODE="full"
  COMPOSE_DIR="${SCRIPT_DIR}/docker"
  COMPOSE_ARGS=(-f docker-compose.yaml)
  ENV_PROD_FILE="${SCRIPT_DIR}/backend/env/.env.prod"
  ENV_PROD_TEMPLATE="${SCRIPT_DIR}/backend/env/.env.prod.example"
elif [ -f "${SCRIPT_DIR}/docker-compose.backend.yaml" ]; then
  MODE="backend-only"
  COMPOSE_DIR="${SCRIPT_DIR}"
  COMPOSE_ARGS=(-f docker-compose.backend.yaml)
  ENV_PROD_FILE="${SCRIPT_DIR}/env.prod"
  ENV_PROD_TEMPLATE="${SCRIPT_DIR}/env.prod.example"
else
  echo "✗ 未找到编排文件，无法确定运行模式。" >&2
  echo "  方式 A：在仓库根目录执行（需要 docker/docker-compose.yaml）" >&2
  echo "  方式 B：把 deploy.sh 与 docker-compose.backend.yaml 放在同一目录" >&2
  exit 1
fi

SSL_DIR="${COMPOSE_DIR}/nginx/ssl"
IMAGE_TAG_DEFAULT="3.1.0"

# ==================== 辅助函数 ====================

print_banner() {
  echo "========================================="
  echo "   deploy — ${1}（模式：${MODE}）"
  echo "========================================="
}

# 在本模式的编排目录内执行 docker compose
dc() {
  (cd "${COMPOSE_DIR}" && docker compose "${COMPOSE_ARGS[@]}" "$@")
}

check_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "  → Docker 未安装，请先安装: https://docs.docker.com/engine/install/"
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "  → Docker Compose 未安装"
    exit 1
  fi
}

check_env_prod() {
  if [ -f "${ENV_PROD_FILE}" ]; then
    return 0
  fi
  echo "  → ✗ 缺少应用配置文件：${ENV_PROD_FILE}"
  if [ -f "${ENV_PROD_TEMPLATE}" ]; then
    echo "  → 请先执行： cp ${ENV_PROD_TEMPLATE} ${ENV_PROD_FILE}"
  elif [ "${MODE}" = "full" ]; then
    echo "  → 请参照 docker/README.md 创建该文件"
  else
    echo "  → 请把开发机的 backend/env/.env.prod.example scp 过来（改名为 env.prod.example），再 cp 成 env.prod"
  fi
  echo "  → 说明：compose 的 env_file 在文件缺失时会直接报错退出（不会静默使用默认值）"
  exit 1
}

check_compose_env() {
  if [ -f "${COMPOSE_DIR}/.env" ]; then
    return 0
  fi
  echo "  → ✗ 缺少 compose 变量文件：${COMPOSE_DIR}/.env"
  if [ -f "${COMPOSE_DIR}/.env.example" ]; then
    echo "  → 请先执行： cp ${COMPOSE_DIR}/.env.example ${COMPOSE_DIR}/.env"
  fi
  echo "  → 该文件提供 MYSQL_ROOT_PASSWORD 等被 compose 强校验的变量"
  exit 1
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${1}"
  else
    shasum -a 256 "${1}"
  fi
}

ensure_ssl_www() {
  mkdir -p "${SSL_DIR}/www"
}

# ==================== 子命令 ====================

cmd_deploy() {
  if [ "${MODE}" != "full" ]; then
    echo "✗ 完整部署仅适用于方式 A（仓库内执行）。" >&2
    echo "  方式 B 请依次执行： image:load → db:migrate → start" >&2
    exit 1
  fi
  print_banner "完整部署"
  echo "  项目路径: ${PROJECT_DIR}"
  echo ""

  # ---- 1. 配置文件 ----
  echo ""
  echo "[1/5] 检查配置文件..."
  check_env_prod
  check_compose_env
  echo "  → 配置文件已就绪"

  # ---- 2. Docker 环境 ----
  echo ""
  echo "[2/5] 检查 Docker 环境..."
  check_docker
  echo "  → Docker $(docker --version)"
  echo "  → Compose $(docker compose version)"

  # ---- 3. 构建后端镜像 ----
  echo ""
  echo "[3/5] 构建后端 Docker 镜像..."
  (cd "${COMPOSE_DIR}" && docker compose "${COMPOSE_ARGS[@]}" build backend)
  echo "  → 后端镜像构建完成"

  # ---- 4. SSL 证书 ----
  echo ""
  echo "[4/5] 配置 SSL 证书..."
  if [ -f "${SSL_DIR}/live/${CERT_DOMAIN}/fullchain.pem" ]; then
    echo "  → SSL 证书已存在: ${SSL_DIR}/live/${CERT_DOMAIN}/"
  else
    echo "  → 尝试签发证书（域名须已指向本机）..."
    cmd_cert_init || echo "  ⚠ 签发失败，部署后手动执行: bash deploy.sh cert:init"
  fi

  # ---- 5. 启动 ----
  echo ""
  echo "[5/5] 启动所有 Docker 服务..."
  cmd_start
  echo ""
  echo "========================================="
  echo "   部署完成！"
  echo "========================================="
  echo ""
  echo "访问地址:"
  echo "   后端 API:      https://${CERT_DOMAIN}/api/v1"
  echo "   后端 API 文档:  https://${CERT_DOMAIN}/api/v1/docs"
  echo "   管理后台:       https://${CERT_DOMAIN}/web/"
  echo "   小程序 H5:      https://${CERT_DOMAIN}/app/"
  echo "   官网:           https://${CERT_DOMAIN}/"
  echo ""
  echo "日志: bash deploy.sh logs"
}

cmd_start() {
  local option="${1:-}"
  print_banner "启动服务"
  check_docker
  check_env_prod

  if [ "${MODE}" = "full" ]; then
    check_compose_env
    if [ "${option}" = "--local-deps" ]; then
      echo "  → 方式 A 整栈已含 mysql/redis，忽略 --local-deps"
    fi
    echo "  → 检查数据目录..."
    mkdir -p "${COMPOSE_DIR}/mysql/data" "${COMPOSE_DIR}/redis/data"
    echo "  → 数据目录已就绪"
  elif [ "${option}" = "--local-deps" ]; then
    if [ ! -f "${COMPOSE_DIR}/docker-compose.local-deps.yaml" ]; then
      echo "  → ✗ 缺少 docker-compose.local-deps.yaml（--local-deps 需要它）"
      exit 1
    fi
    check_compose_env
    COMPOSE_ARGS=(-f docker-compose.backend.yaml -f docker-compose.local-deps.yaml)
    echo "  → 已叠加本地依赖（mysql + redis）"
  fi

  dc up -d
  echo "  → 服务已启动"
  dc ps 2>/dev/null || true
  echo "  → 日志: bash deploy.sh logs"
}

cmd_stop() {
  print_banner "停止服务"
  check_docker
  dc down
  echo "  → 服务已停止"
}

cmd_restart() {
  print_banner "重启服务"
  cmd_stop
  echo ""
  cmd_start
}

cmd_status() {
  print_banner "服务状态"
  check_docker
  dc ps
}

cmd_logs() {
  check_docker
  local service="${1:-}"
  if [ -n "${service}" ]; then
    dc logs -f "${service}"
  else
    dc logs -f
  fi
}

cmd_restart_backend() {
  print_banner "构建并重启后端服务"
  check_docker
  check_env_prod

  if [ "${MODE}" = "full" ]; then
    echo "  → 构建后端镜像..."
    dc build backend
    echo "  → 后端镜像构建完成"
  else
    echo "  → 方式 B 不构建镜像；更新代码请先在开发机执行 image:export 再 image:load"
  fi

  # ---- 数据库迁移检查 ----
  echo ""
  echo "  → 检查数据库迁移..."
  set +e
  MIGRATE_OUTPUT="$(dc run --rm backend alembic check 2>&1)"
  MIGRATE_EXIT_CODE=$?
  set -e

  if echo "${MIGRATE_OUTPUT}" | grep -q "No new upgrade operations"; then
    echo "  → 数据库已是最新，无需迁移"
  elif [ ${MIGRATE_EXIT_CODE} -eq 0 ] || echo "${MIGRATE_OUTPUT}" | grep -q "New upgrade operations"; then
    echo "  → ⚠ 检测到待应用的数据库迁移"
    echo "${MIGRATE_OUTPUT}" | grep -E "(New upgrade|alembic)" || true
    # read 在 EOF（ssh 无 -t / cron / < /dev/null）会返回 1，`set -e` 下会**静默中止**，
    # 且中止点在下面的 dc restart backend 之前 —— operator 会以为重启成功。
    if [ -t 0 ]; then
      read -p "  → 是否执行数据库迁移 (alembic upgrade head)? [y/N] " DO_MIGRATE || DO_MIGRATE="n"
    else
      echo "  → 非交互环境，默认跳过迁移（如需迁移请显式执行 bash deploy.sh db:migrate）"
      DO_MIGRATE="n"
    fi
    if [[ "${DO_MIGRATE}" =~ ^[Yy] ]]; then
      echo "  → 执行数据库迁移..."
      dc run --rm backend alembic upgrade head
      echo "  → 数据库迁移完成"
    else
      echo "  → 跳过数据库迁移"
    fi
  else
    echo "  → 迁移检查结果:"
    echo "${MIGRATE_OUTPUT}"
  fi

  echo ""
  echo "  → 重启 backend 容器..."
  dc restart backend
  echo ""
  echo "  → 启动日志（等待 5 秒）..."
  sleep 5
  dc logs --tail=50 backend
}

cmd_image_export() {
  if [ "${MODE}" != "full" ]; then
    echo "✗ image:export 需在仓库内执行（方式 A）。" >&2
    exit 1
  fi
  print_banner "导出后端镜像"
  check_docker
  check_compose_env

  local tag="${1:-${IMAGE_TAG_DEFAULT}}"
  local image="fastapiadmin-backend:${tag}"
  local dist="${COMPOSE_DIR}/dist"
  local tar_file="${dist}/backend-${tag}.tar.gz"

  echo "  → 构建镜像 ${image} ..."
  (cd "${COMPOSE_DIR}" && IMAGE_TAG="${tag}" docker compose "${COMPOSE_ARGS[@]}" build backend)

  echo "  → 校验镜像架构（服务器需 linux/amd64）..."
  local arch
  arch="$(docker image inspect --format '{{.Architecture}}' "${image}" 2>/dev/null || echo unknown)"
  if [ "${arch}" != "amd64" ]; then
    echo "  → ⚠ 镜像架构为 ${arch}，服务器为 linux/amd64 时无法运行"
    echo "  → 请确认编排里 backend 的 platform: linux/amd64 已生效后再导出"
  fi

  mkdir -p "${dist}"
  echo "  → 导出 ${tar_file} ..."
  # 不用 `docker save | gzip > file`：管道退出码取最后一个命令，docker save 失败会被吞，
  # 结果是一个合法的、约 20 字节的空 gzip，随后 sha256 还会给它“背书”，服务器上显示“校验通过”。
  # 先落到临时文件、校验、再原子替换，避免一次失败的导出毁掉上一版可用产物。
  local tmp_raw="${TMPDIR:-/tmp}/backend-${tag}.tar"
  local tmp_gz="${dist}/.backend-${tag}.tar.gz.tmp"
  if ! docker save -o "${tmp_raw}" "${image}"; then
    echo "  → ✗ docker save 失败" >&2
    rm -f "${tmp_raw}" "${tmp_gz}"
    exit 1
  fi
  if ! gzip -c "${tmp_raw}" > "${tmp_gz}" || ! gzip -t "${tmp_gz}"; then
    echo "  → ✗ gzip 压缩/校验失败" >&2
    rm -f "${tmp_raw}" "${tmp_gz}"
    exit 1
  fi
  rm -f "${tmp_raw}"
  mv -f "${tmp_gz}" "${tar_file}"
  (cd "${dist}" && sha256_of "backend-${tag}.tar.gz" > "backend-${tag}.tar.gz.sha256")

  echo ""
  echo "  → 产物:"
  ls -lh "${tar_file}" "${tar_file}.sha256"
  echo ""
  echo "  下一步（在 docker/ 目录执行）:"
  echo "    scp ${tar_file} ${tar_file}.sha256 \\"
  echo "        docker-compose.backend.yaml docker-compose.local-deps.yaml \\"
  echo "        .env.example 用户@服务器:~/fastapiadmin/"
  echo "    另需把 ${ENV_PROD_TEMPLATE} 拷成服务器上的 env.prod（填 DATABASE_HOST 等）"
}

cmd_image_load() {
  print_banner "加载后端镜像"
  check_docker

  local tar_file="${1:-}"
  if [ -z "${tar_file}" ]; then
    # 同时覆盖开发机的 dist/ 与服务器上平铺的目录
    tar_file="$(ls -t "${COMPOSE_DIR}"/backend-*.tar.gz "${COMPOSE_DIR}"/dist/backend-*.tar.gz 2>/dev/null | head -n 1 || true)"
  fi
  if [ -z "${tar_file}" ] || [ ! -f "${tar_file}" ]; then
    echo "  → ✗ 未找到镜像包"
    echo "  → 用法: bash deploy.sh image:load [backend-3.1.0.tar.gz]"
    echo "  → 或把 backend-*.tar.gz 放在 ${COMPOSE_DIR}/ 下"
    exit 1
  fi
  echo "  → 使用镜像包: ${tar_file}"

  if [ -f "${tar_file}.sha256" ]; then
    echo "  → 校验 SHA256 ..."
    local want got
    want="$(awk '{print $1}' "${tar_file}.sha256" | head -n 1)"
    got="$(sha256_of "${tar_file}" | awk '{print $1}')"
    if [ "${want}" != "${got}" ]; then
      echo "  → ✗ 校验失败，镜像包可能损坏或被篡改"
      echo "    期望: ${want}"
      echo "    实际: ${got}"
      exit 1
    fi
    echo "  → 校验通过"
  else
    echo "  → ⚠ 未找到 ${tar_file}.sha256，跳过校验"
  fi

  echo "  → docker load ..."
  gunzip -c "${tar_file}" | docker load
  echo ""
  echo "  → 已加载镜像:"
  docker image ls fastapiadmin-backend
  echo ""
  echo "  下一步: bash deploy.sh db:migrate && bash deploy.sh start"
}

cmd_db_migrate() {
  print_banner "数据库迁移"
  check_docker
  check_env_prod
  echo "  → 执行 alembic upgrade head ..."
  dc run --rm backend alembic upgrade head
  echo "  → 迁移完成"
}

cmd_cert_init() {
  if [ "${MODE}" != "full" ]; then
    echo "✗ 证书管理仅适用于方式 A（服务器侧证书由其自身 nginx 维护）。" >&2
    exit 1
  fi
  print_banner "SSL 证书签发"
  echo "  域名: ${CERT_DOMAIN}"
  echo "  存储: ${SSL_DIR}/"
  echo ""

  check_docker
  check_compose_env
  ensure_ssl_www

  # 确保 nginx 在运行（提供 ACME webroot）
  if ! dc ps --format '{{.Name}}' 2>/dev/null | grep -q 'nginx'; then
    echo "  → 启动 nginx..."
    if ! dc up -d nginx; then
      echo "  → ✗ nginx 启动失败，无法提供 ACME webroot" >&2
      return 1
    fi
    sleep 2
  fi

  echo "签发证书中..."
  # 注意：本函数被 cmd_deploy 以 `cmd_cert_init || …` 调用，而 bash 在 `||` 左操作数
  # 语境下会**对整个函数体禁用 -e**，所以失败必须在这里显式判定，否则会静默返回 0。
  if ! dc run --rm certbot certonly --webroot -w /var/www/certbot \
    -d "${CERT_DOMAIN}" \
    --email "${CERT_EMAIL}" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring \
    --no-eff-email; then
    echo "  → ✗ 证书签发失败，nginx 将无法启动 HTTPS" >&2
    return 1
  fi

  echo ""
  echo "  证书路径: ${SSL_DIR}/live/${CERT_DOMAIN}/"
  echo "  续签: bash deploy.sh cert:renew"
}

cmd_cert_renew() {
  if [ "${MODE}" != "full" ]; then
    echo "✗ 证书管理仅适用于方式 A。" >&2
    exit 1
  fi
  print_banner "SSL 证书续签"
  check_docker
  check_compose_env

  dc run --rm certbot renew
  dc exec nginx nginx -s reload

  echo "  → 续签完成"
  echo "  → 建议 crontab: 0 3 * * 0 bash ${PROJECT_DIR}/deploy.sh cert:renew"
}

cmd_help() {
  echo "用法: bash deploy.sh <command>  （当前模式: ${MODE}，工作目录: ${COMPOSE_DIR}）"
  echo ""
  echo "方式 A 全套 Docker（仓库内）:"
  echo "  (无参数)             完整部署 — 环境检查 → 构建 → 证书 → 启动"
  echo "  restart:backend      构建镜像并重启后端，输出启动日志"
  echo "  image:export [tag]   构建并导出后端镜像 tar.gz + sha256 到 docker/dist/"
  echo "  cert:init            签发 Let's Encrypt SSL 证书"
  echo "  cert:renew           续签 SSL 证书"
  echo ""
  echo "方式 B 仅后端镜像（服务器上）:"
  echo "  image:load [tar]     校验并加载离线镜像包（默认取最新 backend-*.tar.gz）"
  echo "  db:migrate           执行数据库迁移（alembic upgrade head）"
  echo "  start --local-deps   启动，并叠加本机 mysql + redis"
  echo ""
  echo "通用:"
  echo "  start                启动服务"
  echo "  stop                 停止服务"
  echo "  restart              重启服务"
  echo "  status               查看服务运行状态"
  echo "  logs [服务]          查看日志（可选指定服务名）"
  echo "  help                 显示本帮助"
  echo ""
  echo "项目路径: ${PROJECT_DIR}"
}

# ==================== 入口 ====================

case "${1:-deploy}" in
  deploy|full)      cmd_deploy          ;;
  start)            cmd_start "${2:-}"  ;;
  stop)             cmd_stop            ;;
  restart)          cmd_restart         ;;
  restart:backend)  cmd_restart_backend ;;
  status)           cmd_status          ;;
  logs)             cmd_logs "${2:-}"   ;;
  image:export)     cmd_image_export "${2:-}" ;;
  image:load)       cmd_image_load "${2:-}"   ;;
  db:migrate)       cmd_db_migrate     ;;
  cert:init)        cmd_cert_init      ;;
  cert:renew)       cmd_cert_renew     ;;
  help|--help|-h)   cmd_help           ;;
  *)
    echo "未知命令: $1"
    echo "可用命令: deploy | start [--local-deps] | stop | restart | restart:backend | status | logs | image:export | image:load | db:migrate | cert:init | cert:renew | help"
    exit 1
    ;;
esac
