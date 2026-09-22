# module_system/dept — 部门管理

## 模块定位

部门/组织树（树形结构）的增删改查与启用停用。
边界：维护 `sys_dept`；数据权限的「可见部门集合」计算在内核 `core/permission.py`，
本子模块只提供模型。

## 入口

| 入口类型         | 路径                          | 说明                                                          |
| ---------------- | ----------------------------- | ------------------------------------------------------------- |
| HTTP 路由        | `controller.py` → `DeptRouter` | 容器前缀 `/system/dept`，共 6 条                              |
| ORM 模型         | `model.py`                     | `sys_dept`                                                    |
| 内核槽位（数据） | 父插件 `plugin.py::start()`    | `DeptModel` 经 `auth.data_scope_models` 注入内核数据权限过滤   |
| 种子数据         | 由父插件声明                   | `sys_dept`(code)                                              |

路由（6 条）：`tree`、`create`、`update/{id}`、`delete`、`detail/{id}`、`available/setting`。

## 依赖

- 内核槽位：无直接消费；其模型被父插件放进 `auth.data_scope_models` 供内核消费。
- 其它插件：`system`（用户/角色关联）。

## 删除影响

删除本子模块后：

- `/system/dept/*` 6 条接口消失，部门树不可维护。
- `sys_dept` 不再自动创建，部门种子不再写入。
- 内核数据权限过滤失去 `dept_model` → 跳过按部门的数据范围过滤（不再限制可见数据）。
