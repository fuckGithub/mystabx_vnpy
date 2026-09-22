# module_example — 示例插件（可安全删除）

## 模块定位

开发示例插件：演示 `module_*` 目录约定、动态路由挂载、ORM 模型声明与生成器产出的代码形态。
边界：纯演示，不含业务语义；`plugin.toml` 声明 `optional = true`，删除后不影响任何功能。

## 入口

| 入口类型       | 路径                     | 说明                                                                                                                 |
| -------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| 插件入口       | `plugin.py`              | `class Plugin(PluginBase)`：`MODEL_PATHS=("demo.model","demo01.model")`，`setup()` 里 `ctx.add_models(*MODEL_PATHS)` |
| HTTP 路由      | `<子模块>/controller.py` | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/example`（2 个子路由，共 18 条）                                      |
| WebSocket 路由 | 无                       | —                                                                                                                    |
| ORM 模型       | `<子模块>/model.py`      | 表 `gen_demo`、`gen_demo01`                                                                                          |
| 种子数据       | 无                       | —                                                                                                                    |
| 内核槽位       | 无                       | 既不提供也不消费                                                                                                     |
| 定时任务       | 无                       | 未调用 `ctx.add_scheduler_job`                                                                                       |
| 事件订阅       | 无                       | 未调用 `ctx.on(...)`                                                                                                 |

子路由：

| 子模块   | 路由前缀          | 条数 |
| -------- | ----------------- | ---- |
| `demo`   | `/example/demo`   | 9    |
| `demo01` | `/example/demo01` | 9    |

## 依赖

- 内核槽位：无。
- 其它插件：无（`plugin.toml` 未声明 `depends`；接口用内核 `AuthSchema`/`AuthPermission`
  鉴权，因此需要 `system` 提供 `auth.user_resolver` 才能登录后调用）。

## 删除影响

删除本目录后：

- `/example/*` 下 18 条接口消失（demo 与 demo01 各 9 条）。
- 表 `gen_demo`、`gen_demo01` 不再自动创建（已存在的表与数据保留）。
- 无种子、无槽位、无定时任务、无事件；**其余插件与内核完全不受影响**（这是
  「增删插件互不影响」的最小演示）。
- 前端若挂有示例菜单，会指向已不存在的接口（404）。
