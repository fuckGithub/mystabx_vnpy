# 09 CTA 策略实施规划

> 关联文档：[08-VeighNa-Elite-CTA策略参考](08-VeighNa-Elite-CTA策略参考.md)（功能参考）、[06-实施路线图](06-实施路线图.md)（P1-10 策略管理 / P1-11 回测）、[01-架构与功能规划](01-架构与功能规划.md)（F 策略管理 / G 回测）。

## 1. 背景与结论

08 文档描述的是 **VeighNa Elite（商业闭源版）** 的 CTA 策略模块；本项目后端运行时是 **开源 vn.py 4.0**。经核对，08 所列能力约 80% 在开源版中已有对应实现（`vnpy_ctastrategy` 1.4.1、`vnpy_ctabacktester` 1.3.0 已随依赖安装），仅少数需自研或后置。

**结论：先做「CTA 生命周期 Web 化」，再做「Elite 风格 shim 层」，最后再评估多进程 / 批量移仓等重活。**

## 2. 能力对照表（Elite → 开源 vnpy）

| 08 文档 Elite 能力 | 开源 vnpy 对应 | 结论 |
|---|---|---|
| `CtaTemplate`（兼容） | `vnpy_ctastrategy.CtaTemplate` | ✅ 直接有 |
| `EliteTargetTemplate`（set_target / get_target / execute_trading + buy/sell/short/cover） | `TargetPosTemplate`（`set_target_pos` / `get_target_pos` / `trade` / `cancel_all`） | ✅ 基本 1:1 |
| `get_engine_type` / `load_bar` / `load_tick` / `put_event` / `write_log` / `send_email` / `sync_data` / 本地停止单 `stop=True` | 全都有 | ✅ 直接有 |
| `EliteCtaTemplate`（`on_history` + `HistoryManager` + 内置指标 `sma/wma/cross_over/cross_below`） | 无，对应方案是 `BarGenerator` + `ArrayManager` | ⚠️ 需自研 shim 层 |
| 理论持仓管理器（`calculate_volume` / `bar_since_entry` / `long_average_price` / `short_average_price`） | 无 | ⚠️ 需自研 |
| `get_account` / `get_account_pos` | 开源模板无（引擎侧可补） | ⚠️ 易补 |
| 多进程架构（每策略独立进程） | 单进程 `CtaEngine`（受 GIL） | ❌ 重活，后置 / 或买 Elite |
| 批量并发移仓助手 + 价差算法 | 开源仅「单合约移仓助手」 | ❌ 重活 |
| R-Cubed 稳健优化指标 | 无 | ⚠️ 回测阶段自研 |

## 3. 设计决策

### D1 策略文件管理

- 初期：策略 `.py` 文件放服务器 `strategies/` 目录，由管理员维护（git 拉取 / 手动放置）；`init_engine()` 时 `load_strategy_class()` 加载；Web 只做**实例管理**，不做文件上传。
- 进阶：文件上传 + `importlib.reload` 热加载（风险：老实例持旧代码引用，需谨慎）。

### D2 单引擎 vs 多用户隔离

- `CtaEngine` 是**进程内单例**，策略实例是全局的，不能像资金 / 持仓那样按用户隔离。
- 方案：策略由**管理员统一创建 / 启停**，普通用户只读监控；策略通过 `setting["gateway_name"]` 绑定到具体账户（对应 08「多账户支持」基础版）。

### D3 回测 / 实盘同构

- `vnpy_ctabacktester.BacktesterEngine` 复用同一套策略类（对应 08「一套代码跑回测 + 实盘」）。
- **前置依赖**：历史 bar 数据（06 的 P1-2：DataManager + RQData / 本地 CSV 入库），否则回测无数据。

### D4 Elite 专属能力边界

- **自研（阶段 C）**：`HistoryManager` + 内置指标函数 + 理论持仓管理器（价值高、成本可控）。
- **自研（阶段 E，本期）**：多进程、批量并发移仓、R-Cubed（工程量大，选型与任务见 7.5 的 D5）。

## 4. 分阶段实现步骤

### 阶段 A — CTA 生命周期闭环（06 P1-10，最高优先）

**后端（`core/` + 新 `features/strategy/`）**

| 步骤 | 内容 | 落点 |
|---|---|---|
| A1 | `main_engine.add_app(CtaStrategyApp)` 拿到 `cta_engine` 单例 | `core/runtime.py` / `core/engine.py` |
| A2 | 事件桥接：`EVENT_CTA_STRATEGY` / `EVENT_CTA_LOG` / `EVENT_CTA_STOPORDER` → WS | `core/events.py`、`core/ws.py` |
| A3 | 策略类加载与枚举：`init_engine()`、`get_strategy_class_names()` | `features/strategy/engine.py` |
| A4 | 实例管理 REST：`add/remove/edit_strategy`、`init/start/stop_strategy`、`init/start/stop_all_strategies` | `features/strategy/api.py` |
| A5 | 序列化 `CtaStrategyData` → JSON（名称 / 合约 / 参数 / 变量 / inited / trading / gateway） | `core/serialize.py` |
| A6 | 参数表单 schema：`get_class_parameters()` 反推策略参数及默认值 | `features/strategy/api.py` |

**前端（新 `features/strategy/`）**

- 策略类下拉 →「添加策略」参数表单 → 实例表格（参数 / 变量 / inited / trading）→ 操作按钮（初始化 / 启动 / 停止 / 编辑 / 移除）+ 全部初始化 / 启动 / 停止。
- WS 实时刷新状态 + 策略日志面板（对应 08「运行日志」「状态跟踪」）。

**验收**：浏览器里从「选策略类 → 建实例 → 初始化（load_bar）→ 启动（trading=True）→ 停策略撤销委托」全程闭环。

### 阶段 B — 回测（06 P1-11）

- 挂 `BacktesterApp` → `BacktesterEngine`；REST 设参数（合约 / 周期 / 区间 / 费率滑点 / 资金）→ `start_backtesting` → 进度 + 结果。
- 结果可视化（ECharts）：资金曲线、回撤、收益、胜率、逐笔明细。
- **依赖**：先完成 P1-2（bar 入库）。

### 阶段 C — Elite 风格 shim 层（自研）

新建独立小库（如 `core/strategy_shim.py` 或独立包），不污染 vnpy 核心：

1. **`HistoryManager`**：定长 deque 存 K 线 + `close/open/high/low/volume/turnover/open_interest` 数组 + `bar_count()` + `to_dataframe()`（08 第 928 行起）。
2. **内置指标函数**：`sma` / `wma` / `cross_over` / `cross_below`（numpy 实现）。
3. **理论持仓管理器**：`calculate_volume` / `bar_since_entry` / `long_average_price` / `short_average_price`（08 第 567–597 行）。
4. 把 `on_history(hm)` 接到 `TargetPosTemplate.on_bar`（K 线合成后喂 HistoryManager 再回调）。

目标：用户既可用开源标准 `on_bar`，也可用接近 Elite 的 `on_history` 写法，迁移成本最低。

### 阶段 D — 停止单 + 批量操作 + 多账户（低成本补齐）

- 停止单监控组件（`EVENT_CTA_STOPORDER`，对应 08「停止单」），`stop=True` 已原生支持。
- 批量初始化 / 启动 / 停止（对应 08「批量操作」）：纯 Web 层按钮，调 `*_all_strategies`。
- 多账户：实例参数里的 `gateway_name` 下拉（对应 08「多账户支持」基础版，最多 5 个）。

### 阶段 E — 重活（本期直接实现）

- 多进程架构：每个策略实例独立子进程，主进程聚合状态 / 日志 / 委托（对标 Elite 核心卖点，工程量大、风险高）。
- 批量并发移仓 + 价差算法、R-Cubed 稳健指标、参数优化。
- 详细任务、进程模型、IPC 协议与 REST / WS 契约见 [7.5](#75-阶段-e--重活本期直接实现)。

## 5. 实施策略与演示策略

推进顺序与风险控制：

1. 先打通「实例生命周期」主线（阶段 A），复用 `gateways.py` / `events.py` / `ws.py` 的成熟模式。
2. 默认模板用 `TargetPosTemplate`（而非裸 `CtaTemplate`）：目标仓位语义与 08 的 `EliteTargetTemplate` 几乎一致。
3. 回测放 shim 层之前：回测依赖数据链路（P1-2），shim 层依赖回测验证，顺序不能反。
4. shim 层做成独立、可测试的小库，单测覆盖指标函数与 HistoryManager。
5. 先写 1–2 个演示策略作为 Web「策略类下拉」的默认选项，验证整条链路。

**建议先实现的演示策略**

- **双均线金叉死叉**（`TargetPosTemplate` + `on_bar`，用 `ArrayManager` + talib / vnpy 自带指标）：零 shim 依赖，可立刻跑通阶段 A 全链路。
- **RumiStrategy**（08 文档示例：均线偏差 + 止损 + 持仓周期）：需先完成 shim 的 `on_history` / `calculate_volume`，作为阶段 C 的验收用例。

## 6. 风险与注意点

- `CtaEngine` 单例 + 单进程：策略并发上来受 GIL 限制（开源版每进程建议 20–50 个策略，08 亦提及），属阶段 E 才解决的问题。
- **别对 vnpy 引擎用 `uvicorn --workers`**：CTA 引擎必须在同一进程（README 已强调）。
- 策略初始化依赖历史数据：接口 / 数据服务拿不到 bar 时 `load_bar` 返回空，UI 需明确提示（08 第 638 行 `use_database` 说明）。
- 停止策略会 `cancel_all`（撤掉该策略所有活动委托）并 `sync_data` 缓存，Web 层要同步更新「活动委托」视图，避免「幽灵委托」。

## 7. 原子任务清单（含 REST 路由 / WS 事件 / 前端交互）

> 约定：REST 走 `APIRouter` + `Depends(current_user)`（参考 `features/trade/api.py`）；WS 用 `envelope(type, data)`（`{type, ts, data}`，参考 `core/serialize.py`）；权限用 `visible_gateways(user)`；枚举/状态输出沿用 `enum_out`。CTA / 回测引擎是进程内单例，**写操作（创建 / 启停 / 编辑 / 移除）默认仅管理员**，普通用户只读。已核对本仓库 `.venv`：`vnpy_ctastrategy` 1.4.1（APP_NAME=`CtaStrategy`）、`vnpy_ctabacktester` 1.3.0（APP_NAME=`CtaBacktester`）。

### 7.0 公共前置（阶段 A / B 共用）

| ID | 任务 | 文件 | 关键点 |
|---|---|---|---|
| S0 | 新建策略目录 | `strategies/`（项目根） | 放 `.py` 策略；`CtaEngine.init_engine()` 默认从运行目录 `strategies/` 加载 |
| S1 | 挂载两个 App | `core/engine.py` | `main_engine.add_app(CtaStrategyApp)`、`main_engine.add_app(CtaBacktesterApp)` |
| S2 | Runtime 暴露引擎 | `core/runtime.py` | 加 `cta` / `backtester` 属性 → `me.get_engine("CtaStrategy")` / `me.get_engine("CtaBacktester")` |
| S3 | 初始化引擎 | `core/main.py` lifespan | `runtime.cta.init_engine()`、`runtime.backtester.init_engine()`（加载策略类） |
| S4 | 事件桥接 | `core/events.py` | 注册 CTA / 回测事件 → `publish_threadsafe(envelope(...))` |
| S5 | 序列化 | `core/serialize.py` | 加 `cta_strategy_payload` / `cta_stop_order_payload` / `backtester_log_payload` / `backtester_finished_payload`；CTA 日志复用 `log_payload` + `strategy_name` |

**WS 事件 → 前端 msg type 映射**

| vnpy 事件常量 | WS msg type | 数据 |
|---|---|---|
| `EVENT_CTA_STRATEGY`（"eCtaStrategy"） | `cta_strategy` | `strategy.get_data()` + `inited` / `trading` / `pos` / `gateway_name` |
| `EVENT_CTA_LOG`（"eCtaLog"） | `cta_log` | `log_payload` + `strategy_name` |
| `EVENT_CTA_STOPORDER`（"eCtaStopOrder"） | `cta_stop_order` | 见 7.4 停止单字段 |
| `EVENT_BACKTESTER_LOG`（"eBacktesterLog"） | `backtester_log` | `log_payload` |
| `EVENT_BACKTESTER_BACKTESTING_FINISHED` | `backtester_finished` | 空数据（前端收到后主动拉结果） |
| `EVENT_BACKTESTER_OPTIMIZATION_FINISHED` | `backtester_optimization_finished` | 空数据 |

**WS 订阅 topics 追加**（`ui/ws.ts` auth_ok 后的 subscribe）：`cta_strategy`、`cta_log`、`cta_stop_order`、`backtester_log`、`backtester_finished`。

### 7.1 阶段 A — CTA 生命周期闭环

**REST 路由（`features/strategy/api.py`，`APIRouter(tags=["cta"])`）**

| 方法 | 路径 | 请求体 | 响应 | 引擎调用 |
|---|---|---|---|---|
| GET | `/api/cta/strategies` | — | `[{class_name, display_name, parameters, file_name, file_path, module}]` | `get_all_strategy_class_names()` + `get_strategy_class_parameters(name)` + 源文件元数据 |
| POST | `/api/cta/strategies/reload` | — | 同上列表 | 管理员：`load_strategy_class()` 重扫 `strategies/` 并 `importlib.reload` |
| GET | `/api/cta/instances` | — | `[cta_strategy_payload]` | 遍历 `engine.strategies` |
| POST | `/api/cta/instances` | `{class_name, strategy_name, vt_symbol, setting}` | `{ok, strategy_name}` | `add_strategy(class_name, strategy_name, vt_symbol, setting)` |
| POST | `/api/cta/instances/{name}/init` | — | `{ok}` | `init_strategy(name)`（返回 Future，异步完成） |
| POST | `/api/cta/instances/{name}/start` | — | `{ok}` | `start_strategy(name)` |
| POST | `/api/cta/instances/{name}/stop` | — | `{ok}` | `stop_strategy(name)` |
| PATCH | `/api/cta/instances/{name}` | `{setting}` | `{ok}` | `edit_strategy(name, setting)` |
| DELETE | `/api/cta/instances/{name}` | — | `{ok}` | `remove_strategy(name)` |
| POST | `/api/cta/instances/init-all` | — | `{ok}` | `init_all_strategies()` |
| POST | `/api/cta/instances/start-all` | — | `{ok}` | `start_all_strategies()` |
| POST | `/api/cta/instances/stop-all` | — | `{ok}` | `stop_all_strategies()` |
| GET | `/api/cta/stop-orders` | — | `[cta_stop_order_payload]` | `engine.active_stop_orders` |

**任务拆分**

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| A1 | `cta_strategy_payload(strategy)`：字段 `strategy_name / vt_symbol / class_name / author / parameters / variables / inited / trading / pos / gateway_name`；`inited/trading/pos` 从 `strategy` 实例取（`get_data()` 不含），`gateway_name` 从 `setting` 或实例取 | `core/serialize.py` | 单测：构造一个策略实例，序列化字段齐全 |
| A2 | 事件绑定：`on_cta_strategy` / `on_cta_log` / `on_cta_stop_order` → `publish_threadsafe` | `core/events.py` | 启动策略后 WS 能收到 `cta_strategy` 状态 |
| A3 | 引擎单例暴露：`runtime.cta` 属性 + lifespan 里 `init_engine()` | `core/runtime.py`、`core/main.py` | `/health` 能报 CTA 引擎已就绪 |
| A4 | 只读接口：GET strategies / instances / stop-orders | `features/strategy/api.py` | curl 返回策略类列表 + 实例列表 |
| A5 | 写接口：POST instances + init/start/stop + PATCH + DELETE + \*_all，加 `is_admin` 校验（复用 `core/deps`） | `features/strategy/api.py` | 管理员可建/启停/移除；普通用户 403 |
| A6 | `features/strategy` 路由注册进 `core/main.py`（`app.include_router`） | `core/main.py` | OpenAPI `/docs` 出现 cta 接口 |
| A7 | 前端 store：`useStrategyStore`（`instances` / `stopOrders` / `logs`，`upsertStrategy` / `upsertLog` / `upsertStopOrder`） | `ui/stores.ts` | WS 消息能增量更新 store |
| A8 | WS 分发：`ui/ws.ts` 的 `dispatch` 增加 `cta_strategy` / `cta_log` / `cta_stop_order` 分支 | `ui/ws.ts` | 控制台可见消息进 store |
| A9 | 路由 + 导航：`/strategy/:section`（instances / logs / stoporders）+ topMenu「策略交易」+ sidebar | `ui/router.ts`、`ui/nav.ts` | 顶栏出现「策略交易」，侧栏三入口 |
| A10 | 页面：策略实例表格（参数 / 变量 / inited / trading）+ 操作按钮（初始化 / 启动 / 停止 / 编辑 / 移除）+ 批量按钮 + 添加策略弹窗（class_name 下拉 + 参数表单由 `get_strategy_class_parameters` 生成） | `features/strategy/StrategyView.vue` | 浏览器完成建实例 → 初始化 → 启动 → 停止闭环 |
| A11 | 日志面板 + 停止单面板（复用现有 log 展示风格） | `features/strategy/` | 策略日志 / 停止单实时刷新 |

**验收**：管理员在浏览器从「选策略类 → 建实例（填参数）→ 初始化 → 启动（trading=True）→ 停止（撤单）」全程闭环，状态实时刷新；普通用户只读。

### 7.2 阶段 B — 回测

**REST 路由（`features/backtest/api.py`，`APIRouter(tags=["backtest"])`）**

| 方法 | 路径 | 请求体 | 响应 | 引擎调用 |
|---|---|---|---|---|
| GET | `/api/backtest/strategies` | — | `[{class_name, parameters:{name:default}}]` | `get_strategy_class_names()` + `get_default_setting(name)` |
| POST | `/api/backtest/run` | `{class_name, vt_symbol, interval, start, end, rate, slippage, size, pricetick, capital, setting}` | `{ok}` | `start_backtesting(...)`（后台线程跑） |
| GET | `/api/backtest/result` | — | `{statistics, df, daily_results}` | `get_result_statistics()` + `get_result_df()` + `get_all_daily_results()` |
| GET | `/api/backtest/trades` | — | `[trade_payload]` | `get_all_trades()` |

**回测请求体字段**（对应 `start_backtesting` 签名）：`interval` 用 `"1m"` 等字符串（`Interval` 枚举）；`start/end` 用 ISO 日期；`rate/slippage/size/pricetick/capital` 为数值；`setting` 为策略参数覆盖。

**任务拆分**

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| B1 | `runtime.backtester` 属性 + lifespan `init_engine()` | `core/runtime.py`、`core/main.py` | 引擎就绪 |
| B2 | 事件绑定：`EVENT_BACKTESTER_LOG/FINISHED/OPTIMIZATION_FINISHED` → WS | `core/events.py` | 回测结束前端收到 `backtester_finished` |
| B3 | 回测 REST 接口（上表 4 个） | `features/backtest/api.py` | curl 能跑回测并拉结果 |
| B4 | 前端 `useBacktestStore` + `BacktestView.vue`：参数表单 → 运行 → 进度（用 `backtester_log`）→ 结果页 | `ui/stores.ts`、`features/backtest/` | 浏览器跑完回测看到统计 + 资金曲线 |
| B5 | 结果可视化：ECharts 资金曲线 / 回撤 / 每日盈亏（数据来自 `get_result_df()`） | `features/backtest/` | 图能渲染 |
| B6 | 前置依赖：bar 数据入库（06 的 P1-2） | `core/clickhouse.py` 或 DataManager | 回测能取到历史 bar |

**验收**：选策略 + 参数 → 跑回测 → 看统计（收益率 / 回撤 / 夏普 / 胜率）与资金曲线。

### 7.3 阶段 C — Elite 风格 shim 层（自研，独立小库）

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| C1 | `HistoryManager`：定长 deque 存 K 线，属性 `datetime/open/high/low/close/volume/turnover/open_interest` 返回 numpy 数组；方法 `bar_count()`、`to_dataframe()` | `core/strategy_shim.py` | 单测：喂 100 根 bar，`close[-1]` 正确，`to_dataframe()` 列齐全 |
| C2 | 指标函数：`sma / wma / cross_over / cross_below`（numpy，返回 ndarray / bool） | `core/strategy_shim.py` | 单测：与 talib 对照（若 talib 可用） |
| C3 | 理论持仓管理器：`calculate_volume(risk_capital, risk_window, max_volume, min_volume)` / `bar_since_entry()` / `long_average_price()` / `short_average_price()` | `core/strategy_shim.py` | 单测：模拟开平仓后持仓周期 / 均价正确 |
| C4 | `EliteCtaTemplate` 基类：继承 `TargetPosTemplate`，把 `on_bar` 转喂 `HistoryManager` 后回调 `on_history(hm)` | `core/strategy_shim.py` | 用 RumiStrategy 跑回测，`on_history` 被调用 |
| C5 | 内置指标接入 `ArrayManager` 可选项：支持在 shim 里直接 `hm.close` 计算，兼容 `on_bar` 老写法 | `core/strategy_shim.py` | 双均线策略同时用两种写法可跑 |

**验收**：把 08 的 RumiStrategy 翻译到 shim 版，能在阶段 B 回测跑通，结果与 `on_bar` 版本一致。

### 7.4 阶段 D — 停止单 + 批量 + 多账户

**停止单字段（`cta_stop_order_payload`）**：`stop_orderid / vt_symbol / direction / offset / price / volume / status(WAITING|TRIGGERED|CANCELLED) / strategy_name / vt_orderids / datetime`。

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| D1 | `cta_stop_order_payload` + 事件绑定（已在 A2 覆盖，此处补字段完整） | `core/serialize.py` | 发出 `stop=True` 委托后 WS 出现 `cta_stop_order` |
| D2 | 停止单监控组件（表格 + 状态标签，对应 08「停止单」） | `features/strategy/` | 等待中 / 已触发 / 已撤销三态可见 |
| D3 | 批量按钮：初始化 / 启动 / 停止全部（调 `*_all` 接口，二次确认） | `features/strategy/` | 一次操作全部实例 |
| D4 | 多账户：实例表单里 `gateway_name` 下拉（复用 `/api/gateways` 的可见账户列表）；策略实例绑定账户 | `features/strategy/` | 不同实例可指定不同账户，委托落到对应 gateway |

**验收**：停止单三态正确；批量启停可用；实例绑定 gateway 后委托归属正确。

### 7.5 阶段 E — 重活（本期直接实现）

> 阶段 E 四块：E1 多进程、E2 批量移仓、E3 R-Cubed、E4 参数优化。已核对 `.venv`：`vnpy_algotrading`（APP_NAME=`AlgoTrading`，含 `AlgoEngine` / `AlgoTemplate`）、`vnpy_ctabacktester.start_optimization(...)`（含 `OptimizationSetting`、`use_ga`、`max_workers`）、开源 `vnpy_ctastrategy/ui/rollover.py`（单合约移仓参考实现）。

#### D5 设计决策：多进程架构选型（E1 前置）

| 方案 | 说明 | 结论 |
|---|---|---|
| A：主进程管连接/OMS + 子进程管策略计算 | 主进程：gateway(td/md) + OMS + Dispatcher；子进程（worker）：每策略实例一个，收行情→算信号→回传「目标仓位」 | ✅ **推荐**（同 Elite「Chrome 多进程」思路） |
| B：每策略实例独立进程 + 独立 gateway | 每子进程自带 MainEngine + gateway + CtaEngine | ❌ 每进程独立连柜台，CTP 连接数 / 认证受限 |
| C：仅回测 / 优化多进程 | `start_optimization(max_workers)` 内部已多进程 | 仅覆盖计算密集，不解决实盘 GIL |

**E1 采用方案 A**：worker 只算信号、回报「目标仓位」，下单仍由主进程 OMS 执行，复用阶段 C 的 `execute_trading` / `cancel_all` 语义。

#### E1 多进程架构

**进程模型**

```text
主进程(controller)                        子进程(worker) × N
┌────────────────────────────┐          ┌────────────────────────────┐
│ gateway td/md + OMS        │  行情     │ StrategyWorker             │
│ CtaDispatcher ──Tick/Bar───┼─────────▶ │ 策略实例(计算)             │
│ 目标仓位执行(OMS下单)        │◀──目标仓位─┼─ on_tick/on_bar 算信号    │
│ 状态/日志聚合 → WS          │◀──状态/日志┼─ 回传 target_pos          │
└────────────────────────────┘          └────────────────────────────┘
        IPC: multiprocessing.Pipe（双向，pickle 序列化）
```

**IPC 协议（`core/mpcta/protocol.py`，dataclass + pickle）**

| 消息 | 方向 | 字段 |
|---|---|---|
| `ControlMsg` | 主→worker | `action(init/start/stop/remove)` + `strategy_class` / `strategy_name` / `vt_symbol` / `setting` / `strategies_path` |
| `BarMsg` | 主→worker | `bar: BarData`（**init 回放历史**） |
| `TickMsg` | 主→worker | `tick: TickData`（**实盘行情**） |
| `TargetMsg` | worker→主 | `strategy_name` + `target_pos: int` + `price_add: float` |
| `StatusMsg` | worker→主 | `strategy_name` + `inited` / `trading` / `pos` / `variables` |
| `LogMsg` | worker→主 | `strategy_name` + `msg` |

**数据流约定**：`init` 时主进程查历史 bar → 按序发 `BarMsg` → worker 回放喂 `on_bar` → 回 `StatusMsg(inited=True)`；实盘时主进程订阅 tick → 发 `TickMsg` → worker `on_tick`（策略内部 BarGenerator 合成 K 线，与 vnpy 标准行为一致）。

**原子任务**

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| E1-1 | IPC 协议 dataclass（上表） | `core/mpcta/protocol.py` | pickle 往返单测通过 |
| E1-2 | `StrategyWorker(Process)`：`run()` 里按 `strategies_path` 注入 `sys.path` 并加载策略类；收 `BarMsg/TickMsg` 喂策略；策略状态变化回 `StatusMsg`；`write_log` 钩子转 `LogMsg`；目标变化回 `TargetMsg` | `core/mpcta/worker.py` | 单测：主进程起 worker，喂 bar，收 Target/Status |
| E1-3 | `CtaDispatcher`：主进程维护 `vt_symbol→[worker]` 映射；init 回放 bar、实盘路由 tick；收 `TargetMsg` → 调 OMS（`cancel_all` + 按目标仓差下单） | `core/mpcta/dispatcher.py` | 多实例并发收行情、各自回报目标、主进程正确下单 |
| E1-4 | `WorkerManager`：spawn / start / stop / remove worker；`is_alive()` + 心跳超时检测；崩溃告警 + 自动重启（可配） | `core/mpcta/manager.py` | kill 一个 worker 能检测并告警 |
| E1-5 | 状态/日志聚合：`StatusMsg` / `LogMsg` → `publish_threadsafe(envelope("cta_strategy"/"cta_log", ...))` | `core/mpcta/manager.py` 或 `core/events.py` | WS 可见 worker 状态 |
| E1-6 | REST 改造：阶段 A 的 `/api/cta/instances/*` 从直连 `CtaEngine` 改为走 `WorkerManager`（spawn/start/stop/remove） | `features/strategy/api.py` | 建实例=spawn worker；移除=kill worker |
| E1-7 | 前端实例表格加「worker 状态」列（running / crashed / restarting）+ 崩溃告警 | `features/strategy/` | 崩溃可见 + 可重启 |
| E1-8 | 压测验收 | — | 单机 >50 个策略实例，Tick-2-Trade 延时不再被 GIL 拖累 |

#### E2 批量并发移仓 + 价差算法

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| E2-1 | 挂载 `AlgoTradingApp`，`runtime.algo = me.get_engine("AlgoTrading")` | `core/engine.py`、`core/runtime.py` | 引擎就绪 |
| E2-2 | 自研 `RolloverAlgo(AlgoTemplate)`：订阅新旧合约行情；价差 = 新−旧；按价差目标挂单；`max_order_volume` 单笔上限、`price_add` 超价；`on_trade` / `on_timer` 驱动；完成 / 停止回调 | `core/algos/rollover_algo.py` | 单合约价差移仓跑通 |
| E2-3 | 移仓引擎（headless）：对标 08「移仓助手」——批量并发（每合约一个 RolloverAlgo）、参数校验（新旧合约不能一样 / 品种一致）、执行前确认 | `core/rollover.py` | 多合约并发移仓 |
| E2-4 | REST：`POST /api/rollover/run`（`{tasks:[{strategy_name, old_symbol, new_symbol, long_volume, short_volume, max_order_volume, price_add}]}`）、`GET /api/rollover/tasks`、`POST /api/rollover/tasks/{id}/stop`、`POST /api/rollover/stop-all` | `features/strategy/rollover.py` | curl 能批量发起 / 停止移仓 |
| E2-5 | WS：复用 `EVENT_ALGO_UPDATE` / `EVENT_ALGO_LOG`（常量值见 `vnpy_algotrading/engine.py`）→ `algo_update` / `algo_log`；移仓任务状态 → `rollover_status` | `core/events.py`、`core/serialize.py` | 前端实时看移仓进度 |
| E2-6 | 移仓助手页面：配置表格 + 批量执行 + 算法监控 + 单任务停止 | `features/strategy/` | 浏览器批量移仓、可中途停止 |
| E2-7 | 验收：移仓完成后策略 `vt_symbol` 已切换、老仓平掉、新仓建好、有完整委托 / 成交 | — | 与 08「移仓效果」一致 |

#### E3 R-Cubed 稳健指标

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| E3-1 | 实现 R-Cubed：输入每日收益序列，输出 R³ 及中间量（RAR=年化收益 / 最大回撤、最长回撤期、收益分布稳健系数）。公式以 Curtis Faith《海龟交易法则》 / vn.py 社区实现为准，先落一版可复算 | `core/metrics.py` | 单测：构造全赢 / 全亏 / 震荡三组序列，结果有区分度 |
| E3-2 | 接入回测统计：`/api/backtest/result` 的 `statistics` 追加 `r_cubed` | `features/backtest/api.py` | 回测结果含 R³ |
| E3-3 | 接入优化目标：`OptimizationSetting.set_target("r_cubed")`（需在回测统计 key 里注册 `r_cubed`，查证 `vnpy_ctabacktester` 是否支持自定义 target；不支持则用可用的稳健目标替代） | `features/backtest/api.py` | 优化能按稳健性选参 |
| E3-4 | 前端结果页展示 R³，与夏普 / 回撤并列 | `features/backtest/` | 结果卡片可见 R³ |

#### E4 参数优化

| ID | 任务 | 文件 | 验收 |
|---|---|---|---|
| E4-1 | REST `POST /api/backtest/optimize`：body `{class_name, vt_symbol, interval, start, end, rate, slippage, size, pricetick, capital, parameters:[{name,start,end,step}], target_name, use_ga, max_workers}` → 后端构造 `OptimizationSetting`（`add_parameter`×N + `set_target`）→ `start_optimization(...)` | `features/backtest/api.py` | curl 发起优化任务 |
| E4-2 | WS：`EVENT_BACKTESTER_OPTIMIZATION_FINISHED` → `backtester_optimization_finished`，前端收到后拉结果 | `core/events.py` | 优化结束前端可感知 |
| E4-3 | 结果查询 `GET /api/backtest/optimize/result`：返回参数组合 + 每组 target 值（`get_result_values()`，以实际返回为准） | `features/backtest/api.py` | curl 拉取最优参数组 |
| E4-4 | 前端：优化配置表单（参数范围 + 目标 + 遗传 / 网格 + workers 数）+ 进度（复用 `backtester_log`）+ 结果表（参数组合 → 目标值排序）+ 一键回填参数到回测 / 实例 | `features/backtest/` | 浏览器跑优化、看结果、回填参数 |
| E4-5 | 验收：双均线策略优化 fast / slow 窗口，得到最优组，回填后回测结果与优化一致 | — | 全链路可用 |

**实施顺序建议**：E3（纯计算，最快）→ E4（依赖 E3，且 `start_optimization` 已内置多进程，顺手）→ E2（依赖 E2-1 挂 AlgoTrading + 自研 RolloverAlgo）→ E1（最大，放最后，E4 的 `max_workers` 多进程经验可复用）。

## 8. 性能调优方案

> 目标：把性能作为 A–E 全阶段的**横切关注点**，而不是事后优化。核心指标是 **Tick-2-Trade 延迟**。先埋点测量（P8）再优化热点，避免无数据凭感觉改。

### 8.1 性能目标（量化）

| 指标 | 目标 | 测量方式 |
|---|---|---|
| Tick-2-Trade 延迟 | p50 < 10ms，p99 < 50ms（本地单机） | `tick.datetime` 进 EventEngine → `send_order` 完成，`time.perf_counter` 埋点 |
| WS 推送吞吐 | 单进程 ≥ 5 万 msg/s（聚合前） | 压测 tick 洪峰，统计丢帧率 |
| 策略并发 | 单机 > 50 实例后 GIL 不再是瓶颈（E1 后） | E1-8 压测 |
| 回测速度 | 1 年 1 分钟 K（约 25 万 bar）单策略 < 30s | E4 基准 |
| ClickHouse 写入 | 峰值不阻塞行情 | 现有 `_MAX_QUEUE=50_000` 满则丢 + 队列深度监控 |

### 8.2 性能五原则

1. **关键路径 / 慢路径分离**：`tick → 策略 → 下单` 是关键路径，必须零阻塞；WS 推送、ClickHouse 写、日志全部异步解耦。现有 `features/market/tick_writer.py` 的 `enqueue_tick`（非阻塞、满则丢）+ 独立线程批量写已是范本——阶段 A/E 的策略日志、状态回传照此模式做。
2. **按需序列化**：同一 payload 的 JSON **只序列化一次并缓存**，仅对订阅了该 topic 的连接发送；用 `orjson` 替换标准 `json`（通常 2–5 倍）。
3. **批量与攒批**：WS 高频 tick 攒批（10–20ms 窗口，可配）再 flush；IPC 行情批量投递；ClickHouse 已是批量（`_BATCH=400`）。
4. **向量化**：策略指标用 numpy（08 的 RumiStrategy 已是）；HistoryManager 用**预分配 numpy 数组 + 滚动索引**，避免 `append` 触发数组复制。
5. **零拷贝 / 共享内存**：多进程 IPC 用 `multiprocessing.shared_memory` + 环形缓冲传 numpy 数组，避免 pickle 大对象（E1 关键）。

### 8.3 关键路径时序（单 Tick）与优化点

```text
CTP 回调 → EventEngine.put(EVENT_TICK)
  → core/events.on_tick:
      ① record_tick(内存缓冲)          ~µs    （主进程 GIL）
      ② enqueue_tick(CH 队列, 异步)     ~µs    （已非阻塞，满则丢）
      ③ publish_threadsafe(WS)          ~µs~ms  （序列化最重，主进程 GIL 竞争点）
  → (E1 后) CtaDispatcher 路由 TickMsg → worker 子进程
  → worker: on_tick → BarGenerator 合成 → on_bar 算信号（numpy）
  → TargetMsg 回主进程
  → 主进程 OMS: cancel_all + send_order
```

优化点：
- **③ 是主进程最大 GIL 竞争点**：按需序列化 + orjson + 攒批（对应 P1/P2）。
- **①③ 与策略计算争 GIL**：E1 把策略计算（worker）从主进程剥离后，①③ 延迟显著下降（E1 的收益之一）。
- **② 已异步**：保持现状，只加队列深度监控（P8）。

### 8.4 分层优化清单 + 性能任务

| 性能任务 | 层 | 瓶颈 | 手段 | 关联任务 |
|---|---|---|---|---|
| P1 | 序列化 | `json.dumps` + 每 tick 建 30+ 字段 dict | `orjson`；payload 缓存；只对订阅连接序列化 | A1 / S5 |
| P2 | WS fan-out | `WsHub.route()` O(连接数) 逐连接遍历 + topic 集合运算 | topic→连接**倒排索引**；攒批 flush | A2 / A8 |
| P3 | 事件回调 | 回调里重活占 GIL | 回调只入队，重活下沉 worker / 线程（照 `tick_writer` 模式） | A2 |
| P4 | 多进程 IPC | pickle 大对象往返 | `shared_memory` + 环形缓冲；行情**批量投递** | E1-1 / E1-3 |
| P5 | 策略计算 | Python 循环 | numpy 向量化；HistoryManager 预分配数组 | C1 / C2 |
| P6 | 回测/优化 | 单核 | `max_workers` 多进程；策略向量化 | E4 / B5 |
| P7 | 前端 | 高频响应式更新 | 节流/批量写 store；虚拟滚动；图表数据采样 | A10 / B5 |
| P8 | 埋点监控 | 无量化基线 | `core/metrics.py` 加延迟/队列深度，暴露到 `/health` | 新增（见 8.6） |

### 8.5 各阶段性能验收补充（并入对应任务的「验收」）

| 阶段 | 原任务 | 追加性能验收 |
|---|---|---|
| A | A2 | tick 洪峰（如 100 tick/s × 多合约）下 EventEngine 不被 WS 序列化阻塞（用 P8 埋点验证） |
| A | A10 | 前端在 tick 高频下 UI 不卡顿（P7 节流 + 虚拟滚动） |
| E1 | E1-8 | 明确 p50/p99 Tick-2-Trade 指标；对比单进程基线，证明 GIL 收益 |
| E4 | E4-1 | `max_workers = min(cpu_count, 参数组合数)`；优化吞吐随核数近线性 |

### 8.6 性能埋点（`core/metrics.py`，与 E3 的 R-Cubed 同文件分模块）

| 指标 | 含义 | 采集方式 |
|---|---|---|
| `tick_to_trade_latency` | tick 到达 → 下单完成的 p50/p99 | 下单处回填 `tick.datetime` 差值 |
| `ws_queue_depth` | asyncio 待发送消息数 | `WsHub` 计数 |
| `ipc_queue_depth` | worker 管道待处理消息数 | `WorkerManager` 计数 |
| `ch_queue_depth` | ClickHouse 写队列长度 | `tick_writer` 暴露 `_q.qsize()` |
| `strategy_latency` | 单策略 on_bar 耗时 | worker 内 `perf_counter` 环绕 |

暴露方式：`/health` 追加 `metrics` 段；告警阈值进配置（如 `tick_to_trade_latency.p99 > 50ms`）。

**性能实施顺序**：P8（先有基线）→ P1/P2（主进程热点，见效最快）→ P4（随 E1 一起做，避免二次返工）→ P5/P6（策略与回测）→ P7（前端）。P3 是模式约束，贯穿始终。
