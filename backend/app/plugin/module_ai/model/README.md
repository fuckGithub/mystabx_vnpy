# module_ai/model — AI 供应商与模型

## 模块定位

AI 供应商（`ai_provider`）与模型（`ai_model`）两级配置管理：CRUD、设默认、连通性测试、
按供应商查模型。
边界：只维护配置数据与模型实例构建；实际对话在 `module_ai/chat`。

## 入口

| 入口类型  | 路径                                         | 说明                                        |
| --------- | -------------------------------------------- | ------------------------------------------- |
| HTTP 路由 | `controller.py` → `AiProviderRouter`         | 容器前缀 `/ai/provider`，共 8 条             |
| HTTP 路由 | `controller.py` → `AiModelRouter`            | 容器前缀 `/ai/model`，共 8 条                |
| ORM 模型  | `model.py`                                   | 表 `ai_provider`、`ai_model`                 |
| 业务实现  | `service.py`、`crud.py`、`utils.py`、`schema.py` | `utils.py` 按 `api_type` 协议映射构建模型实例 |

路由（16 条）：
`/ai/provider/{list,create,update/{id},delete,detail/{id},set-default/{id},test-connectivity}`、
`/ai/model/{list,page,create,update/{id},delete,detail/{id},set-default/{id},by-provider/{provider_id}}`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（鉴权基元）。
- 第三方：`agno`。

## 删除影响

删除本子模块后：

- `/ai/provider/*` 与 `/ai/model/*` 共 16 条接口消失。
- 表 `ai_provider`、`ai_model` 不再自动创建（已有配置数据保留）。
- `module_ai/chat` 取不到模型配置，聊天链路失效（供应商/模型选择无法进行）。
