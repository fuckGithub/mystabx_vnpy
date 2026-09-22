# module_example/demo01 — 示例模块 01

## 模块定位

与 `demo` 同构的第二个示例子模块，用于验证「同插件内多子模块、多路由前缀」的挂载形态。
边界：仅演示与自测（表 `gen_demo01`）。

## 入口

| 入口类型  | 路径                                 | 说明                                |
| --------- | ------------------------------------ | ----------------------------------- |
| HTTP 路由 | `controller.py` → `Demo01Router`     | 容器前缀 `/example/demo01`，共 9 条 |
| ORM 模型  | `model.py`                           | 表 `gen_demo01`                     |
| 业务实现  | `service.py`、`crud.py`、`schema.py` | 标准三层结构                        |

路由（9 条）：`GET /example/demo01/list`、`POST /example/demo01/create`、
`PUT /example/demo01/update/{id}`、`DELETE /example/demo01/delete`、
`GET /example/demo01/detail/{id}`、`PATCH /example/demo01/available/setting`、
`POST /example/demo01/export`、`POST /example/demo01/import`、
`POST /example/demo01/download/template`。

## 依赖

- 内核槽位：无。
- 其它插件：无（父插件 `module_example`）。

## 删除影响

删除本子模块后：

- `/example/demo01/*` 9 条接口消失。
- 表 `gen_demo01` 不再自动创建（数据保留）。
- `demo` 子模块与其它插件不受影响。
