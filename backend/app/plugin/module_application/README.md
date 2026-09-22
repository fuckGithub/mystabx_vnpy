# module_application — 应用管理

## 模块定位

应用门户（`app_portal`）的增删改查、启用设置与「插件清单」查询。
边界：只维护门户应用数据；插件清单不落库，直接来自内核插件发现器
（`app/core/plugin/loader.discover_plugins`）。

## 入口

| 入口类型       | 路径                   | 说明                                                                            |
| -------------- | ---------------------- | ------------------------------------------------------------------------------- |
| 插件入口       | `plugin.py`            | `class Plugin(PluginBase)`：`setup()` 声明 `ctx.add_models("portal.model")`     |
| HTTP 路由      | `portal/controller.py` | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/application`（1 个子路由，7 条） |
| WebSocket 路由 | 无                     | —                                                                               |
| ORM 模型       | `portal/model.py`      | 表 `app_portal`                                                                 |
| 种子数据       | 无                     | —                                                                               |
| 内核槽位       | 无                     | 既不提供也不消费                                                                |
| 定时任务       | 无                     | 未调用 `ctx.add_scheduler_job`                                                  |
| 事件订阅       | 无                     | 未调用 `ctx.on(...)`                                                            |

子路由：

| 子模块   | 路由前缀              | 条数 |
| -------- | --------------------- | ---- |
| `portal` | `/application/portal` | 7    |

## 依赖

- 内核槽位：无。但 `portal/plugin_manifest.py` **直接调用内核** `discover_plugins()` 与
  `SchemaUtil` 读取插件清单（这是与其它插件不同的一点：消费内核函数，而非槽位）。
- 其它插件：无（`plugin.toml` 声明 `depends = ["system"]`；门户接口本身用 `AuthPermission`
  做鉴权，因此实际需要 `system` 提供 `auth.user_resolver` 槽位）。

## 删除影响

删除本目录后：

- `/application/portal/*` 7 条接口消失，应用门户不可用。
- `app_portal` 不再自动创建（已存在的表与数据保留）。
- 无种子、无定时任务；插件清单接口消失，但插件发现与加载本身不受影响。
