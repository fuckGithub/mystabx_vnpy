# Stabx Web 交易台

浏览器里用的期货交易台：Vue 网页 + FastAPI（REST / WebSocket / SSE）+ 进程内 vnpy `MainEngine`。产品入口是 Web，不是桌面 Qt。

## 仓库地址

| 平台 | 地址 | 说明 |
|---|---|---|
| Gitee | https://gitee.com/xjc621105/mystabx_vnpy | 主远程（`origin` fetch） |
| GitHub | https://github.com/fuckGithub/mystabx_vnpy | 公开开源镜像（MIT） |

## 社区与交流

欢迎通过微信群或知识星球交流 Mystabx / vnpy Web 交易台落地实践。

<p align="center">
  <img src="docs/images/mystabx-avatar.png" alt="MyStabx 项目头像" width="120" />
</p>

**微信交流群**（群聊：MyStabx期货量化交易平台）

提示：微信群二维码约 7 天有效（当前至 2026/9/24 前）；过期后会刷新，请以本页最新图片为准。

![MyStabx 微信群二维码](docs/images/mystabx-wechat-group-qr.jpg)

**知识星球**「MyStabx 期货量化交易平台」

提示：长按或扫描下方优惠券二维码，领取新人立减券（¥88，有效至 2026/12/31），进星球交流实践与联调经验。

![MyStabx 知识星球新人优惠券](docs/images/mystabx-zsxq-coupon.png)


本机 `origin` 配置了 **双 push URL**（Gitee + GitHub）：`git push origin` 会同时推送到两个平台。另有独立 remote 名 `github` 指向同一 GitHub 仓库。

> 状态：产品入口是 **Web**（Vue 3 + FastAPI + 进程内 vnpy）。启动任选其一：`python main.py`、`uv run start` 或 `./start.sh`（三者等价，均落到 `./start.sh`）。遗留 Qt 桌面仅 `python main.py --qt`。`docs/` 是设计文档；实现按 `features/ + core/ + ui/` 放在仓库根目录。

规划文档见下文「文档索引」（[docs/01](docs/01-架构与功能规划.md)–[docs/09](docs/09-CTA策略实施规划.md)）。

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

一句话概括：从「策略想法」到「实盘下单」，所有环节都在一个框架里。

覆盖范围（**当前仅国内期货 + CTP**；其余为路线图，尚未实现）：

```text
┌──────────────────────────────────────────────────────────┐
│ 数据获取 → 策略开发 → 回测验证 → 实盘交易                 │
│                                                          │
│ 【当前已支持】国内期货 · CTP（SimNow / 实盘通道）          │
│ 【规划中】A 股 · ETF 期权 · 黄金 TD · 外盘               │
│ 【规划中】XTP · Interactive Brokers · 其他 20+ 接口      │
└──────────────────────────────────────────────────────────┘
```

### 品种与接口路线图

| 类别 | 当前已支持 | 规划中（未实现） |
|---|---|---|
| 投资品种 | **国内期货** | A 股、ETF 期权、黄金 TD、外盘 |
| 交易接口 | **CTP**（SimNow 模拟 / 期货公司实盘前置） | XTP、Interactive Brokers、及其他 20+ 接口 |

将 vnpy（VeighNa）从 PySide6 桌面终端改造成 **B/S 架构的团队交易终端**：

- Python 进程内跑 vnpy 的 `MainEngine` / `EventEngine`（无界面，headless）
- 通过 **REST + WebSocket + SSE** 暴露能力（Tick 走 WS；工作台账号/资金走 SSE）
- 前端用 **Vue 3** 做完整交易台
- 支持**多用户**、**每用户独立账户**、**用户级隔离 + 管理员**

## 项目功能

把 vnpy（VeighNa）跑成 **B/S 交易终端**：一个 Python 进程里启动 headless `MainEngine` / `EventEngine`，浏览器完成登录、连柜台、看行情、下单和查资金持仓。面向本机或局域网小团队，每用户独立 CTP / SimNow 账户，用户级隔离，另有管理员。

| 菜单 | 路由 | 做什么 |
|---|---|---|
| **工作台** | `/workbench` | 首页：顶栏拆开 **账号登录**（交易 TD）与 **行情**（行情 MD）；持仓、已订阅行情、风险表、成交日志。账号/资金走 **SSE**（`/api/sse`，事件 `gateway` / `account`）；Tick 走 **WebSocket** |
| **市场行情** | `/market/ticks` → `/market/quotes` | 侧栏顺序：**实时行情**（仅已订阅）→ **行情中心**（全市场）。点行只选中看盘；**订阅 / 退订**靠行内按钮或工具栏「订阅合约」，退订走 `POST /api/market/unsubscribe`。图表（`QuoteChart`）：分时（当日内存 tick + ClickHouse 近 10 日）+ 周期 **模拟 K 线**（RQData 未对接）+ MACD 副图 |
| **交易下单** | `/trade/order`、`/trade/orders` | 下单面板（二次确认）；活动委托、撤单 |
| **策略** | `/strategy/cta` 等 | 开源 `vnpy_ctastrategy` CTA：实例生命周期（管理员写 / 用户读）、停止单、策略日志；`/strategy/backtest` 最小回测（无 bar / RQData 时结果为空） |
| **资金持仓** | `/account/gateways` 等 | **账户连接**表与管理端通道列表风格对齐：交易/行情双状态、自动连接、连接 / 测试联通 / 断开；另有资金、持仓、成交 |
| **系统管理** | `/admin/users`、`/admin/accounts` | 管理员：用户 CRUD；通道 CRUD、保存后加密、**测试联通**、**操作日志**（SQLite `channel_op_logs`，列表「日志」抽屉） |

**CTA 策略（开源 vnpy，非 Elite）**

- 策略源码放仓库根目录 `strategies/`（如演示 `DoubleMaStrategy` / `RumiStrategy`）；进程启动时 `chdir` 到项目根，`CtaEngine.init_engine()` 自动加载类。
- **管理员**在「策略 → CTA实例」创建 / 编辑 / 启停 / 移除；普通用户只读监控。WebSocket 推送 `cta_strategy` / `cta_log` / `cta_stop_order`。
- Elite 风格 shim：`core/strategy_shim.py`（`HistoryManager`、sma/wma/cross、`EliteCtaTemplate`）。多进程 / 批量移仓 / R-Cubed / GA 优化属阶段 E，本期不做。
- 回测依赖历史 bar；未配置 RQData 且本地库无数据时，回测结果为空属预期。

**通道与连接**

- 状态拆开：**交易**（`td_status` / `login_status`）与 **行情**（`md_status` / `quote_status`），UI 用 `ChannelStatusPair` 展示。
- 通道可开 **启动自动连接**（`accounts.auto_connect`）：进程启动时后台连柜；掉线后按退避自动重连（用户主动「断开」会禁止重连，直到再次连接 / 开自动连接 / 重启进程）。
- **macOS + SimNow CTP 6.7.13**：断开时不调用原生 `TdApi`/`MdApi` 的 `exit()`/`close()`（会 segfault）；重连只走 `MainEngine.connect()`。测试联通成功后也不做原生 teardown，会话可继续用。Linux 可正常 `gateway.close()`。
- 默认对接 **SimNow CTP**（生产前置 / 看穿式）；实盘 CTP 填期货公司参数即可。

**存储**

- **SQLite**（默认 `.vntrader/stabx_web.db`）：用户、通道（含 `auto_connect`）、会话、通道操作日志等；通道密钥 Fernet 加密。
- **ClickHouse** 只存 Tick：库表 `vnpy.market_tick`，默认 TTL ~10 天；进程不可用时软失败，当日分时仍走内存。根目录 `ch_schema.sql` 是早期设计稿，运行时建表以 `core/clickhouse.py` 为准。

技术栈：Vue 3 + Vite + TypeScript + Element Plus + ECharts；FastAPI + Uvicorn。Docker、RQData 历史行情仍非产品能力。

不要对 vnpy 引擎使用 `uvicorn --workers`（`MainEngine` 必须在同一进程内）。

## 已确认的关键决策

| 决策项 | 结论 |
|---|---|
| 下单能力 | 完整 Web 交易台（浏览器下单/撤单） |
| 用户规模 | 局域网 / 小团队多用户 |
| 前端技术栈 | Vue 3 + Vite + TypeScript + Element Plus + ECharts |
| 后端技术栈 | FastAPI + Uvicorn，进程内 headless 启动 **vnpy**（非自研引擎） |
| 数据存储 | SQLite（用户/通道/会话/操作日志）+ ClickHouse（仅 Tick，默认 10 天） |
| 账户模型 | 每用户独立 CTP 账户（多 gateway 实例） |
| 权限模型 | 用户级隔离 + 一个管理员标志（无复杂 RBAC） |
| 目录组织 | 功能域优先：`features/ + core/ + ui/`（不按 backend/frontend 分层） |
| 运行入口 | `python main.py` / `uv run start` / `./start.sh`（单进程托管 API + 构建后的 SPA）；Qt 仅 `--qt` |

## 文档索引

| 文档 | 内容 |
|---|---|
| [01-架构与功能规划](docs/01-架构与功能规划.md) | 总体架构、技术栈、功能模块 |
| [02-数据存储方案](docs/02-数据存储方案.md) | 设计稿：存储分层；实现以 SQLite 用户库 + CH Tick 为准 |
| [03-账户隔离与权限](docs/03-账户隔离与权限.md) | 多 gateway、用户级隔离、管理员、后端伪代码 |
| [04-WebSocket消息协议](docs/04-WebSocket消息协议.md) | 消息 envelope 与字段级 payload |
| [05-前端方案与目录结构](docs/05-前端方案与目录结构.md) | 轻量化前端、功能域目录、依赖清单 |
| [06-实施路线图](docs/06-实施路线图.md) | P0 / P1 可执行开发任务清单 |
| [07-用户服务协议与免责声明](docs/07-用户服务协议与免责声明.md) | 免责声明全文（与 `/disclaimer` 一致） |
| [08-VeighNa-Elite-CTA策略参考](docs/08-VeighNa-Elite-CTA策略参考.md) | VeighNa Elite 官方文档「CTA趋势策略」本地镜像（正文 + 28 张截图） |
| [09-CTA策略实施规划](docs/09-CTA策略实施规划.md) | CTA 策略 / 回测的实现阶段（阶段 A–E）与设计决策 |

## 与桌面端的关系

- **产品（Web）**：`core/` + `features/` + `ui/`；`python main.py` / `uv run start` / `./start.sh` 一键起 FastAPI + Vue
- **遗留（桌面）**：`mystabx/` + `python main.py --qt`（官方 MainWindow）。保留但不作为默认入口

未完成（见 [06-实施路线图](docs/06-实施路线图.md)）：RQData 历史 K 线、Docker、Web 策略应用入口。分时与 ClickHouse Tick 入库（近 10 日）已落地；周期 K 线目前是 mock。

## 目录说明

产品代码在 `core/`、`features/`、`ui/`；`mystabx/` 是遗留桌面端。下列为**本仓库实际目录**（含子目录用途）。带「本机生成、不进 git」的目录会出现在你本机资源管理器里，但不会提交。

```text
mystabx_vnpy/
├── core/                          # Web 后端内核：FastAPI 入口、vnpy 引擎、网关、库表、鉴权、WS / SSE
│   ├── main.py                    #   uvicorn 应用：挂路由、静态 dist、lifespan、/api/sse
│   ├── start.py                   #   uv / console：exec ./start.sh
│   ├── engine.py                  #   无界面      MainEngine / EventEngine
│   ├── runtime.py                 #   进程内单例：引擎、OMS、网关管理器
│   ├── gateways.py                #   多账户 CtpGateway；td/md 状态；自动连接/重连；测试联通
│   ├── channel_log.py             #   通道操作日志写入 SQLite（脱敏）
│   ├── events.py                  #   vnpy 事件转到 WebSocket；Tick 同时入内存与 CH 队列
│   ├── ws.py                      #   WebSocket：Tick / 委托 / 持仓等实时推送
│   ├── sse.py                     #   SSE：工作台账号登录与资金（gateway / account）
│   ├── db.py                      #   SQLite：users / accounts / sessions / channel_op_logs 等
│   ├── clickhouse.py              #   ClickHouse：仅 market_tick，TTL 10 天，不可用时软失败
│   ├── config.py                  #   读 .env 与本机密钥
│   ├── deps.py                    #   登录用户 / 管理员依赖
│   ├── crypto.py                  #   Fernet 加解密通道配置
│   └── serialize.py               #   REST/WS 载荷序列化
├── features/                      # 按业务域划分的 API + Vue 页面（前后端同目录）
│   ├── auth/                      #   登录、免责声明页
│   ├── workbench/                 #   工作台首页（顶栏账号登录 vs 行情）
│   │   └── components/            #     顶栏、持仓/行情/风控卡片、成交日志、日历
│   ├── market/                    #   实时行情 / 行情中心：订阅退订、分时、模拟 K + MACD
│   ├── trade/                     #   下单、委托列表
│   ├── account/                   #   账户连接、资金、持仓、成交
│   └── admin/                     #   用户管理、通道配置与操作日志（仅管理员）
├── ui/                            # Vue 壳：入口、路由、布局、全局样式（Vite root）
│   ├── main.ts / App.vue / router.ts / stores.ts / api.ts / ws.ts / sse.ts / nav.ts
│   ├── gatewayStatus.ts           #   td/md 双状态归一
│   ├── components/                #   AppLayout、ChannelStatusPair、StatusTag 等
│   │   └── auth/                  #     登录页左侧品牌栏
│   ├── styles/                    #   顶栏/侧栏、内页表格、登录、工作台 CSS
│   └── assets/brand/              #   登录与壳层用的品牌图
├── mystabx/                       # 遗留 Qt 桌面（python main.py --qt）
├── docs/                          # 文档 01–09
├── scripts/                       # 安装与冒烟
├── vendor/simnow-ctp/             # SimNow 官方 CTP 对接说明（Mac framework / Linux .so）
├── licenses/                      # vn.py / vnpy_ctp 的 MIT 许可原文
├── main.py                        # 产品入口 → start.sh；加 --qt 才起桌面
├── start.sh                       # 构建 / 托管 SPA + uvicorn
└── …（.venv / node_modules / dist / .vntrader / .deps 本机生成，gitignore）
```

子目录再展开一层：

| 路径 | 用途 |
|---|---|
| `core/` | Web 后端唯一运行时。`main.py` 提供 FastAPI；`gateways.py` 管 CTP 双腿状态与自动重连；`channel_log.py` 记操作日志；`sse.py` 推账号状态；`clickhouse.py` 只写 Tick。 |
| `features/auth/` | `LoginView.vue`、`DisclaimerView.vue`、登录 API。 |
| `features/workbench/` | 工作台；顶栏账号登录 vs 行情两路状态。 |
| `features/market/` | 合约列表、订阅/退订、分时（SimNow + CH 10d）、模拟 K + MACD（`QuoteChart`）、Tick 缓冲与入库。 |
| `features/trade/` | `OrderTicket` 下单、`TradeView` 委托、`/api/trade`。 |
| `features/account/` | 账户连接（风格对齐管理端列表）、资金持仓成交。 |
| `features/admin/` | 用户 CRUD、通道 CRUD/加密、测试联通、操作日志抽屉。 |
| `ui/` | 路由 / 导航（行情默认 `/market/ticks`）、布局、SSE/WS 客户端、`gatewayStatus`。 |
| `mystabx/` | 桌面连接框、Mac 主题、官方 MainWindow；与 Web 共用 SimNow 前置逻辑。 |
| `docs/` | `01` 架构 … `07` 免责声明全文；`08` VeighNa Elite CTA策略参考（含截图）；`09` CTA 策略实施规划。 |
| `scripts/` | `install_macos.sh` / `install_linux.sh`、`load_simnow_ctp.sh`、`smoke_*.py`。 |
| `vendor/simnow-ctp/` | 上期技术 CTP 二进制说明（Mac `.framework` / Linux `.so`，gitignore）。 |

根目录常见文件：`start.sh` 产品启动；`pyproject.toml` / `package.json` / `vite.config.ts`；`.env` / `.env.example`（`.env` 勿提交）；`NOTICE` / `THIRD_PARTY.md`；`ch_schema.sql`（早期 CH 设计稿，运行时以 `core/clickhouse.py` 为准）。

## 搭建步骤

仓库根目录操作。`python main.py` 与 `uv run start` 都会 `exec ./start.sh`。`./start.sh` 要求已有 **`.venv`**、**Node.js**、**npm**。Linux 服务器缺依赖时脚本会给出 `apt-get` 提示；不要假设 Homebrew。

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

**已知限制（macOS）**：SimNow CTP 6.7.13 上对 Md/Td 调用 `exit()`/`close()` 会导致进程崩溃，因此 Web 在 macOS 上「断开」只清本地状态并禁止自动重连，不拆原生会话；真正释放需重启进程。详见上文「通道与连接」。

**Linux**（Ubuntu/Debian 等 x86_64 服务器）：Python 封装同样用 `vnpy_ctp` 6.7.7.2 源码编译；**柜台动态库用 Linux `.so`**（vnpy_ctp 自带，或覆盖 `vendor/simnow-ctp/linux/`）。不要把 Mac `.framework` 或本机 Mac 编译产物拷到服务器，也不要跑 `install_macos.sh`。

系统依赖示例（缺了脚本会报错并提示）：

```bash
sudo apt-get install -y python3 python3-venv python3-dev build-essential git nodejs npm
```

```bash
python3 -m venv .venv
./scripts/install_linux.sh
```

该脚本会创建/使用 `.venv`，`pip`/`uv pip install -e .`，clone `vnpy_ctp`，用 `scripts/load_simnow_ctp.sh` 覆盖 Linux `.so`（若有），再安装 `vnpy_ctp`。**不会**打 Darwin 补丁。可选：从 [SimNow API 下载](https://www.simnow.com.cn/static/apiDownload.action) 解压 Linux 包到 `vendor/simnow-ctp/linux/`（或设 `STABX_SIMNOW_CTP`）。官方 CTP Linux 库仅支持 **x86_64**。

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

部署默认（构建 Vue，**一个 uvicorn 进程**同时提供 API 和 `dist/` SPA）。Linux 服务器用这条；Mac 本机开发可用 `--dev`。下列命令等价（参数原样交给 `start.sh`）：

```bash
python main.py
# 或
uv run start
# 或
./start.sh
```

本机热更新（同一脚本内 `uvicorn --reload` + Vite，默认前端 http://127.0.0.1:5173）：

```bash
python main.py --dev
# 或
uv run start --dev
# 或
./start.sh --dev
```

已有 `dist/index.html` 时可跳过构建：`./start.sh --skip-build`。遗留桌面：`python main.py --qt`。

浏览器打开 `http://<主机>:<端口>/`。默认 `STABX_HOST=0.0.0.0`、`STABX_PORT=8000`。

冒烟（不常驻 uvicorn、不打开 Qt）：

```bash
.venv/bin/python scripts/smoke_web.py
```

不要让 agent 代为启动服务，也不要启动 Qt（除非显式 `--qt`）。

## 推荐的服务器配置

进程模型是 **单 uvicorn + 进程内 MainEngine**，内存里挂实时行情/委托/持仓。按个人或小团队看板估算即可，不是高频机房。

| 场景 | CPU / 内存 / 磁盘 | 系统 | 说明 |
|---|---|---|---|
| Mac 本机开发 / 个人 SimNow | 4 核、8 GB 起（16 GB 更稳）、约 20 GB 空闲 | macOS | `.venv`、`node_modules`、编译 `vnpy_ctp` 都占盘；走 `scripts/install_macos.sh`；注意上文 Mac 断开限制 |
| 个人或 1～2 人 VPS（SimNow 或少量实盘通道） | **2 vCPU / 4 GB / 40 GB SSD** | Linux x86_64，如 Ubuntu 22.04+ | 够跑 Web + 一两个 CTP 连接；出网能访问柜台前置；走 `scripts/install_linux.sh` 再 `./start.sh` |
| 小团队同时看盘、下单 | **4 vCPU / 8 GB / 80 GB SSD** | 同上 | 仍是单进程，加用户不会水平扩 uvicorn worker |

- **本机 Mac**：适合开发与个人模拟；生产 API / 原生 teardown 限制见上文。
- **Linux 服务器**：适合 7×24 挂着给浏览器用。先 `./scripts/install_linux.sh`，再 `./start.sh`（默认生产：构建 + 单进程 uvicorn）。必须用 Linux 版 `vnpy_ctp`。不要用 `uvicorn --workers`。
- 磁盘主要给系统、`.venv`、`node_modules`、`dist/`、`.vntrader`（SQLite `stabx_web.db` / 密钥）。ClickHouse 可选：本机 `127.0.0.1:8123` 存近 10 日 Tick；没起来时服务仍可跑，历史交易日分时不可查。
- **ClickHouse 开机启动**（HTTP `8123`）：Mac Homebrew 用 `brew services start clickhouse`（或 `clickhouse-server`）；Linux 用 `sudo systemctl enable --now clickhouse-server`。本机官方单二进制也可用 LaunchAgent：`launchctl enable gui/$(id -u)/com.stabx.clickhouse`（`RunAtLoad` + `KeepAlive`）。Docker 部署则 `docker update --restart unless-stopped <容器>`。
- 安全：监听 `0.0.0.0` 时用防火墙或反向代理限制来源；改默认管理员密码；`.env` 不要提交。

## 业务操作流程

1. **启动**  
   仓库根目录 `python main.py` / `uv run start` / `./start.sh`（或 `--dev`）。浏览器打开上述地址。

2. **登录管理员**  
   首次可用文档默认账号 `admin` / `admin123`，**登录后立刻改密**。管理员才能进 **系统管理**。

3. **通道配置（SimNow 或实盘 CTP）**  
   **系统管理 → 通道配置 → 新增**，把通道分配给某个用户。表单含资金账号、密码、经纪商、产品名称、授权编码、是否启动自动连接等。密码保存后加密；更新时留空表示不改密码。  
   保存后可 **测试联通**；任意连接/断开/测试等写入 **操作日志**（行内「日志」打开抽屉）。  
   **不要把真实密码或资金账号写进 README、源码或 git。** 本机预填可写在已忽略的 `.env`（`STABX_SIMNOW_USER` / `STABX_SIMNOW_PASSWORD`）。
   SimNow 常见默认（与后台预填一致，公开前置）：经纪商 `9999`，产品名称 `simnow_client_test`，授权编码 `0000000000000000`，柜台环境 **实盘**。  
   实盘 CTP：填期货公司给的经纪商、前置、AppID / 授权编码；柜台环境同样是实盘 API。

4. **交易时段与 7×24 前置**  
   未勾选「手动指定前置」时，SimNow **按上海时间自动换前置**，只换地址，不新建通道、不加第二套账户：
   - **交易时段**：工作日 08:45–15:30，以及夜盘 20:45–02:35（周日夜盘至周五夜盘）→ `182.254.243.31:30001` / `30011`
   - **其余时间（7×24）** → `182.254.243.31:40001` / `40011`  
   新 SimNow 账号连 7×24 可能要过若干个交易日才可用。需要固定地址时勾选「手动指定前置」。

5. **连接**  
   用该通道所属用户登录 → **资金持仓 → 账户连接**（或依赖「启动自动连接」）。状态分 **交易 / 行情** 两路；变为已连接后再做后面步骤。工作台顶栏也会显示。可在此 **测试联通** / 开自动连接。

6. **订阅行情**  
   **市场行情 → 行情中心**（`/market/quotes`）：浏览全市场，用行内 **订阅** 或工具栏 **订阅合约**（点行本身只选中，不订阅）。  
   **实时行情**（`/market/ticks`，侧栏第一项）：只展示已订阅合约的盘口与分时；在行情中心可 **退订**。  
   **分时**：当日用 SimNow 内存 tick；历史交易日读 ClickHouse（默认约 10 天）。周期图是 **模拟 K 线 + MACD**，不是 RQData 实盘历史。

7. **看盘与交易**  
   - **工作台**：顶栏「账号」= 交易登录，「行情」= 行情连接；持仓、行情、日志一屏。账号/资金靠 SSE，Tick 靠 WebSocket。  
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
| `STABX_SQLITE_PATH` | `.vntrader/stabx_web.db` | 业务库：用户、通道、会话、操作日志 |
| `STABX_CLICKHOUSE_URL` | `http://127.0.0.1:8123` | Tick 库 HTTP 口；不可用时软失败 |
| `STABX_CLICKHOUSE_TICK_TTL_DAYS` | `10` | ClickHouse Tick 保留天数 |
| `STABX_METRIC_T2T_P99_MS` | `50` | `/health` → `metrics.alerts`：Tick-2-Trade p99 告警阈值（毫秒） |
| `STABX_METRIC_CH_QUEUE_WARN` | `40000` | ClickHouse 写队列深度告警 |
| `STABX_METRIC_WS_PENDING_WARN` | `2000` | WS 待 fan-out 协程数告警 |

**产品（Web）**：`core/` + `features/` + `ui/`；`python main.py` / `uv run start` / `./start.sh`。**遗留（桌面）**：`python main.py --qt` + `mystabx/`。
