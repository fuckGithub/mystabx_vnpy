# Stabx Web 交易台

浏览器里用的期货交易台：Vue 网页 + FastAPI（REST / WebSocket）+ 进程内 vnpy `MainEngine`。产品入口是 Web，不是桌面 Qt / `main.py`。

> 状态：**P0 骨架已落地**（FastAPI headless + Vue 交易台）。产品入口是 **Web**：`./start.sh`。桌面 `main.py` / PySide MainWindow 仅作遗留代码，不是默认入口。`docs/` 是设计文档；实现按 `features/ + core/ + ui/` 放在仓库根目录。

规划文档见下文「文档索引」（[docs/01](docs/01-架构与功能规划.md)–[docs/07](docs/07-用户服务协议与免责声明.md)）。

## 后端与引擎归属

本项目的**后端交易运行时是 vn.py（VeighNa）**，不是本仓库原创的交易引擎或撮合系统。

具体来说：`MainEngine`、事件引擎（`EventEngine`）、OMS（`OmsEngine`），以及委托、持仓、资金、Tick 等对象，均来自 [vnpy](https://github.com/vnpy/vnpy)；CTP 柜台网关 `CtpGateway` 来自 [vnpy_ctp](https://github.com/vnpy/vnpy_ctp)。本仓库是围绕 vnpy 的 **Web UI + FastAPI 托管层**（浏览器界面、REST / WebSocket、多用户与通道配置），**不重新实现**交易所撮合或柜台通信协议。

**许可（事实说明，不构成法律意见）**：vn.py 与 vnpy_ctp 均为 MIT 许可（Copyright (c) 2015-present, Xiaoyou Chen）。使用或分发时须保留其版权与许可声明。本项目不主张对 vnpy 或其组件的所有权。完整原文见根目录 [NOTICE](NOTICE)、[THIRD_PARTY.md](THIRD_PARTY.md) 以及 [licenses/vnpy-LICENSE](licenses/vnpy-LICENSE)、[licenses/vnpy_ctp-LICENSE](licenses/vnpy_ctp-LICENSE)。本仓库未对本包装层另行声明许可证；包装层许可不覆盖、不替代 vnpy / vnpy_ctp 的许可。

**柜台与接口**：CTP API 由上海期货信息技术有限公司（上期技术）提供，与 vnpy 项目相互独立。SimNow / CTP 账号凭证以及交易所、期货公司接口各有其使用条款，须自行遵守。

## 免责声明

本文为事实说明，**不构成法律意见**，亦不构成对 vn.py 官方或上期技术的背书。完整文本见 [docs/07-用户服务协议与免责声明.md](docs/07-用户服务协议与免责声明.md)；登录页可点击「免责声明」进入公开路由 `/disclaimer`（无需登录）。

- 本项目基于 vn.py / vnpy_ctp，是 Web UI + FastAPI 托管层，**不构成**对 vn.py 官方或其作者、上期技术及其 CTP 接口的背书或官方支持。版权与 MIT 许可原文见 [NOTICE](NOTICE)、[licenses/](licenses/)。
- 期货 / SimNow 交易有风险，可能导致本金损失。本软件**不提供投资建议**、不荐品种、不承诺收益；盈亏由使用者自行承担。
- 开源按「现状（AS IS）」提供。作者不对盈亏、服务中断、指令延迟、数据错误或丢失负责，不保证持续可用。
- CTP、SimNow、期货公司与交易所各有条款与规则，使用者须自行遵守。

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
| [07-用户服务协议与免责声明](docs/07-用户服务协议与免责声明.md) | 免责声明全文（与 `/disclaimer` 一致） |

## 与桌面端的关系

- **产品（Web）**：`core/` + `features/` + `ui/`，`./start.sh` 一键起 FastAPI + Vue
- **遗留（桌面）**：根目录 `main.py` + `mystabx/`，官方 MainWindow。保留但不作为入口，不要按这个跑产品

未完成（见 [06-实施路线图](docs/06-实施路线图.md) P1）：K 线、ClickHouse 行情入库、风控、策略/回测、Docker。

## 目录说明

产品代码在 `core/`、`features/`、`ui/`；`mystabx/` 是遗留桌面端。下列为**本仓库实际目录**（含子目录用途）。带「本机生成、不进 git」的目录会出现在你本机资源管理器里，但不会提交。

```text
mystabx_vnpy/
├── core/                          # Web 后端内核：FastAPI 入口、vnpy 引擎、网关、库表、鉴权、WS
│   ├── main.py                    #   uvicorn 应用：挂路由、静态 dist、lifespan
│   ├── engine.py                #   无界面创建 MainEngine / EventEngine
│   ├── runtime.py               #   进程内单例：引擎、OMS、网关管理器
│   ├── gateways.py              #   多账户 CtpGateway 注册 / 连接 / 测试联通
│   ├── events.py                #   vnpy 事件转到 WebSocket
│   ├── ws.py                    #   WebSocket 连接池、鉴权、主题过滤
│   ├── db.py                    #   SQLite 用户/通道表、加密字段
│   ├── config.py                #   读 .env 与本机密钥
│   ├── deps.py                  #   登录用户 / 管理员依赖
│   ├── crypto.py                #   Fernet 加解密通道配置
│   └── serialize.py             #   REST/WS 载荷序列化
├── features/                      # 按业务域划分的 API + Vue 页面（前后端同目录）
│   ├── auth/                    #   登录、免责声明页
│   ├── workbench/               #   工作台首页
│   │   └── components/           #     顶栏、持仓/行情/风控卡片、成交日志、日历
│   ├── market/                 #   行情列表、实时 Tick、订阅
│   ├── trade/                   #   下单、委托列表
│   ├── account/                 #   账户连接、资金、持仓、成交
│   └── admin/                   #   用户管理、通道配置（仅管理员）
├── ui/                            # Vue 壳：入口、路由、布局、全局样式（Vite root）
│   ├── main.ts / App.vue / router.ts / stores.ts / api.ts / ws.ts / nav.ts
│   ├── components/             #   布局 AppLayout、状态标签
│   │   └── auth/                 #     登录页左侧品牌栏
│   ├── styles/                  #   顶栏/侧栏、内页表格、登录、工作台 CSS
│   └── assets/brand/            #   登录与壳层用的品牌图
├── mystabx/                       # 遗留 Qt 桌面（不要当产品入口）
│   ├── trader.py                #   桌面 MainEngine 组装
│   ├── paths.py                 #   项目目录、.vntrader 路径
│   ├── config/                  #   SimNow 前置常量、自动切前置、桌面 App 列表
│   └── ui/                      #   连接对话框、主题、MainWindow
├── docs/                          # 设计文档 01–07（架构、存储、权限、WS、前端、路线图、免责）
├── scripts/                       # 安装与冒烟：install_macos.sh、load_simnow_ctp.sh、smoke_*.py
├── vendor/                        # 第三方非 pip 组件（本仓库只提交说明和公开 ini）
│   └── simnow-ctp/              #   SimNow 官方 Mac CTP v6.7.13 对接说明
│       ├── config/              #     交易时段 / 7×24 公开前置（无账号密码）
│       ├── docs/                #     官方 Mac API 说明摘录
│       └── macos/               #     本机 *.framework（gitignore，从官网或 simnow-ctp 复制）
├── licenses/                      # vn.py / vnpy_ctp 的 MIT 许可原文
├── .cursor/                       # Cursor 规则（可提交）
│   └── rules/                   #   提交信息、每 3 任务提交一次
├── .deps/                         # 本机：clone 的 vnpy_ctp 源码 + 覆盖后的 6.7.13 framework（gitignore）
│   └── vnpy_ctp/                #   编译用源码树
│       └── vnpy_ctp/api/        #     头文件、pybind 封装 vnctpmd/vnctptd、Mac framework
├── .venv/                         # 本机 Python 虚拟环境（gitignore）
├── node_modules/                  # 本机 npm 依赖（gitignore）
├── dist/                          # 本机 Vite 构建产物，由 start.sh 静态托管（gitignore）
├── .vntrader/                     # vnpy 运行时数据、SQLite、connect 模板（gitignore）
└── mystabx_vnpy.egg-info/         # pip install -e 生成的包元数据（gitignore）
```

子目录再展开一层：

| 路径 | 用途 |
|---|---|
| `core/` | Web 后端唯一运行时。`main.py` 提供 FastAPI；`engine.py` 拉起 vnpy；`gateways.py` 管 CTP 通道。 |
| `features/auth/` | `LoginView.vue`、`DisclaimerView.vue`、登录 API。 |
| `features/workbench/` | `index.vue` 工作台；`liveMap.ts` 把 Pinia 数据映到卡片；`mockData.ts` 日历等占位。 |
| `features/workbench/components/` | `FutureTopBar`（环境/通道）、持仓/行情/风控卡、成交日志、日历、`EnvWaveIndicator`。 |
| `features/market/` | 合约搜索订阅、Tick 页与 `/api/market`。 |
| `features/trade/` | `OrderTicket` 下单、`TradeView` 委托、`/api/trade`。 |
| `features/account/` | 网关连接/断开、资金持仓成交列表。 |
| `features/admin/` | 用户 CRUD、通道保存加密、测试联通。 |
| `ui/components/` | `AppLayout.vue` 全宽顶栏 + 模块侧栏；`StatusTag.vue`。 |
| `ui/components/auth/` | 登录左侧品牌与 vn.py 页脚署名。 |
| `ui/styles/` | `layout.css` 顶栏侧栏；`pages.css` 列表/弹窗；`equilibrix-dashboard.css` 工作台；`auth-page.css` 登录。 |
| `ui/assets/brand/` | 品牌资源。 |
| `mystabx/config/` | `simnow.py` 前置与自动切换（Web 与桌面共用）；`apps.py` 桌面 CTA 等。 |
| `mystabx/ui/` | 桌面连接框、Mac 主题、官方 MainWindow 子类。 |
| `docs/` | `01` 架构 … `07` 免责声明全文。 |
| `scripts/` | `install_macos.sh` 装依赖并编译 CTP；`load_simnow_ctp.sh` 覆盖 6.7.13；`smoke_web.py` / `smoke_imports.py` / `smoke_qt.py`。 |
| `vendor/simnow-ctp/macos/` | 上期技术 CTP 二进制。Apple framework 内部还有 `Headers/`、`Resources/`、`Versions/A/`，属官方 SDK 布局，不要手改。 |
| `.deps/vnpy_ctp/vnpy_ctp/api/vnctp/` | `vnctpmd` / `vnctptd` C++ 绑定源码。 |
| `.deps/vnpy_ctp/vnpy_ctp/gateway/` | `CtpGateway` Python 封装。 |
| `.cursor/rules/` | Agent 提交规范。 |

根目录常见文件（不是目录，便于对照资源管理器）：`start.sh` 产品启动；`pyproject.toml` / `package.json` / `vite.config.ts` 构建；`.env` / `.env.example` 本机配置（`.env` 勿提交）；`NOTICE` / `THIRD_PARTY.md` 第三方版权；`ch_schema.sql` ClickHouse 表。

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

**macOS**：Python 封装用 `vnpy_ctp` 6.7.7.2 源码编译；**柜台动态库与头文件用 SimNow 官方 Mac CTP v6.7.13**（测评/生产合并包，本项目 `Create*` 固定生产模式，连看穿式前置）。不要对 `vnpy_ctp` 使用 `pip install -e`。

先准备 SimNow 组件（二选一）：

- 本机已有 `/Users/x/Documents/Stabx/simnow-ctp/production/api/macos/*.framework`（默认搜索路径）
- 或从 [SimNow API 下载](https://www.simnow.com.cn/static/apiDownload.action) 解压到 `vendor/simnow-ctp/macos/`（或设 `STABX_SIMNOW_CTP`）

```bash
# 需先有 .venv，以及本机 uv、Homebrew ta-lib（脚本读 /opt/homebrew）
./scripts/install_macos.sh
```

该脚本会 `uv pip install -e .`，clone `vnpy_ctp` 到 `.deps/vnpy_ctp`，用 `scripts/load_simnow_ctp.sh` 覆盖 6.7.13 framework/头文件，再 `uv pip install .deps/vnpy_ctp`。CTP 二进制版权属上期技术，不进 git（见 `vendor/simnow-ctp/README.md`）。

通道里「柜台环境」固定为「实盘」；SimNow 走生产前置。

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
   **不要把真实密码或资金账号写进 README、源码或 git。** 本机预填可写在已忽略的 `.env`（`STABX_SIMNOW_USER` / `STABX_SIMNOW_PASSWORD`）。
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
| `STABX_SIMNOW_USER` | （空） | 本机新建通道预填资金账号，只写 `.env` |
| `STABX_SIMNOW_PASSWORD` | （空） | 本机新建通道预填密码，只写 `.env`，勿提交 |
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
| [07-用户服务协议与免责声明](docs/07-用户服务协议与免责声明.md) | 免责声明全文（与 `/disclaimer` 一致） |
