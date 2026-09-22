# Mystabx Admin — 全栈开发框架模板

基于 FastapiAdmin 迁入的 FastAPI + Vue3 + UniApp 全栈开发框架模板（本仓库 `main`）。

> 📖 **项目结构详情见 [README.md](./README.md#-工程结构)**，本文档仅包含 Agent 开发所需的快捷参考。

## 技术栈

| 层              | 技术                                               | 说明                            |
| --------------- | -------------------------------------------------- | ------------------------------- |
| 后端            | FastAPI + SQLAlchemy 2.0 + MySQL/PostgreSQL/SQLite | 异步 ORM，自动迁移              |
| 管理后台        | Vue 3 + Element Plus + TypeScript + Vite           | 动态路由/菜单，权限控制         |
| 移动端(UniApp)  | UniApp + Wot UI + UnoCSS + Pinia                   | 跨平台（H5/微信小程序/App）     |
| 移动端(Flutter) | Flutter + Riverpod + GoRouter + TDesign            | 跨平台（Android/iOS/Web/桌面）  |
| 部署            | 本机 / ECS 直接运行（非 Docker）                   | MySQL + Redis + Backend；反向代理可用宿主机 Nginx |
| 包管理          | 后端: uv / pip                                     | 前端: pnpm                      |
| 数据库迁移      | Alembic                                            | 自动生成迁移脚本                |
| 认证            | JWT + OAuth2                                       | 滑动过期 + 多租户               |
| 权限            | RBAC + 数据权限                                    | 角色/菜单/部门数据隔离          |

> ⚡ 快速开始、后端开发、插件开发等通用内容详见 [README.md](./README.md#-快速开始)。

## 默认端口

| 组件         | 默认地址                              |
| ------------ | ------------------------------------- |
| Web 管理后台 | `http://127.0.0.1:5173`               |
| UniApp H5    | `http://127.0.0.1:6120`               |
| Flutter Web  | `http://127.0.0.1:6150`               |
| 后端 API     | `http://127.0.0.1:18080`              |
| Swagger 文档 | `http://127.0.0.1:18080/api/v1/docs`  |
| API 前缀     | `/api/v1`                             |

> 端口对齐 mystabx 产品：后端 / ECS 为 **18080**（原 fastapiadmin **6100**）；Web Vite 为 **5173**（原 **6110**）。
> MySQL 库名 **mystabx_vnpy**（RDS）；Redis 在 ECS `47.102.208.231:6379`（见 `.env.ecs.example`）。

## 关键配置项

见 `admin/app/config/setting.py`，主要配置：

| 配置                 | 默认值  | 说明                                |
| -------------------- | ------- | ----------------------------------- |
| `DATABASE_TYPE`      | `mysql` | 数据库类型（mysql/postgres/sqlite） |
| `CAPTCHA_ENABLE`     | `True`  | 是否启用登录验证码                  |
| `CORS_ORIGIN_ENABLE` | `False` | 是否启用跨域                        |
| `REDIS_ENABLE`       | `True`  | 是否启用 Redis                      |
| `SQL_DB_ENABLE`      | `True`  | 是否启用数据库                      |

## 项目约定

- Python: `ruff`（行长度 100）+ 4-space 缩进
- TypeScript/Vue: ESLint 9 + Prettier（2-space 缩进）
- 新路由在 `module_xxx/controller.py` 中定义，自动注册
- 新菜单 order 追加末尾
- 公共函数需要类型提示 + Google 风格 docstring
- **静态检查必须两条都过**：`ruff check` **和** `pyright`。ruff 不做类型检查，
  只跑 ruff 会漏掉参数不匹配、属性访问、协程漏 `await` 等真实缺陷
  （详见 `admin/AGENTS.md`「验证门禁」）

## 后端插件架构（重要）

后端已全面插件化：**全部业务模块都在 `admin/app/plugin/module_*/` 下，`app/api/` 已删除**。
插件按目录发现，无集中注册文件。

新增/迁移模块时的四条静默失败红线（不报错但功能整体失效）：

1. `plugin.py` 必须有模块级 `PLUGIN = Plugin()`；缺失会**静默跳过整个插件**。
2. 不要在 `plugin.py` 里 `ctx.add_router()` 重复挂载 `controller.py` 顶层 `APIRouter`
   （已由 `app/core/discover.py` 自动挂载，重复即双挂载）。
3. 模型必须显式声明 `ctx.add_models(*MODEL_PATHS)`，否则映射器注册表不完整。
4. 插件自带迁移必须登记到 `admin/alembic.ini` 的 `version_locations`
   （`alembic heads`/`history` 不执行 `env.py`，只写在 env.py 里会静默漏报）。

完整自检清单见 [`admin/app/core/plugin/README.md`](./admin/app/core/plugin/README.md)。

## Agent 指令文件（Skills）

每次启动会话时，根据当前工作内容加载对应 skill：

| Skill         | 适用场景                         | 文件路径                                 |
| ------------- | -------------------------------- | ---------------------------------------- |
| 后端 API 开发 | FastAPI + SQLAlchemy + RBAC      | `.agents/skills/backend-python-skill.md` |
| 移动端开发    | UniApp + Wot UI + 跨端适配       | `.agents/skills/mobile-unibest-skill.md` |
| 管理后台开发  | Vue3 + Element Plus + 动态路由   | `.agents/skills/web-vue3-skill.md`       |
| Wot UI 组件   | wd-\* 组件选型/API 查询/主题定制 | `.agents/skills/wot-ui-skill.md`         |

详细信息见各子目录的 `AGENTS.md`：

- `admin/AGENTS.md` — 后端专用指令
- `web/AGENTS.md` — 管理后台指令
- `uniapp/AGENTS.md` — UniApp 移动端指令
- `flutter/AGENTS.md` — Flutter 移动端指令

> Docker 相关目录与编排已移除；部署请用本机 `uv` / `pnpm` 或 ECS 上的 systemd / 进程方式，勿再引用 `docker/`。
