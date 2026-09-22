# module_system/log — 操作日志

## 模块定位

操作日志（`sys_log`）的查询、详情、删除与导出。
边界：写入侧由内核 `core/router_class.py` 收集，经 `log.operation_sink` 槽位落到本子模块
的 `OperationLogSinkImpl`；本子模块的 HTTP 接口只负责「读与管理」。

## 入口

| 入口类型         | 路径                                | 说明                                                          |
| ---------------- | ----------------------------------- | ------------------------------------------------------------- |
| HTTP 路由        | `controller.py` → `LogRouter`       | 容器前缀 `/system/log`，共 4 条                                |
| ORM 模型         | `model.py`                          | `sys_log`                                                     |
| 内核槽位（实现） | `service.py::OperationLogSinkImpl`  | 由父插件 `plugin.py::start()` 注入 `log.operation_sink`        |
| 种子数据         | 无                                  | 不写入日志表                                                  |

路由（4 条）：`list`、`detail/{id}`、`delete`、`export`。

## 依赖

- 内核槽位：无消费；**提供** `log.operation_sink`（内核 `core/router_class.py::OperationLogRoute` 消费）。
- 其它插件：`system`（日志行关联用户信息）。

## 删除影响

删除本子模块后：

- `/system/log/*` 4 条接口消失，操作日志不可查询/导出/清理。
- `sys_log` 不再自动创建，日志不再落库；内核仍写文件日志（降级行为，不报错）。
