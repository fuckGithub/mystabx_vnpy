# module_system/position — 岗位管理

## 模块定位

岗位（`sys_position`）的增删改查、启用停用与导出。
边界：只维护岗位主数据；用户与岗位的关联行存在 `sys_user_positions`（属 `user` 子模块）。

## 入口

| 入口类型  | 路径                              | 说明                                |
| --------- | --------------------------------- | ----------------------------------- |
| HTTP 路由 | `controller.py` → `PositionRouter` | 容器前缀 `/system/position`，共 7 条 |
| ORM 模型  | `model.py`                        | `sys_position`                      |
| 种子数据  | 由父插件声明                      | `sys_position`(name)；当前为空数组占位 |

路由（7 条）：`list`、`create`、`update/{id}`、`delete`、`detail/{id}`、
`available/setting`、`export`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`。

## 删除影响

删除本子模块后：

- `/system/position/*` 7 条接口消失，岗位不可维护。
- `sys_position` 不再自动创建，岗位种子不再写入（当前种子为空数组，无实际行损失）。
- 已存在的岗位行与用户-岗位关联行保留。
