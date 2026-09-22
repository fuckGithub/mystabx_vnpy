# module_task — 任务与工作流

## 模块定位

定时任务（APScheduler，DB 驱动）与 Prefect 工作流定义/执行。
边界：任务与工作流自身的表和管理接口；内核调度器（`app/core/ap_scheduler.py`）不反向
依赖本插件，只经 `scheduler.job_log_sink` 槽位回写任务日志。

## 入口

| 入口类型         | 路径                     | 说明                                                                                     |
| ---------------- | ------------------------ | ---------------------------------------------------------------------------------------- |
| 插件入口         | `plugin.py`              | `class Plugin(PluginBase)`：声明 2 个模型模块；`start()` 注入 `scheduler.job_log_sink`     |
| HTTP 路由        | `<子模块>/**/controller.py` | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/task`（2 个 controller，共 24 条）        |
| WebSocket 路由   | 无                       | —                                                                                        |
| ORM 模型         | `<子模块>/**/model.py`   | 2 张表，见下                                                                             |
| 种子数据         | 无                       | —                                                                                        |
| 内核槽位（提供） | `plugin.py::start()`     | `scheduler.job_log_sink`（实现：`job_log_sink.py::JobLogSinkImpl`）                       |
| 定时任务         | 无                       | 未调用 `ctx.add_scheduler_job`（任务清单来自数据库，由内核调度器启动时同步）              |
| 事件订阅         | 无                       | 未调用 `ctx.on(...)`                                                                      |

子路由：

| 子模块     | 路由前缀                          | 条数 |
| ---------- | --------------------------------- | ---- |
| `cronjob`  | `/task/cronjob/job`、`/task/cronjob/node` | 24   |

ORM 模型（`__tablename__`）：`task_job`、`task_node`（`cronjob` 下）。

## 依赖

- 内核槽位：无消费；**提供** `scheduler.job_log_sink`（内核 `core/ap_scheduler.py` 消费）。
- 其它插件：无（`plugin.toml` 未声明 `depends`；运行时用内核 `AuthSchema`/`AuthPermission`，
  因此实际需要 `system` 提供 `auth.user_resolver` 才能登录后调用本插件接口）。
- 第三方：`apscheduler`（调度）、`prefect`（工作流引擎）。

## 删除影响

删除本目录后：

- `/task/*` 下 24 条接口全部消失（任务节点/调度器控制/任务日志）。
- `task_job`、`task_node` 不再自动创建。
- `scheduler.job_log_sink` 槽位缺失 → 内核调度器跳过任务日志落库（仍正常调度，记 WARNING）。
- 已配置的定时任务仍在调度器中运行（调度状态由内核持有），但无法再通过接口查看/管理；
  工作流执行链路整体失效。
