# 后端模块创建模板

## 目录结构

创建新模块时，在 `backend/app/plugin/` 下创建以下目录结构：

```
module_<module_name>/          # 顶级插件目录（必须以 module_ 开头）
    __init__.py                 # 空文件
    README.md                   # 模块文档（必需，见下「0. README.md」）
    plugin.toml                 # 插件元数据配置
    plugin.py                   # 插件入口（必须绑定 PLUGIN = Plugin()）
    <module_name>/              # 子模块目录（与 module_name 同名）
        __init__.py             # 空文件
        README.md               # 子模块文档（必需）
        controller.py           # API路由和权限控制
        model.py                # SQLAlchemy ORM模型
        schema.py               # Pydantic请求/响应模型
        service.py              # 业务逻辑层
        crud.py                 # 数据库操作层
```

### 路由注册规则（由 app/core/discover.py 自动处理）

1. 扫描路径：`module_*/**/controller.py`
2. 容器前缀：`module_<name>` → `/<name>`（如 `module_system` → `/system`）
3. controller.py 顶层必须定义 `APIRouter` 实例变量（如 `XxxRouter = APIRouter(...)`）
4. 每层目录都需要 `__init__.py`（可以为空）

---

## 各文件模板

### 0. README.md — 模块文档（必需）

每个模块目录（插件根 + 其每个含 `__init__.py` 的子模块目录）都必须有 `README.md`，
且**逐字**包含 4 个固定小节标题：`## 模块定位` / `## 入口` / `## 依赖` / `## 删除影响`。
缺失时 `PluginLoader.discover()` 记 WARNING，`tests/test_module_readme.py` 直接 FAIL。
内容骨架（复制后替换方括号内容，事实必须来自 `plugin.py` / `plugin.toml` / `controller.py`，
拿不准写 `待确认`，不要编）：

```markdown
# module\_[插件名] — [中文标题]

## 模块定位

[一两句：做什么、边界在哪、属于哪一层]

## 入口

| 入口类型       | 路径                       | 说明                                                   |
| -------------- | -------------------------- | ------------------------------------------------------ |
| 插件入口       | `plugin.py`                | `class Plugin(PluginBase)`；`PLUGIN = Plugin()` 不可省 |
| HTTP 路由      | `[子模块]/controller.py`   | `[XxxRouter]`，容器前缀 `/[name]`（N 条）              |
| WebSocket 路由 | [无 / `[子模块]/ws.py`]    | [是否由 `ctx.add_router` 声明、限流器]                 |
| ORM 模型       | `[子模块]/model.py`        | 表 `[table_name]`                                      |
| 种子数据       | [无 / `seeds/data/*.json`] | [表 + 自然键]                                          |
| 内核槽位       | [无 / 提供 or 消费的槽位]  | [说明]                                                 |
| 定时任务       | [无 / 任务入口]            | [`ctx.add_scheduler_job`]                              |
| 事件订阅       | [无 / 事件名]              | [`ctx.on(...)`]                                        |

## 依赖

- 内核槽位：[无 / 槽位名]
- 其它插件：[无 / 插件名（`plugin.toml` 的 `depends`）]

## 删除影响

删除本目录后：[路由前缀 / 表 / 菜单 / 定时任务 / 内核槽位的具体后果]
```

### 1. plugin.toml — 插件配置

```toml
name = "<module_name>"
title = "<中文模块标题>"
version = "1.0.0"
description = "<模块功能描述>"
optional = false
tags = ["<tag1>", "<tag2>"]
```

---

### 2. model.py — 数据库模型

```python
from sqlalchemy import VARCHAR, Integer, String, Boolean, DECIMAL, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin


class <ModuleName>Model(ModelMixin):
    """
    <表中文名>
    """

    __tablename__: str = "<table_name>"
    __table_args__: dict[str, str] = {"comment": "<表注释>"}
    __loader_options__: list[str] = []

    # 字段示例 - 根据实际业务修改
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="名称"
    )
    phone: Mapped[str] = mapped_column(
        VARCHAR(20),
        nullable=False,
        unique=True,
        comment="联系电话"
    )
    address: Mapped[str | None] = mapped_column(
        VARCHAR(500),
        nullable=True,
        comment="地址"
    )
    status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="状态(0-禁用, 1-启用)"
    )
```

**说明：**

- 必须继承 `ModelMixin`，该基类自动提供以下字段：
  - `id` (主键, 自增), `uuid` (全局唯一标识), `status` (状态)
  - `description` (备注), `created_time`, `updated_time`
  - `is_deleted` (软删除标志), `deleted_time`
- 如果还需要用户审计字段（创建人/更新人/删除人），可同时继承 `UserMixin`
- `__tablename__` 通常使用单数、小写字母
- `__loader_options__` 用于预加载关联关系（为空列表则表示不需要）

---

### 3. schema.py — Pydantic 模型

```python
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class <ModuleName>CreateSchema(BaseModel):
    """创建请求模型"""
    name: str = Field(..., description="名称", max_length=128)
    phone: str = Field(..., description="联系电话", max_length=20)
    address: Optional[str] = Field(None, description="地址", max_length=500)
    status: int = Field(1, description="状态(0-禁用, 1-启用)")


class <ModuleName>UpdateSchema(BaseModel):
    """更新请求模型 — 所有字段可选"""
    name: Optional[str] = Field(None, description="名称", max_length=128)
    phone: Optional[str] = Field(None, description="联系电话", max_length=20)
    address: Optional[str] = Field(None, description="地址", max_length=500)
    status: Optional[int] = Field(None, description="状态(0-禁用, 1-启用)")


class <ModuleName>OutSchema(BaseModel):
    """响应模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="ID")
    uuid: str = Field(..., description="UUID")
    name: str = Field(..., description="名称")
    phone: str = Field(..., description="联系电话")
    address: Optional[str] = Field(None, description="地址")
    status: int = Field(..., description="状态(0-禁用, 1-启用)")
    created_time: datetime = Field(..., description="创建时间")
    updated_time: datetime = Field(..., description="更新时间")


class <ModuleName>QueryParam(BaseModel):
    """查询参数模型 — 所有字段可选"""
    name: Optional[str] = Field(None, description="名称")
    phone: Optional[str] = Field(None, description="联系电话")
    status: Optional[int] = Field(None, description="状态")
```

**说明：**

- **CreateSchema**: 必填字段用 `Field(...)`，可选字段用 `Field(default, ...)`
- **UpdateSchema**: 所有字段都应为 `Optional`，因为 PATCH/PUT 可能只更新部分字段
- **OutSchema**: 必须有 `model_config = ConfigDict(from_attributes=True)` 以支持从 ORM 模型转换
- **OutSchema**: 必须包含 `id`, `uuid`, `created_time`, `updated_time`（这些由 ModelMixin 提供）
- **QueryParam**: 全部可选，用于过滤查询

---

### 4. crud.py — 数据库操作层

```python
from collections.abc import Sequence

from sqlalchemy import select

from app.core.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import <ModuleName>Model
from .schema import <ModuleName>CreateSchema, <ModuleName>OutSchema, <ModuleName>UpdateSchema


class <ModuleName>CRUD(CRUDBase[<ModuleName>Model, <ModuleName>CreateSchema, <ModuleName>UpdateSchema]):
    """<中文名>数据访问层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=<ModuleName>Model, auth=auth)

    async def get_by_<field>(self, <field>: <type>) -> <ModuleName>Model | None:
        """根据<字段>获取对象"""
        async with self.auth.db as session:
            result = await session.execute(
                select(self.model).filter(self.model.<field> == <field>)
            )
            return result.scalars().first()

    async def get_by_id_crud(self, id: int) -> <ModuleName>Model | None:
        return await self.get(id=id)

    async def create_crud(self, data: <ModuleName>CreateSchema) -> <ModuleName>Model | None:
        return await self.create(data=data)

    async def update_crud(self, id: int, data: <ModuleName>UpdateSchema) -> <ModuleName>Model | None:
        return await self.update(id=id, data=data)

    async def delete_crud(self, ids: list[int]) -> None:
        return await self.delete(ids=ids)

    async def page_crud(
        self,
        offset: int,
        limit: int,
        order_by: list[dict] | None = None,
        search: dict | None = None,
    ) -> dict:
        order_by_list = order_by or [{"id": "asc"}]
        search_dict = search or {}

        return await self.page(
            offset=offset,
            limit=limit,
            order_by=order_by_list,
            search=search_dict,
            out_schema=<ModuleName>OutSchema,
        )
```

**说明：**

- 继承 `CRUDBase[Model, CreateSchema, UpdateSchema]`，泛型三个参数
- `__init__` 传入 `model` 和 `auth`
- `get_by_id_crud`, `create_crud`, `update_crud`, `delete_crud`, `page_crud` 是标准包装方法
- 自定义查询方法（如 `get_by_phone`）需要直接操作 `self.auth.db` 执行 SQLAlchemy select
- `page_crud` 中 `order_by_list` 默认值可以是 `[{"id": "asc"}]` 或 `[{"id": "desc"}]`
- `page_crud` 需要传入 `out_schema` 给 `self.page()` 方法

---

### 5. service.py — 业务逻辑层

```python
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.schema import AuthSchema
from app.core.database import async_db_session as async_session

from .crud import <ModuleName>CRUD
from .schema import <ModuleName>CreateSchema, <ModuleName>OutSchema, <ModuleName>QueryParam, <ModuleName>UpdateSchema


class <ModuleName>Service:
    """<中文名>业务逻辑层"""

    @classmethod
    async def get_info_service(cls, <field>_id: int) -> <ModuleName>OutSchema:
        """获取<中文名>信息"""
        async with async_session() as session:
            auth = AuthSchema(db=session)
            crud = <ModuleName>CRUD(auth)
            obj = await crud.get_by_id_crud(<field>_id)
            if not obj:
                raise ValueError("<中文名>不存在")
            return <ModuleName>OutSchema.model_validate(obj)

    @classmethod
    async def page_service(
        cls,
        page_no: int,
        page_size: int,
        search: <ModuleName>QueryParam | None = None,
        order_by: list[dict] | None = None,
    ) -> dict[str, Any]:
        """分页查询<中文名>列表"""
        async with async_session() as session:
            auth = AuthSchema(db=session)
            crud = <ModuleName>CRUD(auth)
            search_dict = vars(search) if search else None
            return await crud.page_crud(
                offset=(page_no - 1) * page_size,
                limit=page_size,
                order_by=order_by,
                search=search_dict,
            )

    @classmethod
    async def get_by_id_service(cls, <field>_id: int) -> <ModuleName>OutSchema:
        """根据ID获取<中文名>详情"""
        async with async_session() as session:
            auth = AuthSchema(db=session)
            crud = <ModuleName>CRUD(auth)
            obj = await crud.get_by_id_crud(<field>_id)
            if not obj:
                raise ValueError("<中文名>不存在")
            return <ModuleName>OutSchema.model_validate(obj)

    @classmethod
    async def create_service(cls, data: <ModuleName>CreateSchema) -> <ModuleName>OutSchema:
        """创建<中文名>"""
        async with async_session() as session:
            auth = AuthSchema(db=session)
            crud = <ModuleName>CRUD(auth)
            # 可选：唯一性校验
            # existing = await crud.get_by_<unique_field>(data.<unique_field>)
            # if existing:
            #     raise ValueError("该<字段>已存在")
            obj = await crud.create_crud(data)
            if not obj:
                raise ValueError("<中文名>创建失败")
            await session.commit()
            return <ModuleName>OutSchema.model_validate(obj)

    @classmethod
    async def update_service(
        cls, <field>_id: int, data: <ModuleName>UpdateSchema
    ) -> <ModuleName>OutSchema:
        """更新<中文名>信息"""
        async with async_session() as session:
            auth = AuthSchema(db=session)
            crud = <ModuleName>CRUD(auth)
            # 可选：字段唯一性校验（排除自身）
            # if data.<unique_field>:
            #     existing = await crud.get_by_<unique_field>(data.<unique_field>)
            #     if existing and existing.id != <field>_id:
            #         raise ValueError("该<字段>已被占用")
            obj = await crud.update_crud(<field>_id, data)
            if not obj:
                raise ValueError("<中文名>不存在或更新失败")
            await session.commit()
            return <ModuleName>OutSchema.model_validate(obj)

    @classmethod
    async def delete_service(cls, <field>_ids: list[int]) -> None:
        """删除<中文名>"""
        async with async_session() as session:
            auth = AuthSchema(db=session)
            crud = <ModuleName>CRUD(auth)
            await crud.delete_crud(<field>_ids)
            await session.commit()
```

**说明：**

- 所有方法使用 `@classmethod`
- 每个方法内部：`async with async_session() as session:` → `auth = AuthSchema(db=session)` → `crud = XxxCRUD(auth)` → 业务逻辑
- 查不到数据时 `raise ValueError("xxx不存在")`
- ORM 转 Schema 使用 `XxxOutSchema.model_validate(obj)`
- 写操作（create/update/delete）后需要 `await session.commit()`
- 自定义业务校验（如手机号唯一性检查）放在 service 层

---

### 6. controller.py — API 路由

```python
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse

from app.core.auth.schema import AuthSchema
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.auth.permission import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from .schema import (
    <ModuleName>CreateSchema,
    <ModuleName>OutSchema,
    <ModuleName>QueryParam,
    <ModuleName>UpdateSchema,
)
from .service import <ModuleName>Service

<ModuleName>Router = APIRouter(
    route_class=OperationLogRoute,
    prefix="/<module_name>",
    tags=["<中文标签>"],
)


@<ModuleName>Router.get(
    "/info/{<field>_id}",
    summary="获取<中文名>信息",
    description="根据ID获取<中文名>详细信息",
    response_model=ResponseSchema[<ModuleName>OutSchema],
)
async def get_info_controller(
    <field>_id: Annotated[int, Path(description="<中文名>ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["plugin:<module_name>:query"]))],
) -> JSONResponse:
    result = await <ModuleName>Service.get_info_service(<field>_id=<field>_id)
    log.info(f"获取<中文名>信息成功 {<field>_id}")
    return SuccessResponse(data=result, msg="获取<中文名>信息成功")


@<ModuleName>Router.get(
    "/list",
    summary="查询<中文名>列表",
    description="分页查询<中文名>列表",
    response_model=ResponseSchema[dict],
)
async def get_<module_name>_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[<ModuleName>QueryParam, Depends()],
) -> JSONResponse:
    result_dict = await <ModuleName>Service.page_service(
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("查询<中文名>列表成功")
    return SuccessResponse(data=result_dict, msg="查询<中文名>列表成功")


@<ModuleName>Router.get(
    "/detail/{<field>_id}",
    summary="获取<中文名>详情",
    description="根据ID获取<中文名>详情",
    response_model=ResponseSchema[<ModuleName>OutSchema],
)
async def get_<module_name>_detail_controller(
    <field>_id: Annotated[int, Path(description="<中文名>ID")],
) -> JSONResponse:
    result = await <ModuleName>Service.get_by_id_service(<field>_id=<field>_id)
    log.info(f"获取<中文名>详情成功 {<field>_id}")
    return SuccessResponse(data=result, msg="获取<中文名>详情成功")


@<ModuleName>Router.post(
    "/create",
    summary="创建<中文名>",
    description="创建新<中文名>",
    response_model=ResponseSchema[<ModuleName>OutSchema],
)
async def create_<module_name>_controller(
    data: <ModuleName>CreateSchema,
) -> JSONResponse:
    result = await <ModuleName>Service.create_service(data=data)
    log.info(f"创建<中文名>成功 {result.id}")
    return SuccessResponse(data=result, msg="创建<中文名>成功")


@<ModuleName>Router.put(
    "/update/{<field>_id}",
    summary="更新<中文名>",
    description="更新<中文名>信息",
    response_model=ResponseSchema[<ModuleName>OutSchema],
)
async def update_<module_name>_controller(
    <field>_id: Annotated[int, Path(description="<中文名>ID")],
    data: <ModuleName>UpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["plugin:<module_name>:update"]))],
) -> JSONResponse:
    result = await <ModuleName>Service.update_service(<field>_id=<field>_id, data=data)
    log.info(f"更新<中文名>成功 {<field>_id}")
    return SuccessResponse(data=result, msg="更新<中文名>成功")


@<ModuleName>Router.delete(
    "/delete",
    summary="删除<中文名>",
    description="批量删除<中文名>",
    response_model=ResponseSchema[None],
)
async def delete_<module_name>_controller(
    ids: Annotated[list[int], Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["plugin:<module_name>:delete"]))],
) -> JSONResponse:
    await <ModuleName>Service.delete_service(<field>_ids=ids)
    log.info(f"删除<中文名>成功 {ids}")
    return SuccessResponse(data=None, msg="删除<中文名>成功")
```

**说明：**

- `Router` 变量名格式：`XxxRouter = APIRouter(...)` — 这会被 discover.py 自动发现并注册
- `route_class=OperationLogRoute` — 自动记录操作日志
- `prefix="/<module_name>"` — 路由前缀（容器前缀 `/<module_name>` 由 discover.py 自动添加，此处是子前缀）
- `tags=["中文标签"]` — 用于 Swagger 文档分组
- 完整路由：`/api/v1/<module_name>/<module_name>/info/{id}`
- 权限格式：`AuthPermission(["plugin:<module_name>:<action>"])`
  - action 取值: `query`, `create`, `update`, `delete`
  - 可选：某些公开接口可以不加权限（但 get/list 通常建议至少加 query 权限）
- `ids: Annotated[list[int], Depends()]` — 批量删除通过 query params 传入

---

## 完整新建模块步骤

1. 在 `backend/app/plugin/` 下创建 `module_<name>/` 和 `module_<name>/<name>/` 目录
2. 在每层目录添加空的 `__init__.py`
3. 创建 `plugin.toml`
4. 创建 `model.py`（继承 `ModelMixin`，定义字段）
5. 创建 `schema.py`（CreateSchema / UpdateSchema / OutSchema / QueryParam）
6. 创建 `crud.py`（继承 `CRUDBase[Model, CreateSchema, UpdateSchema]`）
7. 创建 `service.py`（`@classmethod` + `async_session() + XxxCRUD` 模式）
8. 创建 `controller.py`（定义 `XxxRouter = APIRouter(...)` + 6 个标准端点）
9. 重启后端服务，discover.py 会自动发现并注册所有路由

## 命名约定对照表

| 元素             | merchant 模块示例                | order 模块示例             | 占位符                                     |
| ---------------- | -------------------------------- | -------------------------- | ------------------------------------------ |
| 顶级目录         | `module_merchant`                | `module_order`             | `module_<module_name>`                     |
| 子模块目录       | `merchant`                       | `order`                    | `<module_name>`                            |
| 表名             | `merchant`                       | `order`                    | `<table_name>`                             |
| Model 类         | `MerchantModel`                  | `OrderModel`               | `<ModuleName>Model`                        |
| Router 变量      | `MerchantRouter`                 | `OrderRouter`              | `<ModuleName>Router`                       |
| Service 类       | `MerchantService`                | `OrderService`             | `<ModuleName>Service`                      |
| CRUD 类          | `MerchantCRUD`                   | `OrderCRUD`                | `<ModuleName>CRUD`                         |
| CreateSchema     | `MerchantCreateSchema`           | `OrderCreateSchema`        | `<ModuleName>CreateSchema`                 |
| UpdateSchema     | `MerchantUpdateSchema`           | `OrderUpdateSchema`        | `<ModuleName>UpdateSchema`                 |
| OutSchema        | `MerchantOutSchema`              | `OrderOutSchema`           | `<ModuleName>OutSchema`                    |
| QueryParam       | `MerchantQueryParam`             | `OrderQueryParam`          | `<ModuleName>QueryParam`                   |
| 路由前缀         | `/merchant`                      | `/order`                   | `/<module_name>`                           |
| 完整路径         | `/api/v1/merchant/merchant/list` | `/api/v1/order/order/list` | `/api/v1/<module_name>/<module_name>/list` |
| 权限标识         | `plugin:merchant:query`          | (无权限)                   | `plugin:<module_name>:<action>`            |
|  |
| 管理后台组件路径 | `module_merchant/merchant/index` | —                          | `module_<module_name>/<module_name>/index` |

---

## 管理后台菜单添加流程

创建完后端模块后，需在 `sys_menu.json` 中添加菜单配置，使管理后台能访问到页面。

### 文件位置

- 菜单配置文件：`backend/app/scripts/data/sys_menu.json`
- 数据初始化脚本：`backend/app/scripts/initialize.py`（后端启动时自动运行）

### 菜单 JSON 结构

```json
{
  "name": "菜单名称",
  "type": 1,              // 1=目录(一级), 2=菜单(二级), 3=按钮/权限
  "icon": "ri:store-line", // RemixIcon 图标
  "order": 3,             // 排序
  "permission": null,     // 权限标识（type=1 时为 null）
  "route_name": "Shop",   // 路由名称
  "route_path": "/shop",  // 路由路径
  "component_path": null, // Vue 组件路径（type=1 时为 null）
  "status": "0",          // 状态(0=启用)
  "keep_alive": true,
  "hidden": false,
  "always_show": true,    // 目录有子菜单时建议 true
  "title": "菜单标题",
  "affix": false,
  "redirect": "/shop/product",  // 一级目录重定向到首个子菜单
  "description": "描述",
  "children": [ ... ],    // 子菜单和按钮权限
  "client": "pc"          // pc=管理端, app=移动端
}
```

### 完整添加步骤

1. **确认后端模块已创建**（按上方"完整新建模块步骤"完成）
2. **确认管理后台 Vue 页面已创建**，路径为 `frontend/web/src/views/module_<name>/<name>/index.vue`
3. **在 `sys_menu.json` 中添加菜单配置**：
   - 顶部目录（type=1）：
     - 查看当前最后一个 PC 菜单的 `order` 值（如 `订单管理 order=10`）
     - 新目录的 `order` 设为 `当前最大 order + 1`（如 `11`），**不要插入到中间**
     - ⚠️ 约束：所有新菜单必须追加在末尾（order 递增），不得插入到已有菜单之间
     - 移动端菜单（client="app"）的 order 使用 90 以上范围，与 PC 菜单隔离
   - 页面菜单（type=2）：`component_path` 指向 `module_<name>/<name>/index`
   - 按钮权限（type=3）：create / update / delete / detail / patch / query，`permission` 格式为 `module_<name>:<name>:<action>`
   - Vue 页面中使用的权限字符串格式：`module_<plugin>:<submodule>:<action>`（如 `module_product:product:create`）
4. **重启后端**：停止后重新执行 `python main.py run --env=dev`（本仓库已无 Docker）
   - 后端启动时 `initialize.py` 会自动读取 `sys_menu.json` 写入数据库
   - 如果表已有数据会跳过，如需强制重新导入需先清空 `sys_menu` 表
5. **重新关联管理员角色**（如果清空过菜单表）：
   ```sql
   INSERT IGNORE INTO sys_role_menus (role_id, menu_id) SELECT 1, id FROM sys_menu;
   ```

### 权限标识命名约定

| 元素         | 示例                            | 格式                                 |
| ------------ | ------------------------------- | ------------------------------------ |
| 查询权限     | `module_product:product:query`  | `module_<plugin>:<submodule>:query`  |
| 创建权限     | `module_product:product:create` | `module_<plugin>:<submodule>:create` |
| 修改权限     | `module_product:product:update` | `module_<plugin>:<submodule>:update` |
| 删除权限     | `module_product:product:delete` | `module_<plugin>:<submodule>:delete` |
| 详情权限     | `module_product:product:detail` | `module_<plugin>:<submodule>:detail` |
| 批量修改状态 | `module_product:product:patch`  | `module_<plugin>:<submodule>:patch`  |

---

## 验证测试

创建模块并添加菜单后，运行以下测试验证功能正常。

### 1. 后端 API 自动化测试

```bash
# 确保后端运行
curl http://127.0.0.1:8001/api/v1/common/health/

# 登录获取 Token
curl -s -X POST http://127.0.0.1:8001/api/v1/system/auth/login \
  -d "username=admin&password=123456&login_type=PC端" \
  | python3 -c "import json,sys; open('/tmp/token.txt','w').write(json.load(sys.stdin)['data']['access_token'])"

# 运行 e2e 测试脚本
cd /path/to/project/backend
TOKEN=$(cat /tmp/token.txt) .venv/bin/python app/scripts/e2e_test.py
```

### 2. 手动验证清单

| 验证项          | 方法                                                          |
| --------------- | ------------------------------------------------------------- |
| 菜单树可见      | 刷新管理后台（http://127.0.0.1:5174），确认新菜单出现在侧边栏 |
| 新模块 API 可用 | 使用 Swagger 文档 `http://127.0.0.1:8001/api/v1/docs`         |
| 路由注册        | 检查后端进程日志中是否出现「注册容器」相关输出                |

### 3. 常用调试命令

```bash
# 查看菜单数据（本机 / RDS MySQL，按 env 填写账号库名）
mysql -h <host> -u root -p mystabx_vnpy \
  -e "SELECT id, name, route_path, type FROM sys_menu WHERE type=1 ORDER BY \`order\`;"

# 重新关联角色权限（清空菜单后需执行）
mysql -h <host> -u root -p mystabx_vnpy \
  -e "INSERT IGNORE INTO sys_role_menus (role_id, menu_id) SELECT 1, id FROM sys_menu;"
```
