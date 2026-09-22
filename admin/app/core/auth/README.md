# app/core/auth — 内核认证基元

## 模块定位

内核认证与权限的最小基元：当前用户上下文、JWT 载荷、权限校验依赖、会话信息与结构化用户协议。
边界：**不含任何具体业务模型**（用户/角色/菜单数据不在内核），因此可被任意插件依赖而不产生
反向耦合；用户对象的加载经 `auth.user_resolver` 槽位在运行时注入。

## 入口

| 入口类型   | 路径            | 说明                                                                                                                                                          |
| ---------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 包导出     | `__init__.py`   | `AuthSchema`/`JWTPayloadSchema`/`SessionInfo`/`UserLike`；`AuthPermission` 由 PEP 562 `__getattr__` 惰性再导出（避免与 `app/core/dependencies` 循环导入）     |
| 认证上下文 | `schema.py`     | `AuthSchema`（用户上下文）、`JWTPayloadSchema`（JWT 载荷）、`UserLike`（结构化用户协议）                                                                      |
| 权限依赖   | `permission.py` | `AuthPermission([...])`：controller 直接 `Depends` 使用；数据权限模型经 `auth.data_scope_models` 槽位取                                                       |
| 会话模型   | `session.py`    | `SessionInfo`：登录时序列化进 JWT `sub`（字段：`name`/`session_id`/`user_id`/`user_name`/`ipaddr`/`login_location`/`os`/`browser`/`login_time`/`login_type`） |

## 依赖

- 内核槽位：消费 `auth.user_resolver`（`app/core/dependencies.py::get_current_user`）与
  `auth.data_scope_models`（`app/core/permission.py` 的数据范围过滤）。
- 其它插件：无静态依赖（槽位缺失时降级：前者 401，后者跳过数据权限过滤）。

## 删除影响

不可删除：全部插件的 controller 都 `Depends(AuthPermission(...))` 并以 `AuthSchema` 作类型标注，
删除后应用无法导入（ImportError），而非降级。
