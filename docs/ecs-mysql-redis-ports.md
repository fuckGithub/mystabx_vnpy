# ECS MySQL / Redis / 端口对齐（mystabx_vnpy）

模板说明：真实密码只写本机 `.env.ecs` / `backend/env/.env.prod`（已 gitignore），勿提交。

## 目标口径（相对上游 fastapiadmin）

| 项 | 上游默认 | mystabx |
| --- | --- | --- |
| 后端监听 | `6100` | **`18080`**（`SERVER_PORT` / `STABX_PORT` / `BACKEND_PORT`） |
| Web Vite | `6110` | **`5173`**（`VITE_PORT`） |
| MySQL 库名 | `fastapiadmin` | **`mystabx_vnpy`** |
| MySQL 用户 | `fastapiadmin` | **`root`**（RDS） |
| MySQL 端口 | `3306` | `3306` |
| Redis | 本地自建 / 容器（历史） | ECS `redis-server`：`127.0.0.1:6379`（同机）/ 公网 IP（本机开发） |
| Redis 密码键 | `REDIS_PASSWORD` | 运维侧 `REDIS_PWD` → 后端 `REDIS_PASSWORD` |

## RDS MySQL（非机密）

| 字段 | 值 |
| --- | --- |
| 外网 | `rm-uf608r538nh6i50f3to.mysql.rds.aliyuncs.com` |
| 内网（ECS 应用优先） | `rm-uf608r538nh6i50f3.mysql.rds.aliyuncs.com` |
| 端口 | `3306` |
| 用户 | `root` |
| 库名 | `mystabx_vnpy` |

运维别名：`MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PWD` / `MYSQL_DB`  
FastapiAdmin：`DATABASE_HOST` / `DATABASE_PORT` / `DATABASE_USER` / `DATABASE_PASSWORD` / `DATABASE_NAME`

## Redis（ECS）

| 字段 | 值 |
| --- | --- |
| 公网 | `47.102.208.231:6379` |
| 同机 | `127.0.0.1:6379` |
| 密码 | 仅 `.env.ecs` 的 `REDIS_PWD`（= 后端 `REDIS_PASSWORD`） |

## Nginx

历史 mystabx：公网 `80` → `127.0.0.1:18080`（见 `vnpy` 分支 `scripts/nginx-mystabx.conf`）。  
本仓库已移除 Docker Compose；反向代理请用宿主机 Nginx 指到本机 `18080`。

## ECS 切流注意（勿打断线上交易）

当前 ECS 上 **交易 Web 已占用 `18080`**（systemd / `start.sh`）。

- **不要**在未切流前，把新 FastapiAdmin 栈再绑到同一 `18080` 覆盖现网。
- 先按模板对齐 **MySQL / Redis**（`backend/env/.env.prod.example`、`.env.ecs.example`）。
- 并行试跑新栈时可用临时端口（例如改 `SERVER_PORT` / `BACKEND_PORT`），确认后再与 nginx / systemd 一并切到 `18080`。
- 远端已有 `.env` 由运维保留；本仓库模板**不含**真实密钥，也不会自动覆盖远端密钥文件。

## 相关文件

- `.env.ecs.example`
- `backend/env/.env.example` / `.env.prod.example`
- `web/env/*.example`、`uniapp/env/*.example`
