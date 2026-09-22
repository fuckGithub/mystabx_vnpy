# module_monitor/online — 在线用户监控

## 模块定位

从 Redis 会话键（`access_token:*`）推导在线用户列表，并支持按条件检索、强制下线与清空。
边界：不写业务库；会话数据形状取自内核 `app/core/auth/session.py::SessionInfo`
（本子模块 `schema.py` 的 `OnlineOutSchema` 继承该模型）。

## 入口

| 入口类型  | 路径                             | 说明                                    |
| --------- | -------------------------------- | --------------------------------------- |
| HTTP 路由 | `controller.py` → `OnlineRouter` | 容器前缀 `/monitor/online`，共 3 条     |
| ORM 模型  | 无                               | 无 `model.py`（数据源是 Redis，不是表） |
| 依赖模型  | `schema.py`                      | `OnlineOutSchema(SessionInfo)`          |

路由（3 条）：`GET /monitor/online/list`、`DELETE /monitor/online/delete`、
`DELETE /monitor/online/clear`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（登录写入的 Redis 会话键由 `module_system/auth` 产生）。
- 内核代码：`app/core/auth/session.py::SessionInfo`、`app/core/redis_crud.py`。

## 删除影响

删除本子模块后：

- `/monitor/online/*` 3 条接口消失：无法查看在线用户、无法强制下线或清空会话。
- 无数据表、无种子；Redis 会话键与登录/登出流程不受影响。
