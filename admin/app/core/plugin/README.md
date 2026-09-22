# app/core/plugin — 插件框架内核

## 模块定位

插件框架本体：插件目录发现、`plugin.toml` 解析、依赖拓扑排序、注册项收集与五阶段装配
（discover → setup → mount → start → stop），外加命名槽位与事件总线。
边界：**零业务代码**；只定义协议与编排，具体实现由插件在 `setup()`/`start()` 中注入。
本包是内核中被允许动态导入插件包的**白名单之一**（另一个是 `app/core/discover.py`），
且命中必须落在 `importlib.import_module(...)` 调用上（验收 A2）。

## 入口

| 入口类型       | 路径           | 说明                                                                                                                                                            |
| -------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 包导出         | `__init__.py`  | `PluginBase`/`PluginContext`/`PluginRuntime`/`PluginDir`/`PluginManifest`/`PluginRegistry`/`SeedSpec`/`RouterSpec`/`JobSpec`/`event_bus`/`provide`/`get`…       |
| 元数据解析     | `manifest.py`  | `plugin.toml` → `PluginManifest`（`CORE_PLUGIN_NAME`、`PLUGIN_DIR_PREFIX`、`plugin_name_from_dir`）                                                             |
| 目录发现与排序 | `loader.py`    | `discover_plugins`、`sort_by_dependency`、`iter_migration_dirs`、`import_plugin_models`；缺 `README.md` 记 WARNING                                              |
| 注册接口       | `context.py`   | `PluginContext`：`add_router`/`add_models`/`add_seed(_file)`/`on`/`add_startup_hook`/`add_shutdown_hook`/`add_scheduler_job`；`SeedSpec`/`RouterSpec`/`JobSpec` |
| 装配编排       | `runtime.py`   | `PluginRuntime.discover_and_setup/mount/start/stop`、`get_runtime`、`migration_locations`                                                                       |
| 注册表         | `registry.py`  | `PluginRegistry`/`PluginEntry`：本轮收集到的注册项，供运行时消费                                                                                                |
| 插件基类       | `base.py`      | `PluginBase`：`setup` 抽象；`set_redis`/`start`/`stop` 为可选空实现                                                                                             |
| 命名槽位       | `slots.py`     | `provide`/`get`/`clear_slots` + 5 个槽位常量（`SLOT_*`）                                                                                                        |
| 事件总线       | `events.py`    | `EventBus`/`event_bus`：`subscribe`/`publish`/`clear`                                                                                                           |
| 槽位契约       | `contracts.py` | 4 个 `runtime_checkable` Protocol：操作日志/参数/用户解析/任务日志                                                                                              |

## 依赖

- 内核槽位：无（框架本身即槽位机制的实现者）。
- 其它插件：无（不 import 任何 `module_*`；只按目录名动态导入）。

## 删除影响

不可删除：删除后所有插件都无法被发现与装配，应用只剩内建路由与 `/docs`，
且除 `/common/health/`、`/common/health/ready/` 之外的全部业务接口消失、5 个槽位永远缺失。

## 迁移后自检清单

把任意模块迁移为插件后，逐条核对。前 4 条是**静默失败**（不报错但功能整体失效），
最容易漏，务必优先确认。

### 一、会导致静默失效的项（必查）

1. **入口变量必须存在**
   每个 `app/plugin/module_<name>/plugin.py` 必须有模块级 `PLUGIN = Plugin()`。
   缺失时加载器只记一条 ERROR，然后**静默跳过整个插件**——路由、模型、种子、槽位全没了。

2. **不要在 `plugin.py` 里重复挂载控制器**
   `module_*/**/controller.py` 顶层的 `APIRouter` 由 `app/core/discover.py::get_dynamic_router()`
   以 `/{suffix}` 为容器前缀自动挂载。若 `plugin.py` 再用 `ctx.add_router()` 声明一次，
   就是双挂载（同一「方法 + 路径」重复注册）。
   非 `controller.py` 的路由（如 WebSocket）才走 `ctx.add_router()`。
   守卫：`tests/test_route_snapshot.py::test_no_duplicate_routes`。

3. **模型路径要显式声明**
   用 `ctx.add_models(*MODEL_PATHS)` 列出全部模型模块。只 import 单个模型会让
   字符串命名的 `relationship()` 因映射器注册表不完整而抛
   `KeyError: 'UserModel'` / `InvalidRequestError`，且往往只在别的测试里才炸。

4. **槽位要成对核对**
   提供方在 `start()` 里 `provide(...)`，消费方通过 `PluginContext` 取。
   消费方先用 `get(...)` 判空，缺失时应当**降级并记日志**，不可静默丢弃写入。
   `python -m pytest tests/test_plugin_decoupling.py` 可确认内核零插件引用。

### 二、结构与元数据

5. `plugin.toml` 存在且 `name` 与目录名一致（`module_` 前缀剥离后），`dependencies` 无环。
6. `README.md` 存在（缺失只记 WARNING，但 `tests/test_module_readme.py` 会红）。
7. `plugin.py`、`plugin.toml`、`README.md`、`seeds/` 均已随迁移一并移动到插件目录。

### 三、种子与迁移

8. `add_seed_file(...)` 的声明顺序满足外键依赖（如 tenant → user → user_roles）。
   幂等性由 `tests/core/test_seed.py`、`tests/test_seed_pipeline.py` 覆盖。
9. **自带迁移的插件必须登记到 `admin/alembic.ini`**
   把 `%(here)s/app/plugin/module_<name>/migrations` 追加进 `version_locations`
   （空格分隔）。原因见该文件注释：`alembic heads`/`history` **不执行 `env.py`**，
   只在 `env.py` 里 `set_main_option` 会让插件迁移**静默不出现**。
   自检：临时放一个 revision 进该目录，`alembic heads` 应多出一个 head。

### 四、收尾验证

10. 全量 `pytest` 不新增失败；路由快照 `tests/test_route_snapshot.py` 双向相等。
11. 最小可运行集：`tests/test_plugin_min_set.py`（含内核发现器与 `app.plugin.__path__` 双缝注入）。
12. 真机冒烟：启动后日志含「插件 setup 完成」「插件启动阶段完成」，无 `ERROR`/`Traceback`。
    `REDIS_ENABLE=False` 时自动降级（限流器→InMemoryLimiter、中间件→默认值）。

### 五、已知环境坑（非插件缺陷，勿误判）

- `tests/conftest.py` 设置 `REDIS_ENABLE=False`，应用自动降级（限流器→InMemoryLimiter，
  中间件→默认值）。`test_token_refresh.py` 自行创建 fakeredis 实例。
- ~~`fastapi_limiter` 遍历 `request.app.routes` 假设节点有 `.path`~~ —— **已于 fastapi-limiter 0.2.0 升级时修复**。
  `__call__` 改用 `request.scope["endpoint"]` 定位端点，`build_limiter()` 根据 Redis 可用性
  选择后端（`RedisLimiter` / `InMemoryLimiter`，均按客户端 key 隔离）。详见
  `app/core/http_limit.py`。
