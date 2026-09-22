# mystabx_vnpy

基于 [FastapiAdmin](https://gitee.com/jeromexiong/fastapiadmin)（v3.1.0）能力迁入本仓库 `main` 的现代化全栈管理平台脚手架。  
架构保持 FastAPI 插件化后端 + Vue3 管理后台 + UniApp + Flutter 三端统一，便于在此基础上继续演进交易/业务能力。

> 历史完整交易产品实现仍归档在 **`vnpy`** 分支（未改写历史）。本分支以 fastapiadmin 为重构底座。

上游源码许可见 [`licenses/fastapiadmin-LICENSE`](licenses/fastapiadmin-LICENSE)（MIT）。本仓库整体许可见 [`LICENSE`](LICENSE)。

---

## 功能一览（自 fastapiadmin 迁入）

| 模块 | 能力 |
| --- | --- |
| 仪表盘 | 工作台、分析页 |
| 系统管理 | 用户、角色、菜单、部门、岗位、字典、配置、公告 |
| 监控管理 | 在线用户、服务器监控、缓存监控 |
| 任务管理 | 定时任务（APScheduler） |
| 日志管理 | 操作日志审计 |
| 开发工具 | 代码生成、表单构建、接口文档 |
| 文件 / AI | 统一文件存储、Agno 智能体扩展 |
| 三端客户端 | Web 管理后台、UniApp 小程序、Flutter App |
| 部署 | 本机 / ECS 直接运行（非 Docker） |

---

## 工程结构

```
mystabx_vnpy/
├── backend/                 → FastAPI + SQLAlchemy + Alembic（uv）
│   ├── app/plugin/          → 业务插件 module_*
│   ├── app/core/            → DB / Auth / CRUD / 限流 / 插件发现
│   └── main.py              → typer CLI 入口
├── frontend/
│   ├── web/                 → Vue3 + Element Plus 管理后台
│   ├── uniapp/              → UniApp + Wot UI
│   └── flutter/             → Flutter + Riverpod + TDesign
├── docs/                    → 设计与运维文档
└── licenses/                → 上游 MIT 等第三方许可
```

> Docker Compose / Dockerfile 已从本仓库移除；请按下方「快速开始」用本机或 ECS 直接跑前后端。

---

## 环境要求

| 类型 | 版本 |
| --- | --- |
| Python | ≥ 3.14（与上游 fastapiadmin 一致） |
| Node.js / pnpm | ≥ 20 / ≥ 9 |
| Flutter（可选） | ≥ 3.44 |
| MySQL / PostgreSQL / SQLite | 见 `backend/env` |
| Redis | ≥ 6.x（建议 7.x；ECS 已装 8.x） |

运维用 Redis / RDS 主机见根目录 `.env.ecs.example`（复制为 `.env.ecs`，勿提交密钥）。
ECS `47.102.208.231` 上 `redis-server` 监听 `0.0.0.0:6379` 且启用 `requirepass`；
同机应用用 `REDIS_HOST=127.0.0.1`，本机开发用公网 IP（需安全组放行 TCP 6379）。
后端键名 `REDIS_PASSWORD`（对应运维 `REDIS_PWD`）；库名 **mystabx_vnpy**；API 端口 **18080**。
对齐明细见 [`docs/ecs-mysql-redis-ports.md`](docs/ecs-mysql-redis-ports.md)（含 ECS 切流注意：勿打断现网 18080 交易服务）。

---

## 快速开始

### 1. 后端

```bash
cd backend
cp env/.env.example env/.env
# 填写 DATABASE_PASSWORD / REDIS_PASSWORD（与 .env.ecs 一致）

uv sync
source .venv/bin/activate

# 业务库已在 RDS；若本地自建：
# mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS mystabx_vnpy DEFAULT CHARACTER SET utf8mb4;"

python main.py upgrade --env=dev
python main.py run --env=dev
```

- API：`http://127.0.0.1:18080`
- Swagger：`http://127.0.0.1:18080/api/v1/docs`

### 2. Web 管理后台

```bash
cd frontend/web
pnpm install
pnpm dev
```

访问：`http://127.0.0.1:5173`

### 3. UniApp / Flutter（可选）

见 `frontend/uniapp/README.md`、`frontend/flutter/README.md`：

| 组件 | 地址 |
| --- | --- |
| UniApp H5 | `http://127.0.0.1:6120` |
| Flutter Web | `http://127.0.0.1:6150` |
| 后端 API（各端目标） | `http://127.0.0.1:18080` |

---

## 分支说明

| 分支 | 内容 |
| --- | --- |
| `main` | 本脚手架（fastapiadmin 能力迁入后的重构底座） |
| `vnpy` | 迁入前完整交易产品代码归档 |

远程：Gitee `origin`、GitHub `github`（若可达则同步同名分支）。

请勿将 `.env` / `.env.ecs` 等密钥提交入库。
