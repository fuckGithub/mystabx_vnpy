# module_generator/gencode — 生成器核心（接口 / 模板 / 工具）

## 模块定位

生成器主体：生成配置的 CRUD 接口、模板渲染与输出路径映射。
边界：只做「表/字段配置 → 模板渲染 → 文件（或 ZIP）」；菜单与按钮权限的写入经
`module_system` 的 `MenuCRUD` 完成。

## 入口

| 入口类型  | 路径                                                   | 说明                                                                                           |
| --------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| HTTP 路由 | `controller.py` → `GenRouter`                          | 容器前缀 `/generator/gencode`，共 12 条                                                        |
| ORM 模型  | `model.py`                                             | 表 `gen_table`、`gen_table_column`                                                             |
| 模板目录  | `templates/python/`、`templates/ts/`、`templates/vue/` | `python/` 下 6 个业务模板 + 3 个插件骨架模板（`plugin.toml.j2`/`plugin.py.j2`/`README.md.j2`） |
| 工具      | `tools/jinja2_template_util.py`                        | `prepare_context`、`get_template_list`、`get_file_name`（输出路径映射）                        |
| 工具      | `tools/gen_util.py`                                    | 命名/类型转换等生成期工具                                                                      |
| 业务实现  | `service.py`、`crud.py`、`schema.py`                   | 预览、写入本地、ZIP 打包下载三条路径共用同一模板清单                                           |

路由（12 条）：`GET /generator/gencode/{list,db/list,detail/{table_id},preview/{table_id},sync_db/preview/{table_name}}`、
`POST /generator/gencode/{create,import,output/{table_name},sync_db/{table_name}}`、
`PUT /generator/gencode/update/{table_id}`、`DELETE /generator/gencode/delete`、
`PATCH /generator/gencode/batch/output`。

输出路径（`get_file_name`）：插件骨架写到插件根
`backend/app/plugin/{module_xxx}/{plugin.toml,plugin.py,README.md}`，业务文件写到
`backend/app/plugin/{module_xxx}/{module_name}/`，前端写到
`frontend/src/{api,views}/{module_xxx}/{module_name}*`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（菜单/按钮权限写入）。
- 第三方：`jinja2`。

## 删除影响

删除本子模块后：

- `/generator/gencode/*` 12 条接口消失，生成器无入口。
- 表 `gen_table`、`gen_table_column` 不再自动创建。
- 模板与工具（`templates/`、`tools/`）随本目录一起删除；`module_generator` 插件随之名存实亡。
- 无种子、无槽位、无定时任务。
