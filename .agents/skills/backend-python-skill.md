---
name: fastapi-admin
description: "FastAPI + SQLAlchemy + MySQL/PostgreSQL 后端开发。关键词：FastAPI、SQLAlchemy、RBAC、CRUD、Alembic、JWT、Redis。适用于开发 RESTful API、数据库模型、权限管理、定时任务、工作流编排。"
argument-hint: "API 开发、模型设计、路由注册、权限配置"
---

# FastAPI Admin 后端工程模板技术文档

> 基于 FastAPI + SQLAlchemy + MySQL/PostgreSQL 的企业级管理后端快速开发模板。
> 适用于 SaaS 管理后台、电商系统、CRM、ERP 等需要 RBAC 权限管理和动态模块化的后端项目。

## 技术栈

| 层级           | 技术                    | 说明                                                         |
| -------------- | ----------------------- | ------------------------------------------------------------ |
| 框架           | FastAPI 0.115+          | 异步高性能 Web 框架，自动生成 OpenAPI 文档                   |
| ORM            | SQLAlchemy 2.0          | 异步 ORM，支持 MySQL(asyncmy) / PostgreSQL(asyncpg) / SQLite |
| 数据库迁移     | Alembic 1.15+           | 自动生成迁移脚本，支持 CLI 命令管理                          |
| 任务调度       | APScheduler 3.11+       | 基于 cron 表达式的定时任务，支持动态启停                     |
| 工作流编排     | Prefect 3.5+            | 可视化工作流引擎（DAG 编排 + 分布式执行）                    |
| 缓存           | Redis 7+                | 令牌存储、验证码、系统配置缓存                               |
| 消息/WebSocket | websockets 15+          | 实时通信，支持 AI 流式对话等场景                             |
| AI 集成        | OpenAI SDK / Agno       | LLM 对话、MCP 协议、函数调用                                 |
| 配置管理       | Pydantic Settings 2.5+  | 环境变量驱动的分层配置                                       |
| 认证           | PyJWT + OAuth2 + bcrypt | JWT 双令牌(access + refresh)，支持滑动过期                   |
| 代码质量       | Ruff                    | 行长度 100，preview 模式，自动修复                           |
| 测试           | pytest + fakeredis（仅 token_refresh 独立使用） | 异步测试，内存 Redis 避免外部依赖        |
| 包管理         | uv / pip                | 快速依赖解析，可选国内镜像                                   |

## 项目结构

```
admin/
├── main.py                     # 应用入口（Typer CLI）
├── pyproject.toml              # 项目配置与依赖
├── alembic.ini                 # 数据库迁移配置
├── app/
│   ├── __init__.py
│   ├── common/                 # 公共枚举、常量、请求/响应模型
│   │   ├── constant.py
│   │   ├── enums.py            # 环境枚举、业务类型、Redis键名、权限策略、队列操作符
│   │   ├── request.py
│   │   └── response.py         # 统一响应格式 ResponseSchema / SuccessResponse / ErrorResponse
│   ├── config/                 # 应用配置
│   │   ├── setting.py          # Settings 类，环境变量驱动
│   │   └── path_conf.py        # 路径常量
│   ├── core/                   # 核心框架
│   │   ├── base_crud.py        # 通用 CRUD 基类（CRUDBase）
│   │   ├── base_model.py       # ORM 基类（MappedBase, ModelMixin, TenantMixin, UserMixin）
│   │   ├── base_params.py      # 分页查询参数
│   │   ├── base_schema.py      # 通用 Pydantic Schema
│   │   ├── database.py         # 数据库引擎与会话管理
│   │   ├── dependencies.py     # FastAPI 依赖注入（认证、权限）
│   │   ├── discover.py         # 动态路由发现与注册
│   │   ├── docs.py             # API 文档分类
│   │   ├── exceptions.py       # 统一异常处理
│   │   ├── http_limit.py       # 接口限流
│   │   ├── logger.py           # 日志配置（Loguru）
│   │   ├── middlewares.py      # 中间件（CORS、请求日志、GZip、演示模式拦截）
│   │   ├── permission.py       # 数据权限过滤引擎
│   │   ├── redis_crud.py       # Redis CRUD 工具
│   │   ├── router_class.py     # 操作日志路由装饰器
│   │   ├── security.py         # JWT 令牌处理
│   │   ├── serialize.py        # 序列化工具
│   │   └── validator.py        # 自定义验证器
│   ├── plugin/                 # 业务模块（动态发现）
│   │   ├── module_example/     # 示例模块
│   │   ├── module_system/      # 系统管理（用户/角色/菜单/部门/租户/字典/参数/日志）
│   │   ├── module_monitor/     # 系统监控（缓存/在线用户/服务器/资源监控）
│   │   ├── module_generator/   # 代码生成器
│   │   ├── module_task/        # 任务调度（cronjob + workflow）
│   │   └── module_xxx/         # 业务模块（按 module_ 前缀自动注册；集合随分支不同）
│   ├── scripts/                # 启动脚本
│   │   ├── init_app.py         # 应用初始化（中间件/路由/异常/文件/生命周期）
│   │   ├── initialize.py       # 数据库基础数据初始化
│   │   └── insert_menus.py     # 菜单数据导入
│   └── utils/                  # 工具函数
│       ├── captcha_util.py     # 验证码生成
│       ├── excel_util.py       # Excel 导入导出
│       ├── upload_util.py      # 文件上传
│       ├── sm_crypto_util.py  # 密码加密（国密唯一入口）
│       └── ...
└── tests/                      # 测试
```

## 核心架构设计

### 1. 动态路由发现

业务模块放置在 `app/plugin/` 下，目录以 `module_` 为前缀，系统自动扫描所有 `controller.py` 文件。

**路由注册规则**：

- 扫描路径：`module_*/**/controller.py`
- 路由前缀：`module_xxx` → `/xxx`
- 控制器要求在模块顶层定义 `APIRouter` 实例变量
- 嵌套路由支持：多级目录对应多级 URL 路径

### 2. 通用 CRUD 基类

`CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]` 提供标准数据操作：

| 方法                     | 功能         | 特性                    |
| ------------------------ | ------------ | ----------------------- |
| `get(**kwargs)`          | 条件查询单条 | 支持 `preload` 关系加载 |
| `list(search, order_by)` | 列表查询     | 支持排序、搜索条件      |
| `tree_list()`            | 树形结构查询 | 递归拼接子节点          |
| `page()`                 | 分页查询     | 自动处理排序与权限过滤  |
| `create(data)`           | 创建         | 自动填充审计字段        |
| `update(item, data)`     | 更新         | 部分更新支持            |
| `delete(ids, soft)`      | 删除         | 软/硬删除可选           |
| `batch_set_available()`  | 批量启/禁用  | 状态切换                |

**查询条件语法**（元组格式）：

```
{"field": ("like", "keyword")}           # 模糊匹配
{"field": ("in", [1,2,3])}               # IN 查询
{"field": ("between", [start, end])}     # 范围查询
{"field": (">", value)}                   # 大于
{"field": (">=", value)}                  # 大于等于
{"field": ("date", "2024-01-01")}        # 日期精确匹配
{"field": ("month", "2024-01")}          # 月份精确匹配
{"field": ("!=", value)}                 # 不等于
{"field": ("None",)}                      # IS NULL
{"field": ("not None",)}                  # IS NOT NULL
```

### 3. 多租户与数据隔离

| 特性     | 实现方式                                                                                       |
| -------- | ---------------------------------------------------------------------------------------------- |
| 多租户   | `TenantMixin` → `tenant_id` 外键关联租户表，超级管理员（is_superuser + tenant_id=1）豁免过滤   |
| 数据权限 | 5 级数据范围：仅本人 / 本部门 / 部门及以下 / 全部 / 自定义                                     |
| 权限策略 | `PermissionFilterStrategy`：DATA_SCOPE(默认) / ROLE_BASED / DEPT_BASED / SELF_ONLY / USER_ROLE |
| 软删除   | `is_deleted` + `deleted_time` 字段，全局过滤已删除记录                                         |
| 审计字段 | `UserMixin` → created_id / updated_id / deleted_id + 惰性关联关系                              |

### 4. 认证与授权体系

```
请求 → JWT 解码 → Redis 在线检查 → 权限验证 → 数据权限过滤
```

- **认证方式**：Bearer JWT (access_token + refresh_token 双令牌)
- **令牌存储**：Redis，支持滑动过期自动续期
- **权限控制**：基于 RBAC 模型，用户 → 角色 → 菜单(权限标识)
- **数据权限**：基于用户角色 `data_scope` 字段，自动拼装 SQL WHERE 条件
- **接口级别**：`AuthPermission` 依赖注入装饰器，支持多个权限标识"或"逻辑

### 5. 操作日志系统

通过 `OperationLogRoute` 路由装饰器自动记录：

- 请求路径、方法、参数
- 客户端 IP、地点、操作系统、浏览器
- 响应状态码、处理时长
- 登录日志与操作日志分类
- 支持忽略白名单函数和注解文档请求过滤

### 6. 中间件栈

| 中间件               | 顺序 | 功能                                  |
| -------------------- | ---- | ------------------------------------- |
| CustomCORSMiddleware | 1    | 跨域配置                              |
| CustomGZipMiddleware | 2    | GZip 压缩                             |
| RequestLogMiddleware | 3    | 请求日志 + IP 黑白名单 + 演示模式拦截 |

### 7. 模块化业务开发规范

每个业务模块遵循分层架构：

```
module_xxx/
├── __init__.py
├── controller.py     # 路由定义 + 参数校验
├── schema.py         # Pydantic 输入/输出模型
├── service.py        # 业务逻辑层
├── crud.py           # 数据访问层
└── model.py          # SQLAlchemy ORM 模型
```

**新模块开发流程**：

1. 在 `app/plugin/` 创建 `module_xxx/` 目录
2. 实现 `model.py`（继承 `ModelMixin` + 需要的 Mixin）
3. 实现 `schema.py`（Pydantic 输入/输出模型）
4. 实现 `crud.py`（继承 `CRUDBase` 或自行实现）
5. 实现 `service.py`（业务编排）
6. 实现 `controller.py`（定义 `APIRouter` 实例 + 路由方法）
7. 菜单数据追加到末尾（order = 最大 + 1）

**Controller 路由模板**：

```python
from fastapi import APIRouter, Depends, Path
from app.core.router_class import OperationLogRoute
from app.common.response import ResponseSchema, SuccessResponse

XxxRouter = APIRouter(route_class=OperationLogRoute, prefix="/xxx", tags=["业务模块"])

@XxxRouter.get("/list", summary="分页查询", response_model=ResponseSchema[dict])
async def get_list(page: PaginationQueryParam = Depends(), search: XxxQueryParam = Depends()):
    data = await XxxService.page_service(page_no=page.page_no, page_size=page.page_size, search=search)
    return SuccessResponse(data=data)
```

### 8. 数据库配置

支持 MySQL、PostgreSQL、SQLite 三种数据库，通过环境变量切换：

```bash
# 开发（默认自动重载）
python main.py run --env=dev

# 生产
python main.py run --env=prod
```

数据库迁移命令：

```bash
python main.py revision    # 生成迁移脚本
python main.py upgrade     # 应用迁移
```

### 9. 部署说明

本仓库已移除 Docker Compose / Dockerfile。本地与 ECS 请直接用 `uv` 跑后端（见根目录 README「快速开始」）；反向代理用宿主机 Nginx。

## 关于文档

本文档描述了基于 FastAPI 的企业级后端工程模板的核心架构与开发规范。
模板代码基于 MIT 协议开源，可用于任何商业或非商业项目。
