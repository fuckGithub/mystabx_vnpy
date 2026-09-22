# module_system/user — 用户管理

## 模块定位

系统用户账号的增删改查、个人中心（头像/资料/改密）、注册与找回密码、导入导出。
边界：管理 `sys_user` 与两张关联表；登录态与令牌由 `module_system/auth` 负责。
额外职责：通过 `UserResolverImpl` 向内核提供 `auth.user_resolver` 槽位实现。

## 入口

| 入口类型         | 路径                                     | 说明                                                        |
| ---------------- | ---------------------------------------- | ----------------------------------------------------------- |
| HTTP 路由        | `controller.py` → `UserRouter`           | 容器前缀 `/system/user`，共 16 条                            |
| ORM 模型         | `model.py`                               | `sys_user`、`sys_user_roles`、`sys_user_positions`           |
| 内核槽位（实现） | `service.py::UserResolverImpl`           | 由 `module_system/plugin.py::start()` 注入 `auth.user_resolver` |
| 种子数据         | 由父插件声明                             | `sys_user`(username)、`sys_user_roles`(user_id+role_id)      |

路由（16 条）：`list`、`create`、`update/{id}`、`delete`、`detail/{id}`、
`available/setting`、`export`、`import/data`、`import/template`、`register`、
`forget/password`、`reset/password`、`current/info`、`current/info/update`、
`current/password/change`、`current/avatar/upload`。

## 依赖

- 内核槽位：无消费；**提供** `auth.user_resolver`（内核 `core/dependencies.get_current_user` 消费）。
- 其它插件：`system`（角色/部门/岗位数据）。

## 删除影响

删除本子模块后：

- `/system/user/*` 16 条接口消失，用户与个人中心功能不可用。
- `sys_user`、`sys_user_roles`、`sys_user_positions` 不再自动创建，用户种子不再写入。
- `auth.user_resolver` 槽位缺失 → 内核 `get_current_user` 一律 401，**全站接口不可用**
  （这是本子模块与其它子模块最大的区别）。
