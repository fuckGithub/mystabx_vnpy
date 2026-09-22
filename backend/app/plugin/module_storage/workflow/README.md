# module_storage/workflow — 存储工作流管理

## 模块定位

存储工作流编排与调度，将多个存储操作组合为可执行的工作流定义。
边界：工作流 CRUD，不涉及具体的文件传输执行。

## 入口

| 入口类型 | 路径                | 说明                                       |
| -------- | ------------------- | ------------------------------------------ |
| HTTP 路由 | `controller.py` → `StorageWorkflowRouter` | 容器前缀 `/storage/workflow`，5 条路由 |
| ORM 模型  | `model.py`          | 表 `storage_workflow`                      |

路由（5 条）：`list`、`detail/{id}`、`create`、`update/{id}`、`delete`。

## 依赖

- 内核槽位：无消费、无提供。
- 其它插件：依赖 `module_storage/node` 和 `module_storage/transfer`（工作流步骤引用节点和传输）。
- 第三方：无直接依赖。

## 删除影响

删除本子模块后：

- `/storage/workflow/*` 5 条接口消失。
- 表 `storage_workflow` 不再自动创建，存储工作流无法管理。
- 已定义的工作流将无法执行。
