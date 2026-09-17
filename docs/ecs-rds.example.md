# ECS / RDS / Redis / RabbitMQ（模板 · 无真实密码）

> **本仓库已公开（GitHub MIT）。真实凭据只放本机 `docs/ecs-rds.local.md`（已 gitignore），切勿提交。**
>
> 从 cumustabilis `docs/ecs&rds.md` 迁移结构。本机若尚无 local 文件，可从该仓库复制并改名为 `ecs-rds.local.md`。

## 快速 SSH

```bash
ssh root@47.102.208.231
# 密码见 docs/ecs-rds.local.md「ECS SSH root」
```

| 字段 | 值（非机密） |
|------|-------------|
| 公网 IP | `47.102.208.231` |
| 内网 IP | `172.16.48.255` |
| 实例 ID | `iZuf65p5sljpx18laf9p91Z` |
| SSH 用户 | `root` |
| SSH 密码 | **仅 local 文件** |

## RDS MySQL

| 字段 | 值 |
|------|-----|
| 外网 | `rm-uf608r538nh6i50f3to.mysql.rds.aliyuncs.com` |
| 内网 | `rm-uf608r538nh6i50f3.mysql.rds.aliyuncs.com` |
| 端口 | `3306` |
| 用户 | `root` |
| 密码 | **仅 local 文件**（与 ECS SSH 相同） |

## Redis（跑在 ECS）

| 字段 | 值 |
|------|-----|
| 公网 | `47.102.208.231:6379` |
| 内网 | `172.16.48.255:6379` |
| 密码 | **仅 local 文件**（**≠** SSH / RDS） |

## RabbitMQ（跑在 ECS）

| 字段 | 值 |
|------|-----|
| 公网 AMQP | `47.102.208.231:5672` |
| Management | `http://47.102.208.231:15672` |
| 用户 | `stabx` |
| 密码 | **仅 local 文件** |

## Nacos

| 用途 | URL |
|------|-----|
| API | `http://47.102.208.231:8848/nacos/` |
| Console | 历史曾用 `18080`；**现与 mystabx Web 冲突时勿占用**（本仓库 Web 默认 `STABX_PORT=18080`） |

## mystabx Web（本仓库）

| 字段 | 值 |
|------|-----|
| 监听 | `0.0.0.0:18080`（`STABX_PORT`） |
| 机内健康 | `http://127.0.0.1:18080/` · `/health` |
| 公网 | `http://47.102.208.231:18080/`（需安全组放行 TCP 18080） |
| 管理员 | 仅 ECS `.env` 的 `STABX_ADMIN_*`（勿提交；勿用 `admin123`） |
| 安装 | `./scripts/install_linux.sh`（Web-only；**不装** PySide6 / qdarkstyle） |
| 服务 | `scripts/mystabx-vnpy.service` → systemd；产品入口 Web，无桌面 Qt |
| 远端路径 | `/stabx/mystabx_vnpy` |
| 本机部署 | `./scripts/deploy_ecs.sh`（读 `.env.ecs`；rsync 后先停再启） |

## ECS 自动部署

凭据只放本机 `.env.ecs`（gitignore）。脚本**不会**把本机 `.env` / `.env.ecs` 覆盖到服务器；远端已有 `.env` 会保留。

```bash
# 一次性 / 手动
./scripts/deploy_ecs.sh

# 本机改代码后监视部署（防抖默认 45s；可 brew install fswatch）
./scripts/watch_deploy_ecs.sh

# Cursor afterFileEdit hook（仓库已带 .cursor/hooks.json）
# 开启：touch .cache/auto_deploy_ecs.enabled
# 或：export STABX_AUTO_DEPLOY_ECS=1
# 关闭：rm -f .cache/auto_deploy_ecs.enabled
# 防抖秒数：DEPLOY_ECS_DEBOUNCE=60
# 日志：.cache/deploy_ecs.log
```

行为摘要：

1. rsync → `/stabx/mystabx_vnpy`（排除 `.venv`、`node_modules`、`.git`、本机 `.env` / `.env.ecs`；保留远端 `.env`）
2. 确认远端已有 `.venv`（最多 `--wait-ready`，默认 60s）；**不会**在服务器重跑 `install_linux` / `uv sync`
3. `systemctl stop mystabx-vnpy`（或杀 `start.sh` / `uvicorn` / 释放 18080）
4. 手动部署默认 `npm run build` 后 `systemctl start`；自动部署（hook / watch）默认 `--no-build` + `start.sh --skip-build`

## ClickHouse（ECS 本机 · 官方 deb）

> 你给的 [源码构建文档](https://clickhouse.com/docs/zh/resources/develop-contribute/build/build) 面向贡献者；文档写明若不改源码应装预构建包。本机仅约 3.5 GB 内存，源码编译不现实，已按 [Debian/Ubuntu 安装](https://clickhouse.com/docs/zh/install/debian_ubuntu) 装好。

| 字段 | 值 |
|------|-----|
| HTTP | `http://127.0.0.1:8123`（机内；`/ping` → `Ok.`） |
| 用户 / 密码 | `default` / 空（对齐 mystabx 默认） |
| 库 | `vnpy`（已 `CREATE DATABASE`） |
| 服务 | `systemctl status clickhouse-server` |

## 环境变量（本地覆盖示例）

复制为 `.env.ecs`（已 gitignore）后填写密码：

```bash
ECS_HOST=47.102.208.231
ECS_USER=root
ECS_PASSWORD=

MYSQL_HOST=rm-uf608r538nh6i50f3to.mysql.rds.aliyuncs.com
MYSQL_USER=root
MYSQL_PWD=

REDIS_HOST=47.102.208.231
REDIS_PORT=6379
REDIS_PWD=

RABBIT_HOST=47.102.208.231
RABBIT_PORT=5672
RABBIT_USER=stabx
RABBIT_PWD=

NACOS_HOST=47.102.208.231
```

权威全文（含核实记录、排障、工具链版本）见本机 **`docs/ecs-rds.local.md`**。
