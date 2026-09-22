# module_system — 系统管理（最小可运行集）

## 模块定位

最小可运行集成员：认证授权、用户/角色/菜单/部门/岗位/租户/字典/参数/公告/操作日志。
边界：只提供系统管理自身的 HTTP 接口与数据表；对内核只经 **内核槽位**（设计 §4.7）提供
参数、操作日志、用户解析与数据权限模型，不向其它插件暴露可 import 的接口。

## 入口

| 入口类型          | 路径                                 | 说明                                                                                                        |
| ----------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| 插件入口          | `plugin.py`                          | `class Plugin(PluginBase)`：声明 11 项 `MODEL_PATHS` + 10 条种子；`start()` 注入 4 个槽位并预热配置/字典缓存 |
| HTTP 路由         | `<子模块>/controller.py`             | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/system`（11 个子路由，共 97 条）                             |
| WebSocket 路由    | 无                                   | —                                                                                                           |
| ORM 模型          | `<子模块>/model.py`                  | 13 张表，见下表                                                                                             |
| 种子数据          | `seeds/data/*.json`                  | 10 个文件，见表                                                                                             |
| 内核槽位（提供）  | `plugin.py::start()`                 | `log.operation_sink`、`config.params_provider`、`auth.user_resolver`、`auth.data_scope_models`              |
| 定时任务          | 无                                   | 未调用 `ctx.add_scheduler_job`                                                                              |
| 事件订阅          | 无                                   | 未调用 `ctx.on(...)`；`auth.login`/`auth.logout` 事件当前无发布者                                           |

子路由（`controller.py` → 容器前缀）：

| 子模块   | 路由前缀                          | 条数 |
| -------- | --------------------------------- | ---- |
| `auth`   | `/system/auth`                    | 10   |
| `dept`   | `/system/dept`                    | 6    |
| `dict`   | `/system/dict/type`、`/dict/data` | 16   |
| `log`    | `/system/log`                     | 4    |
| `menu`   | `/system/menu`                    | 6    |
| `notice` | `/system/notice`                  | 8    |
| `params` | `/system/param`                   | 10   |
| `position` | `/system/position`              | 7    |
| `role`   | `/system/role`                    | 8    |
| `tenant` | `/system/tenant`                  | 6    |
| `user`   | `/system/user`                    | 16   |

ORM 模型（`__tablename__`）：`sys_user`、`sys_user_roles`、`sys_user_positions`、
`sys_role`、`sys_role_menus`、`sys_role_depts`、`sys_menu`、`sys_dept`、`sys_position`、
`sys_tenant`、`sys_dict_type`、`sys_dict_data`、`sys_param`、`sys_notice`、`sys_log`。

> `MODEL_PATHS` 还包含 `auth.schema`：该模块无 ORM 模型，随模型清单一起导入以满足
> SQLAlchemy mapper 完整注册表的要求。

种子（表 → 自然键）：`sys_tenant`→`code`、`sys_menu`→(`route_path`,`name`)、
`sys_param`→`config_key`、`sys_dept`→`code`、`sys_role`→`code`、`sys_dict_type`→`dict_type`、
`sys_dict_data`→(`dict_type`,`dict_value`)、`sys_position`→`name`、`sys_user`→`username`、
`sys_user_roles`→(`user_id`,`role_id`)。

## 依赖

- 内核槽位：**无**（本插件只提供，不消费任何槽位）。
- 其它插件：**无**（`plugin.toml` 未声明 `depends`）。
- 内核代码：`app/core/*`（`AuthSchema`/`AuthPermission`/`PluginBase`/`PluginContext`）。

## 删除影响

删除本目录后（应用仍可启动，属预期降级）：

- `/system/*` 下 **97 条**接口全部消失（认证类接口消失后，除白名单外的请求返回 401）。
- 15 张表不再自动创建（`sys_*`；已存在的表不会被删除，数据保留）。
- 10 个种子文件不再写入（菜单/权限/字典/参数/部门/角色/租户/用户引导数据缺失）。
- 4 个内核槽位缺失：用户解析失效（`auth.user_resolver` → 401）、数据权限过滤跳过
  （`auth.data_scope_models`）、操作日志不落库（`log.operation_sink`，仍写文件日志）、
  参数读取退回默认值（`config.params_provider`）。
- 配置与数据字典不再预热到 Redis（`ParamsService.init_config_service` /
  `DictDataService.init_dict_service` 不再被调用）。
