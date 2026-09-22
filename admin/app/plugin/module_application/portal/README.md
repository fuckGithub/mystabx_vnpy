# module_application/portal — 门户应用与插件清单

## 模块定位

门户应用（`app_portal`）的 CRUD/可用性设置，以及只读的「插件清单」接口。
边界：插件清单数据不在本子模块维护，由 `plugin_manifest.py` 委托内核
`discover_plugins()` + `plugin.toml` 解析得到。

## 入口

| 入口类型  | 路径                               | 说明                                              |
| --------- | ---------------------------------- | ------------------------------------------------- |
| HTTP 路由 | `controller.py` → `PortalRouter`   | 容器前缀 `/application/portal`，共 7 条           |
| ORM 模型  | `model.py`                         | 表 `app_portal`                                   |
| 业务实现  | `service.py`、`plugin_manifest.py` | `plugin_manifest.py` 复用内核插件发现器渲染清单行 |

路由（7 条）：`GET /application/portal/list`、`POST /application/portal/create`、
`PUT /application/portal/update/{id}`、`DELETE /application/portal/delete`、
`GET /application/portal/detail/{id}`、`PATCH /application/portal/available/setting`、
`GET /application/portal/plugins`。

## 依赖

- 内核槽位：无。
- 内核函数：`app/core/plugin/loader.py::discover_plugins`（清单来源）。
- 其它插件：`system`（鉴权依赖 `auth.user_resolver`）。

## 删除影响

删除本子模块后：

- `/application/portal/*` 7 条接口消失（含 `/plugins` 清单接口）。
- 表 `app_portal` 不再自动创建；已存在的应用行与菜单行保留。
- 其它插件不受影响（清单是只读派生数据）。
