# Docker 部署说明

本目录包含两种运行方式的编排与配置。

## 两种运行方式

| 方式 | 适用场景 | 编排文件 | 后端来源 |
|------|----------|----------|----------|
| **A 全套 Docker** | 本机开发 / 单机服务器一键起全栈 | `docker-compose.yaml` | 就地 `build` |
| **B 仅后端镜像** | 服务器已有 MySQL/Redis/Nginx，只要跑后端 | `docker-compose.backend.yaml` | 离线 `image:load` |

`deploy.sh` 通过目录特征自动判断模式：仓库内（存在 `docker/docker-compose.yaml`）为 A，服务器目录（存在 `docker-compose.backend.yaml`）为 B。

## 目录结构

```
docker/
├── docker-compose.yaml              # 方式 A：MySQL + Redis + Backend + Nginx + Certbot
├── docker-compose.dev.yaml          # 方式 A 开发档：源码挂载热更新（叠加使用）
├── docker-compose.backend.yaml      # 方式 B：仅 backend
├── docker-compose.local-deps.yaml   # 方式 B 可选：本机 mysql + redis
├── .env.example                     # Compose 变量模板（密码、端口、镜像 tag）
├── backend/Dockerfile               # 后端镜像（源码 COPY 进镜像，监听 18080）
├── nginx/                           # Nginx 配置 + 静态资源 + SSL
├── mysql/data/  redis/data/         # 方式 A 的数据目录
└── dist/                            # image:export 产物（已 gitignore）
```

## 端口口径（重要）

**容器内统一监听 18080**，宿主机端口由 `.env` 的 `BACKEND_PORT` 决定（默认 18080）。
改端口必须三处同步：`Dockerfile` 的 `EXPOSE`、编排的 `SERVER_PORT` 与环境变量、`nginx.conf` 的 `proxy_pass`。
`backend/tests/test_docker_deploy_config.py` 会把这些口径钉住，改漏任一处测试即红。

## 方式 A：全套 Docker

```bash
cd docker
cp .env.example .env                 # 填 MySQL/Redis 密码
cp ../backend/env/.env.prod.example ../backend/env/.env.prod   # 填 SECRET_KEY 与数据库地址
bash ../deploy.sh                    # 完整部署（构建 → 证书 → 启动）
bash ../deploy.sh status
bash ../deploy.sh logs backend
```

**开发态热更新**（改代码即时生效，不重建镜像）：

```bash
cd docker
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d
```

> ⚠️ 启动/停止 dev 栈**不要**用 `bash ../deploy.sh start|restart`：它们走的是不带 dev 覆盖文件的
> `docker compose up -d`，会以「无挂载」配置**重建** backend，源码挂载静默丢失。
> 改完代码用 `bash ../deploy.sh restart:backend`：只重启容器、不 recreate（因此源码挂载保留），
> 但它会先 `build` 镜像并做一次 alembic 迁移检查。
> 另外 dev 栈同样需要 `backend/env/.env.prod` 存在（覆盖文件不能移除主文件的 `env_file`）。

## 方式 B：只交付后端镜像

### 开发机（在仓库根目录执行）

```bash
git pull
[ -f docker/.env ] || cp docker/.env.example docker/.env   # compose 解析整份 project 需要它（已存在则不覆盖）
bash deploy.sh image:export 3.1.0     # → docker/dist/backend-3.1.0.tar.gz + .sha256
```

脚本会校验镜像架构是否为 `linux/amd64`（服务器架构），不是会给出警告。
缺少 `docker/.env` 时脚本会在入口直接提示（compose 的 `${MYSQL_PASSWORD:?}` 等守卫要求它存在）。

### 服务器（起步文件）

`image:export` 结束时会打印需要 scp 的清单，服务器目录与之对应：

```
~/fastapiadmin/
├── deploy.sh                       # 从仓库拷
├── docker-compose.backend.yaml     # 从 docker/ 拷
├── docker-compose.local-deps.yaml  # 从 docker/ 拷（仅本机缺 MySQL/Redis 时需要）
├── .env.example                    # 从 docker/ 拷（scp 清单里就有）
├── .env                            # cp .env.example → .env（端口、镜像 tag、依赖密码）
├── env.prod.example                # scp 开发机的 backend/env/.env.prod.example → 服务器 ./env.prod.example
├── env.prod                        # cp env.prod.example → env.prod（填 DATABASE_HOST 等）
├── backend-3.1.0.tar.gz            # scp 上来
└── backend-3.1.0.tar.gz.sha256     # 一起 scp 上来，否则镜像加载时跳过校验
```

> ⚠️ 仓库里的模板名是 `.env.prod.example`（**有点**）。scp 时要把目标名写死，否则会落地成隐藏文件
> `.env.prod.example`，紧接的 `cp env.prod.example env.prod` 就会报 `No such file`：
>
> ```bash
> scp backend/env/.env.prod.example 用户@服务器:~/fastapiadmin/env.prod.example
> ```

```bash
bash deploy.sh image:load            # SHA256 校验 + docker load
bash deploy.sh db:migrate            # 首次部署 / 升级后执行（不会自动跑）
bash deploy.sh start                 # 连服务器已有 MySQL/Redis
bash deploy.sh start --local-deps    # 本机没有 MySQL/Redis 时，叠加容器版依赖
bash deploy.sh status
bash deploy.sh logs backend
```

`env.prod` 里要填 `DATABASE_HOST` / `REDIS_HOST` 等指向已有实例；`--local-deps` 时这些会被 compose 注入的容器地址自动覆盖（OS 环境变量优先级最高），无需改文件。

### 服务器侧 nginx（反代示例）

```nginx
location /api/v1 {
    proxy_pass http://127.0.0.1:18080;   # backend 容器只绑回环
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;             # WebSocket
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 配置注入机制

应用配置一律通过 `env_file` 以环境变量注入，**不挂载配置文件**：

- 方式 A：`env_file: ../backend/env/.env.prod`
- 方式 B：`env_file: ./env.prod`

优先级：`environment:` > `env_file:` > `env/.env` 文件 > 代码默认值。

这样选是因为：文件缺失时 compose **直接报错退出**；而 `volumes` 挂载一个不存在的文件时，docker 会把缺失的源路径**创建成目录**，配置静默丢失。

## SSL 证书（方式 A）

```bash
bash ../deploy.sh cert:init
bash ../deploy.sh cert:renew         # 建议 crontab: 0 3 * * 0
```

## 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| compose 报 `env file ... not found` | `.env.prod` / `env.prod` 未创建 | 按上文 `cp` 模板后填写 |
| 接口 502 | 端口口径不一致 | `cd backend && uv run pytest tests/test_docker_deploy_config.py` |
| 改代码后容器没变化 | 方式 B 用的是镜像内代码 | 重新 `image:export` → `image:load` → `bash deploy.sh start`（`docker load` 只换 tag，运行中的容器仍跑旧镜像） |

## 验收状态

验收时点：`lite` 分支 `3ebd6d2b`（工作区干净，即本文件所在提交的父提交），机器为 macOS arm64。
下表「本机已验证」的每一行都来自本次实际执行的输出；**本机跑不了的一律写「未验证」**，不做推测性背书。

### 本机已验证（2026-09-18）

`uv run --no-sync` 是必需的：pytest / ruff / pyright 不在裸 PATH 上。

| 项 | 命令 | 结果 |
|----|------|------|
| 配置一致性 | `uv run --no-sync pytest tests/test_docker_deploy_config.py -q` | ✅ `18 passed`（exit 0） |
| 后端全量测试 | `uv run --no-sync pytest -q` | ✅ `180 passed, 1 warning in 4.82s`（exit 0） |
| 静态检查 | `uv run --no-sync ruff check .` / `uv run --no-sync pyright` | ✅ `All checks passed!` / `0 errors, 0 warnings, 0 informations` |
| 脚本语法 | `/bin/bash -n deploy.sh`（仓库根目录） | ✅ 无输出（exit 0，bash 3.2.57） |
| 编排离线解析 | `docker-compose -f … config -q` 四种组合（见下） | ✅ 四组均 exit 0 |
| 缺配置响亮失败 | 删掉 `env.prod` 后再 `config -q` | ✅ 两组均 exit 1 + `env file … not found`（不是静默回落默认值） |
| 构建上下文过滤 | `podman build -f /tmp/probe.Dockerfile -t probe-t7-ctx .` → `podman run --rm probe-t7-ctx sh -c 'find /probe …'` | ✅ 见 §构建上下文探针 |
| 镜像自包含 | `podman run --rm localhost/fastapiadmin-backend:task0 sh -c 'ls -a /home'` | ✅ 见 §镜像自包含（用的是缓存镜像，**未**在本次重建） |
| 镜像可启动 + 健康端点 | `podman run … -e DATABASE_TYPE=sqlite -e REDIS_ENABLE=false …` + `curl /common/health/` | ✅ 200（本机 arm64 仿真下约 22s 就绪） |

> 冒烟用的参数是 `ENVIRONMENT=dev` + SQLite + 关 Redis，**不是** compose 的生产参数
> （`ENVIRONMENT=prod` + 真实 MySQL/Redis），所以它证明的是「镜像能起、应用能响应」，不是生产栈可用。
> 该次日志里持续刷 `Error getting due jobs from job store 'redis' … Connection refused` —— 这是
> `REDIS_ENABLE=false` 的既有表现，本次未深究，也不代表部署链路有问题。

#### 编排离线解析（`docker-compose` 5.5.0，`config` 不需要 daemon）

在当前文件的 `/tmp` 镜像里跑（`backend/env/.env.prod` 与服务器侧 `env.prod` 由 `.env.prod.example` 生成，
`.env` 由 `.env.example` 生成）：

| 组合 | `config -q` | 解析出的服务 |
|------|-------------|--------------|
| `-f docker-compose.yaml` | exit 0 | `mysql` `redis` `backend` `nginx`（`certbot` 属 `profiles: ["manual"]`，不列） |
| `-f docker-compose.yaml -f docker-compose.dev.yaml` | exit 0 | 同上；`backend` 多出 `source: <repo>/backend → target: /home`，端口仍 `18080` |
| `-f docker-compose.backend.yaml` | exit 0 | 仅 `backend` |
| `-f docker-compose.backend.yaml -f docker-compose.local-deps.yaml` | exit 0 | `mysql` `redis` `backend`；`DATABASE_HOST: mysql`、`REDIS_HOST: redis`、`host_ip: 127.0.0.1`、`target: 18080` |

#### 构建上下文探针

```bash
cat > /tmp/probe.Dockerfile <<'EOF'
FROM docker.m.daocloud.io/library/alpine:latest
COPY ./backend/ /probe/
EOF
podman build --pull=never -q -f /tmp/probe.Dockerfile -t probe-t7-ctx .
```

`podman run` 实测：`/probe/env` 只有 `.env.example` 与 `.env.prod.example`（**无** `.env`）；
`find /probe -name '*.db' -o -name '*.sqlite*'` **零命中** —— 而宿主 `backend/fastapiadmin.db` 确实存在，
说明 `backend/*.db` 规则真的在生效，不是「无对象可排除」；`/probe/.venv`、`/probe/logs` 也都不存在。

> 探针镜像用的是临时 `alpine` 基底，只用来验证 `.dockerignore` 的过滤结果，不涉及 `docker/backend/Dockerfile` 本身。
> 基底与真实镜像不同（真实镜像基于 `python:3.14-slim-bookworm`）。

#### 镜像自包含

用的是 Task 0 缓存的镜像 `localhost/fastapiadmin-backend:task0`（2026-09-18 13:51 +0800 构建，
`pyrate-limiter 4.5.0` 已装 → 是修复后的那份；本次**没有**重建，因为构建要数分钟）：

```bash
podman run --rm localhost/fastapiadmin-backend:task0 sh -c 'ls -a /home; find /home -name ".env" -o -name "*.db"'
```

`/home` 下有 `app` `main.py` `requirements.txt` `static` 等；**没有** `.venv`、`logs`、`fastapiadmin.db`、`.env`。
`python -c "import pyrate_limiter, fastapi_limiter"` → `import OK`。

`dc55c58f..HEAD` 期间**只有** `backend/tests/test_docker_deploy_config.py` 变过；对镜像内
`app/**`（147 个 `.py`）+ `main.py` + `requirements.txt` 与 HEAD 逐文件算 `sha256sum` 比对，**零差异**。
即：这个镜像的运行时代码与 HEAD 等价（仅镜像里的 `tests/` 是旧版，不影响运行）。

### 本机未验证

| 项 | 为什么 |
|----|--------|
| 方式 A 全栈 `docker compose up` 端到端（nginx → backend → MySQL/Redis） | 本机**无 `docker` CLI**，`docker.io` 不可达；`podman` 缓存里也没有 `mysql:8.0`、`certbot/certbot` |
| 方式 B 服务器侧端到端（`image:load` → `db:migrate` → `start` → 健康检查） | 同上；服务器已有 nginx 反代、外部 MySQL/Redis 均不在本机 |
| `image:export` / `image:load` 的真实 tar 包与 SHA256 校验 | 依赖 `docker save` / `docker load`；此前只用桩 `docker` 核对过命令向量，**没有真实镜像包** |
| `platform: linux/amd64` 在真实 amd64 机器上的行为 | 本机 arm64，只能仿真运行（podman 会打印 platform 不匹配警告） |
| `deploy.sh` 各子命令在真 docker 上的实际效果 | 无 docker CLI |
| 镜像**重建**在本机 arm64 上是否成功 | 本次未重建（数分钟且已在早前任务验证过）；用的是缓存镜像 |

### 需在有 Docker 的机器上执行

上表「未验证」的部分请在目标机器上补齐。两条 `curl` 都必须带 `-L`：不带尾斜杠的路由是 **307**。

```bash
# 方式 A
cd docker && cp .env.example .env
cp ../backend/env/.env.prod.example ../backend/env/.env.prod
bash ../deploy.sh
curl -sL -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/api/v1/common/health   # 期望 200
docker compose exec backend printenv SERVER_PORT                                      # 期望 18080

# 方式 B（在服务器上）
bash deploy.sh image:load && bash deploy.sh db:migrate && bash deploy.sh start
curl -sL -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/api/v1/common/health   # 期望 200
docker inspect -f '{{json .Mounts}}' backend                                          # 应无源码挂载
```

升级时**额外确认容器真的换了镜像** —— `docker load` 只替换 tag，不会动正在运行的容器：

```bash
docker inspect -f '{{.Image}}' backend    # 加载前记下
bash deploy.sh image:load
bash deploy.sh start
docker inspect -f '{{.Image}}' backend    # 应与加载前不同；相同即说明容器仍在跑旧镜像
```
