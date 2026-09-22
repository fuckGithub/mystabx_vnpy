# module_system/tenant — 租户管理

## 模块定位

多租户（`sys_tenant`）的增删改查、启用停用与详情查询。
边界：只维护租户主数据；租户维度的数据隔离由各业务表自身的租户字段配合内核逻辑实现。

## 入口

| 入口类型  | 路径                            | 说明                              |
| --------- | ------------------------------- | --------------------------------- |
| HTTP 路由 | `controller.py` → `TenantRouter` | 容器前缀 `/system/tenant`，共 6 条 |
| ORM 模型  | `model.py`                      | `sys_tenant`                      |
| 种子数据  | 由父插件声明                    | `sys_tenant`(code)                |

路由（6 条）：`list`、`create`、`update/{id}`、`delete`、`detail/{id}`、`available/setting`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`。

## 删除影响

删除本子模块后：

- `/system/tenant/*` 6 条接口消失，租户不可维护。
- `sys_tenant` 不再自动创建，租户种子不再写入（该种子是其它种子的前置表之一）。
- 已存在的租户行保留，业务数据中的租户字段不受影响。
