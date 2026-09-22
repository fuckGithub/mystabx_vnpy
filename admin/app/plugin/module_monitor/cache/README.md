# module_monitor/cache — 缓存监控

## 模块定位

Redis 缓存的只读监控与键删除：缓存信息概览、键名列表、键值查询，以及按键/按键名删除。
边界：只操作 Redis，不建表、不写库；管理端点需要权限码。

## 入口

| 入口类型  | 路径                            | 说明                               |
| --------- | ------------------------------- | ---------------------------------- |
| HTTP 路由 | `controller.py` → `CacheRouter` | 容器前缀 `/monitor/cache`，共 7 条 |
| ORM 模型  | 无                              | 无 `model.py`                      |

路由（7 条）：`GET /monitor/cache/info`、`GET /monitor/cache/get/names`、
`GET /monitor/cache/get/keys/{cache_name}`、`GET /monitor/cache/get/value/{cache_name}/{cache_key}`、
`DELETE /monitor/cache/delete/all`、`DELETE /monitor/cache/delete/key/{cache_key}`、
`DELETE /monitor/cache/delete/name/{cache_name}`。

## 依赖

- 内核槽位：无。
- 其它插件：无（只依赖 Redis 与配置）。
- 内核代码：`app/core/redis_crud.py`。

## 删除影响

删除本子模块后：

- `/monitor/cache/*` 7 条接口消失：无法查看/清理缓存（`delete/all` 的应急能力一并消失）。
- 无数据表、无种子；缓存本身与其它模块的缓存读写不受影响。
