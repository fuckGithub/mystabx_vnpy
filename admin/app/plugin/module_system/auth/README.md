# module_system/auth — 认证授权

## 模块定位

登录/登出/令牌刷新、验证码、国密 SM2 公钥、OAuth 回调与自动登录。
边界：只负责「把凭据换成会话」（JWT + Redis 会话键），用户与权限数据本身由
`module_system/user`、`module_system/role`、`module_system/menu` 提供。

## 入口

| 入口类型     | 路径                                              | 说明                                                      |
| ------------ | ------------------------------------------------- | --------------------------------------------------------- |
| HTTP 路由    | `controller.py` → `AuthRouter`                    | 容器前缀 `/system/auth`，共 10 条（见下）                 |
| WebSocket    | 无                                                | —                                                         |
| ORM 模型     | 无                                                | 本子模块没有 `model.py`                                   |
| 业务实现     | `service.py`、`oauth_service.py`、`schema.py`     | 会话写入 Redis；`SessionInfo` 取自内核 `app/core/auth`    |

路由（10 条）：`POST /system/auth/login`、`POST /system/auth/logout`、
`POST /system/auth/token/refresh`、`GET /system/auth/captcha/get`、
`GET /system/auth/sm-public-key`、`GET /system/auth/oauth/{provider}/login`、
`GET /system/auth/oauth/{provider}/callback`、`POST /system/auth/auto-login`、
`POST /system/auth/auto-login/token`、`GET /system/auth/auto-login/users`。

## 依赖

- 内核槽位：无直接消费；认证上下文使用内核基元 `app/core/auth`（`AuthSchema`、
  `JWTPayloadSchema`、`AuthPermission`、`SessionInfo`）。
- 其它插件：`system`（同插件内的 user/role/menu 子模块与 `auth.user_resolver` 槽位）。

## 删除影响

删除本子模块后（父插件 `module_system` 仍在）：

- `/system/auth/*` 10 条接口消失：无法登录/登出/刷新令牌，验证码与 SM2 公钥接口消失，
  OAuth 与自动登录链路失效。
- 已签发的 JWT 与 Redis 会话键仍然有效，但缺少刷新入口，令牌到期后必须重新登录。
- 不涉及数据表与种子。
