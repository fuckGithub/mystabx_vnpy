# module_monitor — 系统监控

## 模块定位

在线用户、Redis 缓存、服务器信息与静态资源目录四类监控。
边界：只读/管理运行态数据，不含任何 ORM 模型与种子；在线用户列表由 Redis 会话键推导
（不写库）。

## 入口

| 入口类型       | 路径                     | 说明                                                                            |
| -------------- | ------------------------ | ------------------------------------------------------------------------------- |
| 插件入口       | `plugin.py`              | `class Plugin(PluginBase)`：`setup()` 仅调用 `ctx.add_models()`（无模型）       |
| HTTP 路由      | `<子模块>/controller.py` | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/monitor`（4 个子路由，共 20 条） |
| WebSocket 路由 | 无                       | —                                                                               |
| ORM 模型       | 无                       | 本插件无 `model.py`                                                             |
| 种子数据       | 无                       | —                                                                               |
| 内核槽位       | 无                       | 既不提供也不消费                                                                |
| 定时任务       | 无                       | 未调用 `ctx.add_scheduler_job`                                                  |
| 事件订阅       | 无                       | 未调用 `ctx.on(...)`（`auth.login`/`auth.logout` 事件当前无发布者）             |

子路由：

| 子模块     | 路由前缀            | 条数 |
| ---------- | ------------------- | ---- |
| `cache`    | `/monitor/cache`    | 7    |
| `online`   | `/monitor/online`   | 3    |
| `resource` | `/monitor/resource` | 9    |
| `server`   | `/monitor/server`   | 1    |

## 依赖

- 内核槽位：无。
- 其它插件：无（`plugin.toml` 声明 `depends = ["system"]`；运行时依赖 Redis 与静态目录配置）。
- 内核代码：`app/core/auth`（`SessionInfo`）、`app/core/redis_crud.py`。

## 删除影响

删除本目录后：

- `/monitor/*` 下 20 条接口全部消失（缓存/在线用户/资源目录/服务器信息）。
- 无数据表、无种子：菜单与权限码写在 `module_system` 的 `seeds/data/sys_menu.json` 中，
  删除本插件后**菜单行仍保留**，但对应接口 404（前端页面不可用）。
- 不影响其它插件与内核（无槽位、无事件、无定时任务）。
