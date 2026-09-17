# 10 VeighNa 功能列表

> 来源：[VeighNa 官方 GitHub（vnpy/vnpy，4.4.0）](https://github.com/vnpy/vnpy)、[官方文档](https://www.vnpy.com/docs/cn/index.html) 与 [08-VeighNa-Elite-CTA策略参考](08-VeighNa-Elite-CTA策略参考.md)（Elite 专属能力）。版本以 vnpy 4.x 为准；本项目 `mystabx_vnpy` 当前锁定 `vnpy 4.0.0`（见文末「本项目已装模块」）。

VeighNa（原 vn.py）是一套基于 Python 的开源量化交易系统开发框架，定位「从策略想法到实盘下单，全流程一个框架」。功能按层次分为：**核心框架 → 交易接口 → 交易应用 → 数据层 → API 封装 → 产品线**。

## 1. 核心框架（vnpy 本体）

| 模块 | 说明 |
|---|---|
| `vnpy.trader` | 交易核心：`MainEngine`（主引擎）、`OmsEngine`（订单管理）、`BaseEngine`、`BaseApp`（应用扩展机制）、`BaseGateway`（网关抽象）、数据对象、交易常量、工具函数、参数优化 |
| `vnpy.event` | 事件驱动引擎（`EventEngine`），事件驱动型交易程序的核心 |
| `vnpy.rpc` | 跨进程通讯标准组件，用于分布式部署 |
| `vnpy.chart` | Python 高性能 K 线图表，支持大数据量与实时更新 |
| `vnpy.alpha` | **4.0 新增**：一站式多因子机器学习（ML）策略开发与投研（详见 1.1） |

### 1.1 vnpy.alpha（AI 量化 / 多因子 ML）

| 子模块 | 说明 |
|---|---|
| `dataset` | 因子特征工程：批量特征计算、表达式计算引擎、自定义函数注册、缺失值/无穷值/标准化/特征删除；内置 **Alpha 158** 因子库（源自微软 Qlib） |
| `model` | 预测模型训练：统一 API，内置 **Lasso**、**LightGBM**、**MLP** 三种模型 |
| `strategy` | 策略投研：基于 ML 信号构建策略，支持**截面多标的**与**时序单标的** |
| `lab` | 投研流程管理：数据管理 + 模型训练 + 信号生成 + 回测的完整工作流，内置可视化 |
| `notebook` | 量化投研 Demo（RQData / 迅投研数据下载、Lasso/LightGBM/MLP 工作流示例） |

### 1.2 核心对象与工具（`vnpy.trader`）

- **数据对象**：`TickData`、`BarData`、`OrderData`、`TradeData`、`PositionData`、`AccountData`、`ContractData`、`LogData`、`OrderRequest`、`CancelRequest`、`HistoryRequest` 等
- **交易常量**：`Direction`、`Offset`、`OrderType`、`Status`、`Interval`、`Exchange`、`Product`、`OptionType`、`EngineType` 等
- **工具函数**：`BarGenerator`（Tick 合成 K 线）、`ArrayManager`（K 线序列管理）、`extract_vt_symbol` / `generate_vt_symbol`、`round_to`（价格最小变动取整）等
- **内置技术指标**（talib 封装）：`sma / wma / ema / kama / macd / atr / rsi / boll / cci / adx / obv`
- **持仓转换**：`OffsetConverter`（多空持仓 / 昨仓今仓转换）
- **参数优化**：`OptimizationSetting`（网格 / 遗传优化参数配置）

## 2. 交易接口（Gateway）

### 2.1 国内市场

| 接口 | 代码库 | 覆盖品种 |
|---|---|---|
| CTP | `vnpy_ctp` | 期货、期权（**本项目已装**） |
| CTP Mini | `vnpy_mini` | 期货、期权 |
| CTP 证券 | `vnpy_sopt` | ETF 期权 |
| 飞马 | `vnpy_femas` | 期货 |
| 易盛 | `vnpy_esunny` | 期货、黄金 TD |
| 顶点 HTS | `vnpy_hts` | ETF 期权 |
| 顶点飞创 | `vnpy_sec` | ETF 期权 |
| 中泰 XTP | `vnpy_xtp` | A 股、ETF 期权 |
| 华鑫奇点 | `vnpy_tora` | A 股、ETF 期权 |
| 东证 OST | `vnpy_ost` | A 股 |
| 东方财富 EMT | `vnpy_emt` | A 股 |
| 飞鼠 | `vnpy_sgit` | 黄金 TD、期货 |
| 金仕达黄金 | `vnpy_ksgold` | 黄金 TD |
| 利星资管 | `vnpy_lstar` | 期货资管 |
| 融航 | `vnpy_rohon` | 期货资管 |
| 杰宜斯 | `vnpy_jees` | 期货资管 |
| 中汇亿达 | `vnpy_comstar` | 银行间市场 |
| TTS | `vnpy_tts` | 期货（仿真） |

### 2.2 海外市场

| 接口 | 代码库 | 覆盖品种 |
|---|---|---|
| Interactive Brokers | `vnpy_ib` | 海外证券、期货、期权、贵金属等 |
| 易盛 9.0 外盘 | `vnpy_tap` | 海外期货 |
| 直达期货 | `vnpy_da` | 海外期货 |

### 2.3 特殊应用接口

| 接口 | 代码库 | 说明 |
|---|---|---|
| RQData 行情 | `vnpy_rqdata` | 跨市场（股票/指数/ETF/期货）实时行情 |
| 迅投研行情 | `vnpy_xt` | 跨市场实时行情 |
| RPC 服务 | `vnpy_rpcservice` | 跨进程通讯，分布式架构 |

## 3. 交易应用（App，官方模块）

| 应用 | 代码库 | 功能 |
|---|---|---|
| CTA 策略 | `vnpy_ctastrategy` | CTA 策略引擎，支持报撤行为细粒度控制（降低滑点、高频） |
| CTA 回测 | `vnpy_ctabacktester` | 图形界面策略回测、参数优化 |
| 价差交易 | `vnpy_spreadtrading` | 自定义价差、价差行情与持仓、价差算法交易 / 自动价差策略 |
| 期权交易 | `vnpy_optionmaster` | 期权定价模型、隐含波动率曲面、希腊值风险跟踪 |
| 组合策略 | `vnpy_portfoliostrategy` | 多合约策略（Alpha、期权套利），回测 + 实盘 |
| 算法交易 | `vnpy_algotrading` | TWAP、Sniper、Iceberg、BestLimit 等智能执行算法 |
| 脚本策略 | `vnpy_scripttrader` | 多标的策略 / 计算任务，REPL 指令交易（不支持回测） |
| 本地仿真 | `vnpy_paperaccount` | 纯本地仿真撮合，委托成交推送 + 持仓记录 |
| K 线图表 | `vnpy_chartwizard` | 历史 K 线 + Tick 实时更新 |
| 组合管理 | `vnpy_portfoliomanager` | 交易组合（子账户）管理、仓位跟踪、每日盈亏统计 |
| RPC 服务 | `vnpy_rpcservice` | 服务端统一行情/交易路由，多客户端分布式 |
| 数据管理 | `vnpy_datamanager` | 历史数据树形浏览、CSV 导入导出 |
| 行情录制 | `vnpy_datarecorder` | 录制 Tick / K 线到数据库，供回测/实盘初始化 |
| Excel RTD | `vnpy_excelrtd` | Excel 实时数据（行情/合约/持仓）推送 |
| 风险管理 | `vnpy_riskmanager` | 交易流控、下单数量、活动委托、撤单总数等前端风控 |
| Web 服务 | `vnpy_webtrader` | B-S 架构：REST 主动调用 + WebSocket 被动推送 |

## 4. 数据层

### 4.1 数据库适配器（database）

| 类型 | 数据库 | 代码库 | 说明 |
|---|---|---|---|
| SQL | SQLite | `vnpy_sqlite` | 轻量单文件，vnpy 默认 Database 适配器（**本项目已装，仅供 vnpy 非 Web 路径；业务库已改 MySQL，Tick 走 ClickHouse**） |
| SQL | MySQL | `vnpy_mysql` | 主流关系型，可替换 TiDB 等 |
| SQL | PostgreSQL | `vnpy_postgresql` | 特性更丰富，熟手使用 |
| NoSQL | QuestDB | `vnpy_questdb` | 列式时序库，兼容 PG 协议，高吞吐低延时 |
| NoSQL | DolphinDB | `vnpy_dolphindb` | 高性能分布式时序库，低延时实时 |
| NoSQL | TDengine | `vnpy_taos` | 分布式时序库，内置缓存/流计算/订阅 |
| NoSQL | MongoDB | `vnpy_mongodb` | 文档式数据库，热数据内存缓存 |

### 4.2 数据服务适配器（datafeed）

| 数据服务 | 代码库 | 覆盖 |
|---|---|---|
| 迅投研 | `vnpy_xt` | 股票、期货、期权、基金、债券 |
| 米筐 RQData | `vnpy_rqdata` | 股票、期货、期权、基金、债券、黄金 TD |
| MultiCharts | `vnpy_mcdata` | 期货、期货期权 |
| TuShare | `vnpy_tushare` | 股票、期货、期权、基金 |
| 万得 Wind | `vnpy_wind` | 股票、期货、基金、债券 |
| 同花顺 iFinD | `vnpy_ifind` | 股票、期货、基金、债券 |
| 天勤 TQSDK | `vnpy_tqsdk` | 期货 |
| 掘金 | `vnpy_gm` | 股票 |
| Polygon | `vnpy_polygon` | 股票、期货、期权 |

## 5. Python 交易 API 封装（api）

| 组件 | 代码库 | 说明 |
|---|---|---|
| REST Client | `vnpy_rest` | 协程异步 IO 高性能 REST API 客户端，高并发交易请求 |
| Websocket Client | `vnpy_websocket` | 协程异步 IO，与 REST 共用事件循环 |

## 6. 产品线 / 发行版本

| 版本 | 形态 | 定位 |
|---|---|---|
| **社区版** | 开源（MIT） | 开放式量化开发框架，覆盖尽可能广的市场与策略（上文第 1–5 节全部能力） |
| **Elite 版** | 商业闭源 | 标准化量化交易终端；多进程架构、`EliteCtaTemplate` / `EliteTargetTemplate`、`HistoryManager`、理论持仓管理器、R-Cubed、移仓助手（批量并发+价差算法）、多账户批量下单、深度交易（DOM）、算法执行（详见 [08 文档](08-VeighNa-Elite-CTA策略参考.md)） |
| **Fusion 版** | 商业闭源 | 面向期货公司经纪业务客户：单一 CTP、开箱即用、数据中心、智策 AI 投研 |
| **定制版** | 商业 | 面向机构团队的定制化量化解决方案（系统开发 + 技术咨询） |
| **VeighNa Studio / Station** | 发行版 | 集成框架 + 量化管理平台（Station 启动器）的 Windows 发行版 |

## 7. 内置示例（本项目 `.venv` 已装内容）

### 7.1 CTA 示例策略（`vnpy_ctastrategy/strategies/`）

`atr_rsi`（ATR+RSI）、`boll_channel`（布林通道）、`double_ma`（双均线）、`dual_thrust`（Dual Thrust）、`king_keltner`（Keltner）、`multi_signal`（多信号）、`multi_timeframe`（多周期）、`turtle_signal`（海龟）、`test`（测试）

### 7.2 算法交易模板（`vnpy_algotrading/algos/`）

`best_limit`（最优限价）、`iceberg`（冰山）、`sniper`（狙击手）、`stop`（止损）、`twap`（TWAP）

### 7.3 内置技术指标（`vnpy.trader.utility`）

`sma / wma / ema / kama / macd / atr / rsi / boll / cci / adx / obv`（11 个 talib 封装）

## 8. 本项目（mystabx_vnpy）已装模块

以下为当前 `.venv` 实际安装的 vnpy 组件（其余官方模块可按需 `pip install`）：

| 类别 | 已装 |
|---|---|
| 核心 | `vnpy 4.0.0`（含 `trader` / `event` / `rpc` / `chart` / `alpha`） |
| 接口 | `vnpy_ctp 6.7.7.2` |
| 应用 | `vnpy_ctastrategy 1.4.1`、`vnpy_ctabacktester 1.3.0`、`vnpy_spreadtrading 1.3.1`、`vnpy_optionmaster 1.3.0`、`vnpy_portfoliostrategy 1.2.2`、`vnpy_algotrading 1.1.0`、`vnpy_scripttrader 1.1.1`、`vnpy_paperaccount 1.0.6`、`vnpy_chartwizard 1.1.0`、`vnpy_portfoliomanager 1.1.0`、`vnpy_rpcservice 1.1.0`、`vnpy_datamanager 1.2.0`、`vnpy_datarecorder 1.1.1`、`vnpy_riskmanager 2.0.0`、`vnpy_webtrader 1.1.0` |
| 数据库 | `vnpy_sqlite 1.1.3`（vnpy Database 适配器；Web 业务不用） |

> 说明：本项目是「Web UI + FastAPI 托管层」围绕开源 vnpy 二次开发，当前只启用了 CTP 接口 + 自研的行情/下单/账户链路，CTA / 回测等 App 的 Web 化接入见 [09-CTA策略实施规划](09-CTA策略实施规划.md)。
