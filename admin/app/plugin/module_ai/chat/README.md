# module_ai/chat — AI 聊天会话

## 模块定位

聊天会话管理（创建/查询/改名/删除）与对话执行，其中对话支持 WebSocket 流式输出。
边界：只负责会话与模型调用编排；供应商/模型配置由 `module_ai/model` 提供。

## 入口

| 入口类型       | 路径                        | 说明                                                                     |
| -------------- | --------------------------- | ------------------------------------------------------------------------ |
| HTTP 路由      | `controller.py` → `ChatRouter` | 容器前缀 `/ai/chat`，共 6 条（由目录扫描挂载）                          |
| WebSocket 路由 | `ws.py` → `WS_AI`           | `WEBSOCKET /ai/chat/ws`；**由 `module_ai/plugin.py::setup()` 的 `ctx.add_router()` 声明**，不走目录扫描（文件名不是 `controller.py`），且限流器是 `WebSocketRateLimiter(times=1, seconds=5)` |
| ORM 模型       | 无                          | 本子模块没有 `model.py`；会话数据存储依赖 Agno/内存实现                   |
| 业务实现       | `service.py`、`crud.py`、`utils.py`、`schema.py` | —                                                   |

路由（7 条，含 WebSocket）：
`GET /ai/chat/list`、`POST /ai/chat/create`、`PUT /ai/chat/update/{session_id}`、
`DELETE /ai/chat/delete`、`GET /ai/chat/detail/{session_id}`、
`POST /ai/chat/ai-chat`、`WEBSOCKET /ai/chat/ws`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（`dept/service.py` 被模块级导入）、`ai`（同插件的 `model` 子模块取模型配置）。
- 第三方：`agno`。

## 删除影响

删除本子模块后：

- `/ai/chat/*` 与 `WEBSOCKET /ai/chat/ws` 全部消失；`plugin.py::setup()` 里对 `WS_AI` 的
  import 会失败 → **整个 `module_ai` 插件降级**（setup 不执行、模型与路由都不注册）。
- 无数据表、无种子；`module_ai/model` 的供应商/模型配置接口不受影响（但插件级降级会一并失效）。
