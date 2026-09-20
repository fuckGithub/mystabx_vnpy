# 从 0 到 1 搭建你的 Web 期货量化交易台 · 03 无界面启动 vnpy 引擎：headless MainEngine 是怎么跑的

> 📌 系列第 3 篇 ｜ 本文目标：搞懂"没有 Qt，引擎怎么跑起来" ｜ 预计阅读 7 分钟
> ⚠️ 本系列是「量化交易系统开发」技术内容，不构成投资建议。

## 一、先破除一个误解

很多人以为 vnpy = 桌面软件，必须开图形界面才能交易。其实不是——**vnpy 的核心引擎（`MainEngine` / `EventEngine`）完全不依赖 Qt**，Qt 只是官方给的"显示层"。把显示层去掉，引擎照样能跑，这就叫 **headless**。

本项目的入口就是这么做的，核心在 `core/engine.py`：

```python
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway


def build_headless_engines() -> tuple[MainEngine, EventEngine]:
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    # 命名实例由 AccountGatewayManager 之后注册
    _ = CtpGateway
    return main_engine, event_engine
```

就这么短。两个核心对象：

- **`EventEngine`**：事件驱动引擎，vnpy 的心跳，负责 `put(event)` / `register(type, handler)`；
- **`MainEngine`**：主引擎，管理网关（Gateway）、应用（App）、OMS，向外提供 `send_order` / `subscribe` 等方法。

## 二、引擎在进程里的"生命周期"

真正把它们串起来的是 `core/main.py` 的 FastAPI lifespan：

```python
main_engine, event_engine = build_headless_engines()
manager = AccountGatewayManager(main_engine)
manager.load_all(_load_accounts())      # 从 MySQL 加载账户
bind_events(event_engine, manager)      # 把 vnpy 事件桥接到 WebSocket
runtime.main_engine = main_engine
runtime.event_engine = event_engine
```

`core/runtime.py` 里用一个进程级单例 `runtime` 持有引擎引用，这样任何 API 都能拿到：

```python
runtime.me        # MainEngine
runtime.oms       # OmsEngine（订单管理）
runtime.gw        # AccountGatewayManager（多账户）
```

## 三、为什么"不要 uvicorn --workers"（重点）

这是本项目踩过、也最容易踩的坑：

```bash
# ❌ 错误
uvicorn core.main:app --workers 4

# ✅ 正确
uvicorn core.main:app --host 0.0.0.0 --port 18080
```

原因：`MainEngine` / `EventEngine` 是**进程内单例**。`--workers 4` 会 fork 出 4 个进程，各自初始化一份引擎、各自连柜台，**账户会重复连接、事件会串、状态会乱**。

所以本项目强调：**vnpy 引擎必须单进程**，用 `./start.sh` 时它内部就是单 worker 的 uvicorn。

## 四、headless 后，前端怎么"操作"引擎

桌面版是"按钮 → 直接调 MainEngine 方法"。Web 版是：

```
浏览器 → REST 请求 → FastAPI 路由 → 调 runtime.me.send_order(...) → 柜台
柜台回报 → vnpy 事件 → 桥接层 → WebSocket → 浏览器
```

- **主动操作**走 REST（下单、撤单、订阅、连接）；
- **被动推送**走 WebSocket（tick、委托、成交、持仓、资金）。

这个"主动 REST + 被动 WS"的双通道，是整套 B/S 化的骨架，下一篇（后端骨架）会看到具体路由，第 6、7 篇看行情和下单。

## 五、小结

- vnpy 引擎 headless 可跑，Qt 只是显示层；
- `EventEngine` + `MainEngine` + `runtime` 单例，是后端的地基；
- **单进程**是硬约束，`--workers` 会毁掉一切。

> 🎁 引擎内部源码逐行解读、事件驱动机制详解，已沉淀在知识星球 **「MyStabx 期货量化交易平台」**。

扫描下方优惠券二维码，领取新人立减券（¥88，限量 100 张，有效至 2026/12/31）：

![MyStabx 知识星球新人优惠券](https://stabx-dev.oss-cn-beijing.aliyuncs.com/mystabx/docs/images/mystabx-zsxq-coupon.png)
