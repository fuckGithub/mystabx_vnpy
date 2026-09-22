# module_system/menu — 菜单管理

## 模块定位

菜单/目录/按钮三级树的增删改查与启用停用，是前端动态路由与按钮权限的数据来源。
边界：只维护 `sys_menu`；「谁拥有该菜单」由 `module_system/role` 的关联表决定。

## 入口

| 入口类型  | 路径                          | 说明                                    |
| --------- | ----------------------------- | --------------------------------------- |
| HTTP 路由 | `controller.py` → `MenuRouter` | 容器前缀 `/system/menu`，共 6 条         |
| ORM 模型  | `model.py`                    | `sys_menu`                              |
| 种子数据  | 由父插件声明                  | `sys_menu`(route_path + name)           |

路由（6 条）：`tree`、`create`、`update/{id}`、`delete`、`detail/{id}`、`available/setting`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（角色授权关系）。

## 删除影响

删除本子模块后：

- `/system/menu/*` 6 条接口消失，前端动态路由与权限码无法维护。
- `sys_menu` 不再自动创建，菜单种子不再写入。
- 已写入的菜单行保留，角色-菜单关联保留，`AuthPermission` 仍可依据既有权限码判定；
  但新插件/新功能的菜单与权限码将无法再通过接口登记。
