# module_ai — AI 能力集成（可选插件）

## 模块定位

AI 供应商/模型两级管理与聊天会话（含 WebSocket 流式）能力（基于 Agno）。
边界：只做「配置模型 → 选择模型 → 对话」链路与知识库能力库；不含任何鉴权实现，
鉴权复用内核 `app/core/auth`。

两级结构：`ai_provider`（供应商：base_url/api_key/协议类型）与 `ai_model`
（模型：按 `api_type` 协议映射构建实例），支持不同供应商下的同名模型。

## 入口

| 入口类型         | 路径                      | 说明                                                                                   |
| ---------------- | ------------------------- | -------------------------------------------------------------------------------------- |
| 插件入口         | `plugin.py`               | `class Plugin(PluginBase)`：`MODEL_PATHS=("model.model",)`；`setup()` 里 `ctx.add_models` + `ctx.add_seed_file`（供应商/模型种子）+ `ctx.add_router(WS_AI, ...)` |
| HTTP 路由        | `<子模块>/controller.py`  | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/ai`（2 个 controller，共 22 条 HTTP）    |
| WebSocket 路由   | `chat/ws.py` → `WS_AI`    | **不经目录扫描**（文件不叫 `controller.py`），由 `plugin.py::setup()` 用 `ctx.add_router()` 声明，并自带 `WebSocketRateLimiter(times=1, seconds=5)` |
| ORM 模型         | `model/model.py`          | 表 `ai_provider`、`ai_model`                                                            |
| 知识库能力库     | `rag/`                    | Agno Knowledge / PgVector 向量库 / Embedding 工厂；**无 HTTP 入口**，由 `chat/service.py` 在聊天时注入（非 PostgreSQL 后端自动降级为不注入） |
| 知识文档         | `knowledge/*.md`          | 系统知识文档，由 `rag/knowledge_content.py` 首次聊天时幂等写入知识库                     |
| 种子数据         | `seeds/data/*.json`       | `ai_provider`（6 行）+ `ai_model`（12 行），由 `plugin.py::setup()` 的 `ctx.add_seed_file` 注册（声明序 = 写入序） |
| 内核槽位         | 无                        | 既不提供也不消费                                                                        |
| 定时任务         | 无                        | 未调用 `ctx.add_scheduler_job`                                                          |
| 事件订阅         | 无                        | 未调用 `ctx.on(...)`                                                                    |

路由前缀：

| 子模块  | 路由前缀                        | 条数 |
| ------- | ------------------------------- | ---- |
| `chat`  | `/ai/chat`（含 `WEBSOCKET /ai/chat/ws`） | 7    |
| `model` | `/ai/model`、`/ai/provider`     | 16   |

## 依赖

- 内核槽位：无。
- 其它插件：`system`（`plugin.toml` 声明 `depends = ["system"]`；`chat/service.py` 直接
  import `module_system/dept/service.py`，故 `system` 是本插件的**硬依赖**，缺失时本插件
  在 setup 期导入失败并降级）。
- 第三方：`agno`（模型/知识库/向量库）、`fastembed`（本地 Embedding，无需 API key）、
  `fastapi_limiter`（WebSocket 限流）。
- 向量检索（`rag/`）走 `PgVector`，**仅 PostgreSQL 后端可用**；MySQL/SQLite 下
  `rag_supported()` 返回 `False`，聊天链路降级为「不注入知识库、仅注入系统查询工具」。

## 删除影响

删除本目录后：

- `/ai/chat/*`（含 WebSocket `/ai/chat/ws`）、`/ai/model/*`、`/ai/provider/*` 全部消失。
- 表 `ai_provider`、`ai_model` 不再自动创建（已存在的表与配置数据保留）。
- `rag/` 能力库与 `knowledge/*.md` 知识文档一并删除（文档随插件存放，不残留孤儿文件）；
  聊天链路失去知识库与系统查询工具，回到普通对话。
- 种子数据不再写入：已存在的 `ai_provider` / `ai_model` 行不受影响，新库不再预置供应商与模型。
- 无槽位、无定时任务、无事件订阅：其它插件与内核不受影响。
