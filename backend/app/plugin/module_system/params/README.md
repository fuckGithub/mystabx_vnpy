# module_system/params — 参数管理

## 模块定位

系统参数（`sys_param`）的维护、按键读取与导出；启动时把参数预热到 Redis。
边界：只维护 `sys_param`；「按键读取参数」对内核暴露为 `config.params_provider` 槽位。

## 入口

| 入口类型         | 路径                                | 说明                                                                 |
| ---------------- | ----------------------------------- | -------------------------------------------------------------------- |
| HTTP 路由        | `controller.py` → `ParamsRouter`    | 容器前缀 `/system/param`，共 10 条                                   |
| ORM 模型         | `model.py`                          | `sys_param`                                                          |
| 内核槽位（实现） | `service.py::ParamsProviderImpl`    | 由父插件 `plugin.py::start()` 注入 `config.params_provider`           |
| Redis 预热       | `service.py::ParamsService`         | `init_config_service(redis)` 由父插件 `start()` 调用                 |
| 种子数据         | 由父插件声明                        | `sys_param`(config_key)                                              |

路由（10 条）：`list`、`create`、`update/{id}`、`delete`、`detail/{id}`、`export`、
`info`、`upload`、`key/{config_key}`、`value/{config_key}`。

## 依赖

- 内核槽位：无消费；**提供** `config.params_provider`（内核 `core/middlewares.py`、
  `core/ap_scheduler.py` 消费）。
- 其它插件：`system`。

## 删除影响

删除本子模块后：

- `/system/param/*` 10 条接口消失，参数不可维护。
- `sys_param` 不再自动创建，参数种子不再写入，Redis 参数缓存不再预热。
- `config.params_provider` 槽位缺失 → 内核中间件与调度器取参数返回默认值
  （演示模式/IP 名单等策略退回默认，不报错）。
