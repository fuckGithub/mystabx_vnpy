# module_system/role — 角色管理

## 模块定位

角色增删改查、启用/停用与「角色-菜单」「角色-部门」授权关系维护。
边界：只维护角色与两张关联表；角色被赋予用户是 `module_system/user` 的职责。

## 入口

| 入口类型  | 路径                            | 说明                                            |
| --------- | ------------------------------- | ----------------------------------------------- |
| HTTP 路由 | `controller.py` → `RoleRouter`  | 容器前缀 `/system/role`，共 8 条                 |
| ORM 模型  | `model.py`                      | `sys_role`、`sys_role_menus`、`sys_role_depts`   |
| 种子数据  | 由父插件声明                    | `sys_role`(code)                                |

路由（8 条）：`list`、`create`、`update/{id}`、`delete`、`detail/{id}`、
`available/setting`、`permission/setting`、`export`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（菜单树、部门树）。

## 删除影响

删除本子模块后：

- `/system/role/*` 8 条接口消失，角色与授权关系无法维护。
- `sys_role`、`sys_role_menus`、`sys_role_depts` 不再自动创建，角色种子不再写入。
- 已存在用户的角色/权限关联行保留，但无法再调整；`AuthPermission` 仍按已存关系判定。
