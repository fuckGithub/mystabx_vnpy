# module_example/demo — 示例模块

## 模块定位

生成器常见产出的标准 CRUD 示例：列表/详情/增删改/启用设置/导入导出/下载模板。
边界：仅演示与自测（表 `gen_demo`），不含业务规则。

## 入口

| 入口类型  | 路径                                 | 说明                              |
| --------- | ------------------------------------ | --------------------------------- |
| HTTP 路由 | `controller.py` → `DemoRouter`       | 容器前缀 `/example/demo`，共 9 条 |
| ORM 模型  | `model.py`                           | 表 `gen_demo`                     |
| 业务实现  | `service.py`、`crud.py`、`schema.py` | 标准三层结构                      |

路由（9 条）：`GET /example/demo/list`、`POST /example/demo/create`、
`PUT /example/demo/update/{id}`、`DELETE /example/demo/delete`、
`GET /example/demo/detail/{id}`、`PATCH /example/demo/available/setting`、
`POST /example/demo/export`、`POST /example/demo/import`、
`POST /example/demo/download/template`。

## 依赖

- 内核槽位：无。
- 其它插件：无（父插件 `module_example`）。

## 删除影响

删除本子模块后：

- `/example/demo/*` 9 条接口消失。
- 表 `gen_demo` 不再自动创建（数据保留）。
- `demo01` 子模块与其它插件不受影响。
