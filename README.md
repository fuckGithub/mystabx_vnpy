# Stabx Web 交易台

浏览器里用的期货交易台：Vue 网页 + FastAPI（REST / WebSocket）+ 进程内 vnpy `MainEngine`。产品入口是 Web，不是桌面 Qt / `main.py`。

> 状态：**P0 骨架已落地**（FastAPI headless + Vue 交易台）。产品入口是 **Web**：`./start.sh`。桌面 `main.py` / PySide MainWindow 仅作遗留代码，不是默认入口。`docs/` 是设计文档；实现按 `features/ + core/ + ui/` 放在仓库根目录。

规划文档见下文「文档索引」（[docs/01](docs/01-架构与功能规划.md)–[docs/06](docs/06-实施路线图.md)）。

## 后端与引擎归属

本项目的**后端交易运行时是 vn.py（VeighNa）**，不是本仓库原创的交易引擎或撮合系统。

具体来说：`MainEngine`、事件引擎（`EventEngine`）、OMS（`OmsEngine`），以及委托、持仓、资金、Tick 等对象，均来自 [vnpy](https://github.com/vnpy/vnpy)；CTP 柜台网关 `CtpGateway` 来自 [vnpy_ctp](https://github.com/vnpy/vnpy_ctp)。本仓库是围绕 vnpy 的 **Web UI + FastAPI 托管层**（浏览器界面、REST / WebSocket、多用户与通道配置），**不重新实现**交易所撮合或柜台通信协议。

**许可（事实说明，不构成法律意见）**：vn.py 与 vnpy_ctp 均为 MIT 许可（Copyright (c) 2015-present, Xiaoyou Chen）。使用或分发时须保留其版权与许可声明。本项目不主张对 vnpy 或其组件的所有权。完整原文见根目录 [NOTICE](NOTICE)、[THIRD_PARTY.md](THIRD_PARTY.md) 以及 [licenses/vnpy-LICENSE](licenses/vnpy-LICENSE)、[licenses/vnpy_ctp-LICENSE](licenses/vnpy_ctp-LICENSE)。本仓库未对本包装层另行声明许可证；包装层许可不覆盖、不替代 vnpy / vnpy_ctp 的许可。

**柜台与接口**：CTP API 由上海期货信息技术有限公司（上期技术）提供，与 vnpy 项目相互独立。SimNow / CTP 账号凭证以及交易所、期货公司接口各有其使用条款，须自行遵守。

## 项目定位

将 vnpy（VeighNa）从 PySide6 桌面终端改造成 **B/S 架构的团队交易终端**：

- Python 进程内跑 vnpy 的 `MainEngine` / `EventEngine`（无界面，headless）
- 通过 **REST + WebSocket** 暴露能力
- 前端用 **Vue 3** 做完整交易台
- 支持**多用户**、**每用户独立账户**、**用户级隔离 + 管理员**

## 项目功能

把 vnpy（VeighNa）跑成 **B/S 交易终端**：一个 Python 进程里启动 headless `MainEngine` / `EventEngine`，浏览器完成登录、连柜台、看行情、下单和查资金持仓。面向本机或局域网小团队，每用户独立 CTP 账户，用户级隔离，另有管理员。

| 菜单 | 路由 | 做什么 |
|---|---|---|
| **工作台** | `/workbench` | 首页：连接状态、持仓、已订阅行情、风险表、成交日志 |
| **市场行情** | `/market/quotes`、`/market/ticks` | 搜合约、订阅；实时 Tick |
| **交易下单** | `/trade/order`、`/trade/orders` | 下单面板（二次确认）；活动委托、撤单 |
| **资金持仓** | `/account/gateways`、`/account/funds`、`/account/positions`、`/account/trades` | 连接/断开网关；资金、持仓、成交 |
| **系统管理** | `/admin/users`、`/admin/accounts` | 管理员：用户管理、通道配置（SimNow / CTP） |

技术栈：Vue 3 + Vite + TypeScript + Element Plus + ECharts；FastAPI + Uvicorn；配置与账号在 SQLite（密钥 Fernet 加密）。ClickHouse 表结构在 `ch_schema.sql`，P0 实时链路不依赖 ClickHouse 进程。P1 尚未作为产品入口：K 线、ClickHouse 行情入库、风控、策略/回测、Docker（见 [docs/06-实施路线图.md](docs/06-实施路线图.md)）。

不要对 vnpy 引擎使用 `uvicorn --workers`（`MainEngine` 必须在同一进程内）。

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
| [01-架构与功能规划](docs/01-架构与功能规划.md) | 总体架构、技术栈、功能模块 |
| [02-数据存储方案](docs/02-数据存储方案.md) | 三层存储、ClickHouse/SQLite 表结构、加密 |
| [03-账户隔离与权限](docs/03-账户隔离与权限.md) | 多 gateway、用户级隔离、管理员、后端伪代码 |
| [04-WebSocket消息协议](docs/04-WebSocket消息协议.md) | 消息 envelope 与字段级 payload |
| [05-前端方案与目录结构](docs/05-前端方案与目录结构.md) | 轻量化前端、功能域目录、依赖清单 |
| [06-实施路线图](docs/06-实施路线图.md) | P0 / P1 可执行开发任务清单 |

## 与桌面端的关系

- **产品（Web）**：`core/` + `features/` + `ui/`，`./start.sh` 一键起 FastAPI + Vue
- **遗留（桌面）**：根目录 `main.py` + `mystabx/`，官方 MainWindow。保留但不作为入口，不要按这个跑产品

未完成（见 [06-实施路线图](docs/06-实施路线图.md) P1）：K 线、ClickHouse 行情入库、风控、策略/回测、Docker。

## 搭建步骤

仓库根目录操作。`./start.sh` 要求已有 **`.venv/bin/python`**、**Node.js**、**npm**。

### 1. Python 虚拟环境

`pyproject.toml` 要求 **Python ≥ 3.10**（本仓库类型检查按 3.13）。

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 2. CTP 网关（`vnpy_ctp`）

`pip install -e .` 不会装好可用的 CTP 接口，需按平台另装。

**macOS**（本仓库脚本）：Mac 官方 CTP API 是 6.7.7，**没有 6.7.11 的 Mac API**。用源码编译 6.7.7.2，不要对 `vnpy_ctp` 使用 `pip install -e`：

```bash
# 需先有 .venv，以及本机 uv、Homebrew ta-lib（脚本读 /opt/homebrew）
./scripts/install_macos.sh
```

该脚本会 `uv pip install -e .`，再 `git clone` `vnpy_ctp` 到 `.deps/vnpy_ctp` 后 `uv pip install .deps/vnpy_ctp`。

当前 Mac 构建的 `vnpy_ctp` **只带实盘 API**。通道里「柜台环境」固定为「实盘」；SimNow 也走生产前置，不是评测/穿透式测试 API。

**Linux**：需要对应平台的 `vnpy_ctp`（Linux `.so`）。不要把 Mac 编译产物拷到服务器。

### 3. 前端依赖

`package.json` 在仓库根；Vite 根目录是 `ui/`。`./start.sh` 在缺少 `node_modules` 时会执行 `npm install`。也可先手动装：

```bash
npm install
```

### 4. 环境变量

```bash
cp .env.example .env
```

按需改端口等。不要把真实 SimNow / CTP 密码或 InvestorID 写进仓库或脚本；账户密钥只走 Web **通道配置** 或本机 `.vntrader`。

首次引导管理员（仅当 SQLite 里还没有该用户时写入）默认是 **`admin` / `admin123`**。上线后立刻改掉（可用 `STABX_ADMIN_PASSWORD` 覆盖首次密码，或在后台改用户）。

### 5. 启动

部署默认（构建 Vue，**一个 uvicorn 进程**同时提供 API 和 `dist/` SPA）：

```bash
./start.sh
```

本机热更新（同一脚本内 `uvicorn --reload` + Vite，默认前端 http://127.0.0.1:5173）：

```bash
./start.sh --dev
```

已有 `dist/index.html` 时可跳过构建：`./start.sh --skip-build`。

浏览器打开 `http://<主机>:<端口>/`。默认 `STABX_HOST=0.0.0.0`、`STABX_PORT=8000`。

冒烟（不常驻 uvicorn、不打开 Qt）：

```bash
.venv/bin/python scripts/smoke_web.py
```

不要让 agent 代为启动服务，也不要启动 Qt。

## 推荐的服务器配置

进程模型是 **单 uvicorn + 进程内 MainEngine**，内存里挂实时行情/委托/持仓。按个人或小团队看板估算即可，不是高频机房。

| 场景 | CPU / 内存 / 磁盘 | 系统 | 说明 |
|---|---|---|---|
| Mac 本机开发 / 个人 SimNow | 4 核、8 GB 起（16 GB 更稳）、约 20 GB 空闲 | macOS | `.venv`、`node_modules`、编译 `vnpy_ctp` 都占盘；走 `scripts/install_macos.sh` |
| 个人或 1～2 人 VPS（SimNow 或少量实盘通道） | **2 vCPU / 4 GB / 40 GB SSD** | Linux x86_64，如 Ubuntu 22.04+ | 够跑 Web + 一两个 CTP 连接；出网能访问柜台前置 |
| 小团队同时看盘、下单 | **4 vCPU / 8 GB / 80 GB SSD** | 同上 | 仍是单进程，加用户不会水平扩 uvicorn worker |

- **本机 Mac**：适合开发与个人模拟；生产 API 限制见上一节。
- **Linux 服务器**：适合 7×24 挂着给浏览器用。必须安装 Linux 版 `vnpy_ctp`。不要用 `uvicorn --workers`。
- 磁盘主要给系统、`.venv`、`node_modules`、`dist/`、`.vntrader`（SQLite / 密钥）。P0 不强制 ClickHouse；若以后开时序库再单独加内存和盘。
- 安全：监听 `0.0.0.0` 时用防火墙或反向代理限制来源；改默认管理员密码；`.env` 不要提交。

## 业务操作流程

1. **启动**  
   仓库根目录 `./start.sh`（或 `--dev`）。浏览器打开上述地址。

2. **登录管理员**  
   首次可用文档默认账号 `admin` / `admin123`，**登录后立刻改密**。管理员才能进 **系统管理**。

3. **通道配置（SimNow 或实盘 CTP）**  
   **系统管理 → 通道配置 → 新增**，把通道分配给某个用户。表单字段包括资金账号、密码、经纪商代码、产品名称、授权编码。密码保存后加密；更新时留空表示不改密码。  
   **不要把真实密码或资金账号写进 README、`.env` 或 git。**  
   SimNow 常见默认（与后台预填一致，公开前置）：经纪商 `9999`，产品名称 `simnow_client_test`，授权编码 `0000000000000000`，柜台环境 **实盘**。  
   实盘 CTP：填期货公司给的经纪商、前置、AppID / 授权编码；柜台环境同样是实盘 API。

4. **交易时段与 7×24 前置**  
   未勾选「手动指定前置」时，SimNow **按上海时间自动换前置**，只换地址，不新建通道、不加第二套账户：
   - **交易时段**：工作日 08:45–15:30，以及夜盘 20:45–02:35（周日夜盘至周五夜盘）→ `182.254.243.31:30001` / `30011`
   - **其余时间（7×24）** → `182.254.243.31:40001` / `40011`  
   新 SimNow 账号连 7×24 可能要过若干个交易日才可用。需要固定地址时勾选「手动指定前置」。

5. **连接**  
   用该通道所属用户登录 → **资金持仓 → 账户连接 → 连接**。状态变为已连接后再做后面步骤。工作台顶栏也会显示连接状态。

6. **订阅行情**  
   **市场行情 → 行情列表**：选账户与合约 → **订阅选中**。**实时行情**看 Tick；工作台「订阅合约行情」显示已订阅快照。

7. **看盘与交易**  
   - **工作台**：持仓、行情、日志一屏  
   - **交易下单**：下单面板（确认后才发单）；**委托列表**撤单  
   - **资金持仓**：资金账户、持仓明细、成交记录  

普通用户只能看/管自己的通道与订单；管理员可配置全部用户与通道。

## 环境变量

可复制 `.env.example` 为 `.env`（已 gitignore）。常用项：

| 变量 | 默认 | 说明 |
|---|---|---|
| `STABX_HOST` | `0.0.0.0` | 监听地址 |
| `STABX_PORT` | `8000` | 监听端口 |
| `STABX_ADMIN_USERNAME` | `admin` | 首次引导管理员名 |
| `STABX_ADMIN_PASSWORD` | `admin123` | 首次引导管理员密码（立刻改掉） |
| `STABX_JWT_SECRET` | 自动生成 | JWT 密钥；缺省写入 `.vntrader/web_keys.json` |

**产品（Web）**：`core/` + `features/` + `ui/`，`./start.sh` 一键起 FastAPI + Vue。**遗留（桌面）**：根目录 `main.py` + `mystabx/`（官方 MainWindow），保留但不作为入口。

## 关键决策

| 决策项 | 结论 |
|---|---|
| 下单能力 | 完整 Web 交易台（浏览器下单/撤单） |
| 用户规模 | 局域网 / 小团队多用户 |
| 前端技术栈 | Vue 3 + Vite + TypeScript + Element Plus + ECharts |
| 后端技术栈 | FastAPI + Uvicorn，进程内 headless 启动 **vnpy**（非自研引擎） |
| 数据存储 | ClickHouse（时序/事件）+ SQLite（业务/配置）三层混合 |
| 账户模型 | 每用户独立 CTP 账户（多 gateway 实例） |
| 权限模型 | 用户级隔离 + 一个管理员标志（无复杂 RBAC） |
| 目录组织 | 功能域优先：`features/` + `core/` + `ui/` |
| 运行入口 | `./start.sh`（单进程托管 API + 构建后的 SPA）；不要用 `main.py` 当产品 |

## 设计文档

| 文档 | 内容 |
|---|---|
| [01-架构与功能规划](docs/01-架构与功能规划.md) | 总体架构、技术栈、功能模块 |
| [02-数据存储方案](docs/02-数据存储方案.md) | 三层存储、ClickHouse/SQLite 表结构、加密 |
| [03-账户隔离与权限](docs/03-账户隔离与权限.md) | 多 gateway、用户级隔离、管理员 |
| [04-WebSocket消息协议](docs/04-WebSocket消息协议.md) | 消息 envelope 与字段级 payload |
| [05-前端方案与目录结构](docs/05-前端方案与目录结构.md) | 轻量化前端、功能域目录、依赖清单 |
| [06-实施路线图](docs/06-实施路线图.md) | P0 / P1 可执行开发任务清单 |
