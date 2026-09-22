# module_storage/transfer — 传输任务管理

## 模块定位

文件传输任务管理（上传/下载/同步），与存储节点配合完成数据传输。
边界：传输任务 CRUD，不涉及节点配置或工作流编排。

## 入口

| 入口类型 | 路径                | 说明                                      |
| -------- | ------------------- | ----------------------------------------- |
| HTTP 路由 | `controller.py` → `StorageTransferRouter` | 容器前缀 `/storage/transfer`，5 条路由 |
| ORM 模型  | `model.py`          | 表 `storage_transfer`                     |

路由（5 条）：`list`、`detail/{id}`、`create`、`update/{id}`、`delete`。

## 依赖

- 内核槽位：无消费、无提供。
- 其它插件：依赖 `module_storage/node`（传输任务关联存储节点）。
- 第三方：无直接依赖。

## 删除影响

删除本子模块后：

- `/storage/transfer/*` 5 条接口消失。
- 表 `storage_transfer` 不再自动创建，传输任务无法管理。
- 工作流中涉及传输的步骤将失效。
