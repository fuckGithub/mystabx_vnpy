# module_storage/node — 存储节点管理

## 模块定位

存储节点的接入与配置管理，支持多存储后端的统一抽象。
边界：节点 CRUD，不涉及文件传输或工作流编排。

## 入口

| 入口类型 | 路径                | 说明                                    |
| -------- | ------------------- | --------------------------------------- |
| HTTP 路由 | `controller.py` → `StorageNodeRouter` | 容器前缀 `/storage/node`，5 条路由 |
| ORM 模型  | `model.py`          | 表 `storage_node`                       |

路由（5 条）：`list`、`detail/{id}`、`create`、`update/{id}`、`delete`。

## 依赖

- 内核槽位：无消费、无提供。
- 其它插件：无。
- 第三方：无直接依赖。

## 删除影响

删除本子模块后：

- `/storage/node/*` 5 条接口消失。
- 表 `storage_node` 不再自动创建，存储节点无法管理。
- 依赖节点的传输任务和工作流将无法正常运行。
