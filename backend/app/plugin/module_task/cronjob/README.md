# module_task/cronjob — 定时任务（节点 / 调度器）

## 模块定位

定时任务节点（`task_node`：任务定义与代码块）与任务实例（`task_job`：调度配置与状态）管理，
外加调度器运行时控制界面（启动/暂停/恢复/关闭/同步/状态/任务清单/控制台）。
边界：本子模块只做数据与调度器控制；内核 `app/core/ap_scheduler.py` 负责真正的调度循环，
并经由 `scheduler.job_log_sink` 槽位回写任务日志。

## 入口

| 入口类型  | 路径                                       | 说明                                     |
| --------- | ------------------------------------------ | ---------------------------------------- |
| HTTP 路由 | `job/controller.py` → `JobRouter`          | 容器前缀 `/task/cronjob/job`，共 16 条   |
| HTTP 路由 | `node/controller.py` → `NodeRouter`        | 容器前缀 `/task/cronjob/node`，共 8 条   |
| ORM 模型  | `job/model.py`、`node/model.py`            | 表 `task_job`、`task_node`               |
| 转换函数  | `node/service.py::node_to_job_spec`        | 把 `NodeModel` 转成内核 `JobSpec`（内核不 import 本插件） |

路由（24 条）：`/task/cronjob/job/{list 之外的 log/*(3)、scheduler/*(10)、task/*(4)}` 共 16 条 +
`/task/cronjob/node/{list,create,update/{id},delete,detail/{id},execute/{id},options,clear}` 共 8 条。

## 依赖

- 内核槽位：无直接消费；父插件提供 `scheduler.job_log_sink`，本子模块的 `node/service.py`
  产出内核 `JobSpec`（`app/core/plugin/context.py`）。
- 其它插件：无（父插件 `module_task`）。
- 第三方：`apscheduler`（经内核调度器）。

## 删除影响

删除本子模块后：

- `/task/cronjob/job/*`（16 条）与 `/task/cronjob/node/*`（8 条）共 24 条接口消失。
- 表 `task_job`、`task_node` 不再自动创建，已配置任务无法再管理。
- 内核调度器仍会运行（不依赖本子模块的导入），但任务日志槽位的数据来源与调度器控制面板缺失。
