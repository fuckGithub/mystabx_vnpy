# Stabx Web 交易台 — 规划文档

> 状态：**P0 骨架已落地**（FastAPI headless + Vue 交易台）。产品入口是 **Web**：`./start.sh`。桌面 `main.py` / PySide MainWindow 仅作遗留代码，不是默认入口。本目录是设计文档；实现按 `features/ + core/ + ui/` 放在本仓库根目录。

## 项目定位

将 vnpy（VeighNa）从 PySide6 桌面终端改造成 **B/S 架构的团队交易终端**：

- Python 进程内跑 vnpy 的 `MainEngine` / `EventEngine`（无界面，headless）
- 通过 **REST + WebSocket** 暴露能力
- 前端用 **Vue 3** 做完整交易台
- 支持**多用户**、**每用户独立账户**、**用户级隔离 + 管理员**

## 已确认的关键决策

| 决策项 | 结论 |
|---|---|
| 下单能力 | 完整 Web 交易台（浏览器下单/撤单） |
| 用户规模 | 局域网 / 小团队多用户 |
| 前端技术栈 | Vue 3 + Vite + TypeScript + Element Plus + ECharts |
| 后端技术栈 | FastAPI + Uvicorn，headless 启动 vnpy |
| 数据存储 | ClickHouse（时序/事件）+ SQLite（业务/配置）三层混合 |
| 账户模型 | 每用户独立 CTP 账户（多 gateway 实例） |
| 权限模型 | 用户级隔离 + 一个管理员标志（无复杂 RBAC） |
| 目录组织 | 功能域优先：`features/ + core/ + ui/`（不按 backend/frontend 分层） |
| 运行入口 | `./start.sh`（单进程托管 API + 构建后的 SPA）；不要用 `main.py` 当产品 |

## 文档索引

| 文档 | 内容 |
|---|---|
| [01-架构与功能规划](./01-架构与功能规划.md) | 总体架构、技术栈、功能模块 |
| [02-数据存储方案](./02-数据存储方案.md) | 三层存储、ClickHouse/SQLite 表结构、加密 |
| [03-账户隔离与权限](./03-账户隔离与权限.md) | 多 gateway、用户级隔离、管理员、后端伪代码 |
| [04-WebSocket消息协议](./04-WebSocket消息协议.md) | 消息 envelope 与字段级 payload |
| [05-前端方案与目录结构](./05-前端方案与目录结构.md) | 轻量化前端、功能域目录、依赖清单 |
| [06-实施路线图](./06-实施路线图.md) | P0 / P1 可执行开发任务清单 |

## 与桌面端的关系

- **产品（Web）**：`core/` + `features/` + `ui/`，`./start.sh` 一键起 FastAPI + Vue
- **遗留（桌面）**：根目录 `main.py` + `mystabx/`，官方 MainWindow。保留但不作为入口，不要按这个跑产品

未完成（见 [06-实施路线图](./06-实施路线图.md) P1）：K 线、ClickHouse 行情入库、风控、策略/回测、Docker。

## 怎么跑

用户自己启动，不要让 agent 代启，也不要启动 Qt。

一键（默认生产 / 部署：构建 Vue，单个 uvicorn 托管 API + `dist/`）：

```bash
./start.sh
```

本机热更新（同一脚本内起 uvicorn + Vite，仍不要开两个终端）：

```bash
./start.sh --dev
```

环境变量见仓库根目录 `.env.example`（`STABX_HOST` / `STABX_PORT` / `STABX_ADMIN_PASSWORD` / `STABX_JWT_SECRET` 等）。不要提交真实 SimNow 密码。

冒烟（不打开交易窗口、不常驻 uvicorn）：

```bash
.venv/bin/python scripts/smoke_web.py
```

默认管理员 `admin` / `admin123`（仅本机首次引导，可用 `STABX_ADMIN_PASSWORD` 覆盖）。ClickHouse 表结构在仓库根目录 `ch_schema.sql`，P0 实时链路不依赖 ClickHouse 进程。
