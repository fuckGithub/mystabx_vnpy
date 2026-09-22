# module_generator — 代码生成

## 模块定位

以数据库表为输入、以 Jinja2 模板为输出的 CRUD 代码生成器：表/字段配置的同步与维护、
代码预览、写入本地工程、打包下载。
边界：只生成代码与菜单行；生成结果写入 `backend/app/plugin/{module_xxx}/`（并自 A10 起
自带 `plugin.toml`/`plugin.py`/`README.md` 插件骨架），前端模板产出 TS/Vue 文件。

## 入口

| 入口类型       | 路径                                    | 说明                                                                              |
| -------------- | --------------------------------------- | --------------------------------------------------------------------------------- |
| 插件入口       | `plugin.py`                             | `class Plugin(PluginBase)`：`setup()` 声明 `ctx.add_models("gencode.model")`      |
| HTTP 路由      | `gencode/controller.py`                 | 由 `app/core/discover.py` 扫描挂载，容器前缀 `/generator`（1 个子路由，12 条）    |
| WebSocket 路由 | 无                                      | —                                                                                 |
| ORM 模型       | `gencode/model.py`                      | 表 `gen_table`、`gen_table_column`                                                |
| 模板           | `gencode/templates/{python,ts,vue}/`    | 渲染源（Python: controller/service/crud/schema/model/`__init__` + 插件骨架 3 件） |
| 模板工具       | `gencode/tools/jinja2_template_util.py` | 上下文准备、模板清单、输出路径映射                                                |
| 内核槽位       | 无                                      | 既不提供也不消费                                                                  |
| 种子数据       | 无                                      | —                                                                                 |
| 定时任务       | 无                                      | 未调用 `ctx.add_scheduler_job`                                                    |
| 事件订阅       | 无                                      | 未调用 `ctx.on(...)`                                                              |

子路由：

| 子模块    | 路由前缀             | 条数 |
| --------- | -------------------- | ---- |
| `gencode` | `/generator/gencode` | 12   |

## 依赖

- 内核槽位：无。
- 其它插件：`system`（`plugin.toml` 声明 `depends = ["system"]`；生成流程会经
  `MenuCRUD` 写入菜单/按钮权限，属同仓插件间**直接 import** 的既有耦合）。
- 第三方：`jinja2`。

## 删除影响

删除本目录后：

- `/generator/gencode/*` 12 条接口消失，代码生成功能整体不可用。
- `gen_table`、`gen_table_column` 不再自动创建（已配置的生成规则保留但无入口）。
- 模板与工具一并删除（`app/plugin/module_generator/gencode/templates` 属本目录）。
- 无种子、无槽位、无定时任务；其它插件与内核不受影响（运行期无反向依赖）。
