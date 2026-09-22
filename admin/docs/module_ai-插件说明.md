# module_ai 插件说明（AI 能力集成）

> 版本：1.1.0 · 目录：`admin/app/plugin/module_ai/` · 技术栈：Agno + OpenAI/Anthropic/Gemini/Ollama 多协议

---

## 一、插件定位

`module_ai` 是 FastAPIAdmin 的 **AI 能力插件**，提供：

1. **模型供应商管理**（一级：`ai_provider`）
2. **模型管理**（二级：`ai_model`，归属供应商，支持同名模型跨供应商并存）
3. **聊天会话**（`ai/chat`：流式 WebSocket + 非流式 JSON 接口，会话持久化到 Agno）

核心设计参照 `ProviderConfig(供应商) + ModelSpec(模型)` 两级结构，
**协议由 `api_type`（apiType）决定，而非 vendor 厂商名**——这正是"不同供应商存在相同模型"的
解耦关键。

---

## 二、目录结构

```
admin/app/plugin/module_ai/
├── plugin.toml          # 插件元数据（本文件描述）
├── __init__.py
├── chat/                # 聊天会话子模块
│   ├── controller.py    # ChatRouter（/ai/chat/*）
│   ├── crud.py          # ChatSessionCRUD（Agno 会话持久化）
│   ├── schema.py        # 聊天请求/响应模型
│   ├── service.py       # ChatService（流式/非流式，按 model_id 选模型）
│   ├── utils.py         # AgnoFactory（Team + Agent 组装，model 实例注入）
│   └── ws.py            # WS_AI WebSocket 路由
└── model/               # 供应商 + 模型 两级管理子模块
    ├── controller.py    # AiProviderRouter（/ai/provider/*）+ AiModelRouter（/ai/model/*）
    ├── crud.py          # AiProviderCRUD + AiModelCRUD
    ├── model.py         # AiProviderModel（ai_provider）+ AiModelModel（ai_model）
    ├── schema.py        # 供应商/模型嵌套 Schema
    ├── service.py       # AiProviderService + AiModelService（build_model_by_id）
    └── utils.py         # AgnoModelFactory（按 api_type 协议构建模型实例）
```

路由由 `module_ai/**/controller.py` 顶层 `APIRouter` 变量动态发现并挂载到 `/ai/` 容器。

---

## 三、数据模型（两级表）

### 3.1 供应商表 `ai_provider`

| 字段                                     | 类型            | 说明                                                               |
| ---------------------------------------- | --------------- | ------------------------------------------------------------------ |
| `id` / `uuid` / `status` / `description` | ModelMixin 继承 | 公共字段                                                           |
| `name`                                   | String(64)      | 供应商名称（如 `mimo-tp` / `DeepSeek`）                            |
| `vendor`                                 | String(32)      | 厂商类型（openai/anthropic/google/ollama/deepseek/customendpoint） |
| **`api_type`**                           | String(32)      | **API 协议类型**（chat-completions/messages/gemini/ollama/azure）  |
| `api_key`                                | String(255)     | 供应商 API 密钥（可空，模型级可覆盖）                              |
| `base_url`                               | String(255)     | 供应商默认 API 地址（模型可覆盖）                                  |
| `is_default`                             | Boolean         | 是否为默认供应商                                                   |
| `sort_order`                             | Integer         | 排序号（越大越靠前）                                               |

### 3.2 模型表 `ai_model`

| 字段                                     | 类型            | 说明                                                    |
| ---------------------------------------- | --------------- | ------------------------------------------------------- |
| `id` / `uuid` / `status` / `description` | ModelMixin 继承 | 公共字段                                                |
| **`provider_id`**                        | Integer(FK)     | 归属供应商（`ai_provider.id`，级联删除）                |
| `model_key`                              | String(128)     | 模型 id（如 `mimo-v2.5`，同供应商内可重名跨供应商区分） |
| `name`                                   | String(128)     | 模型显示名（如 `mimo-v2.5-tp`）                         |
| `url`                                    | String(255)     | 模型端点（覆盖供应商 `base_url`，可空）                 |
| `tool_calling` / `vision` / `thinking`   | Boolean         | 能力元数据（toolCalling/vision/thinking）               |
| `max_input_tokens` / `max_output_tokens` | Integer         | 输入/输出 token 上限                                    |
| `temperature`                            | Float           | 温度（默认 0.7）                                        |
| `is_default`                             | Boolean         | 是否为默认模型                                          |
| `sort_order`                             | Integer         | 排序号                                                  |

> 不同供应商可以有**相同** `model_key`（如多个厂商都有 `claude-3-5-sonnet`），
> 通过 `provider_id` 归属区分——这是两级表相对扁平单表的本质优势。

---

## 四、协议构建（`AgnoModelFactory`）

`model/utils.py` 的 `AgnoModelFactory.build_model(config)` 根据**合并后的供应商+模型配置**
构建 Agno 原生模型实例。

### 关键：协议由 `api_type` 决定，vendor 仅兜底

| `api_type`                    | 构建的 Agno 模型类 | 典型场景                                                                         |
| ----------------------------- | ------------------ | -------------------------------------------------------------------------------- |
| `chat-completions` / `openai` | `OpenAILike`       | DeepSeek、OpenAI、Moonshot、SiliconFlow 等 OpenAI 兼容                           |
| `messages` / `anthropic`      | `Claude`           | Anthropic 官方、以及 **mimo 等 vendor=customendpoint 但走 anthropic 协议的服务** |
| `gemini` / `google`           | `Gemini`           | Google Gemini                                                                    |
| `ollama`                      | `Ollama`           | 本地 Ollama                                                                      |
| `azure`                       | `AzureOpenAI`      | Azure OpenAI                                                                     |

参数注入规则：

- **模型端点优先**：`model.url` > `provider.base_url`
- `temperature` / `max_tokens`（来自 `max_output_tokens`）/ `api_key`（供应商级）自动注入
- Claude 协议：`thinking=true` → `{"type": "enabled"}`
- Ollama：`api_key` 移除，`host` 取自端点
- Azure：使用 `azure_deployment`（模型 key）+ `azure_endpoint`
- 对应 SDK 未安装时抛出**友好 ImportError**（提示 `pip install anthropic` 等），不导致崩溃

### 与参考配置的对应关系

```json
{
  "name": "mimo-tp",
  "vendor": "customendpoint",
  "apiKey": "${input:chat.lm.secret.-452cc05c}",
  "apiType": "messages",
  "models": [
    {
      "id": "mimo-v2.5",
      "name": "mimo-v2.5-tp",
      "url": "https://token-plan-cn.xiaomimimo.com/anthropic",
      "toolCalling": true,
      "vision": true,
      "maxInputTokens": 1024000,
      "maxOutputTokens": 128000,
      "thinking": true
    }
  ]
}
```

数据库两级表映射：

| 参考字段                                   | 落库                                          |
| ------------------------------------------ | --------------------------------------------- |
| Provider 顶层 `name/vendor/apiKey/apiType` | `ai_provider.name/vendor/api_key/api_type`    |
| Provider 顶层 `models[]`                   | `ai_model` 行（`provider_id` 关联）           |
| Model `id` / `name` / `url`                | `ai_model.model_key/name/url`                 |
| `toolCalling` / `vision`                   | `ai_model.tool_calling/vision`                |
| `maxInputTokens` / `maxOutputTokens`       | `ai_model.max_input_tokens/max_output_tokens` |
| `thinking`                                 | `ai_model.thinking`                           |

> `vendor=customendpoint + apiType=messages` → 走 **Claude 协议**（`agno.models.anthropic.claude:Claude`），
> 这正是 reference 配置 mimo 场景的正确解析。

---

## 五、API 路由清单

容器前缀 `/ai`，全部路由由 discover 自动发现（`module_ai/**/controller` 顶层 router 变量）。

### 5.1 供应商管理 `AiProviderRouter`（prefix `/provider`）

| 方法   | 路径                            | 权限                     | 说明                        |
| ------ | ------------------------------- | ------------------------ | --------------------------- |
| GET    | `/ai/provider/detail/{id}`      | `module_ai:model:detail` | 供应商详情（含嵌套 models） |
| GET    | `/ai/provider/list`             | `module_ai:model:query`  | 供应商列表                  |
| GET    | `/ai/provider/page`             | `module_ai:model:query`  | 供应商分页                  |
| POST   | `/ai/provider/create`           | `module_ai:model:create` | 新建供应商                  |
| PUT    | `/ai/provider/update/{id}`      | `module_ai:model:update` | 更新供应商                  |
| DELETE | `/ai/provider/delete`           | `module_ai:model:delete` | 删除供应商（级联删模型）    |
| PUT    | `/ai/provider/set-default/{id}` | `module_ai:model:update` | 设置默认供应商              |

### 5.2 模型管理 `AiModelRouter`（prefix `/model`）

| 方法    | 路径                                      | 权限                     | 说明                                   |
| ------- | ----------------------------------------- | ------------------------ | -------------------------------------- |
| GET     | `/ai/model/detail/{id}`                   | `module_ai:model:detail` | 模型详情（含供应商信息）               |
| GET     | `/ai/model/list`                          | `module_ai:model:query`  | 模型列表                               |
| GET     | `/ai/model/page`                          | `module_ai:model:query`  | 模型分页                               |
| **GET** | **`/ai/model/by-provider/{provider_id}`** | `module_ai:model:query`  | **按供应商查启用模型（前端分类下拉）** |
| POST    | `/ai/model/create`                        | `module_ai:model:create` | 新建模型（需指定 provider_id）         |
| PUT     | `/ai/model/update/{id}`                   | `module_ai:model:update` | 更新模型                               |
| DELETE  | `/ai/model/delete`                        | `module_ai:model:delete` | 删除模型（批量）                       |
| PUT     | `/ai/model/set-default/{id}`              | `module_ai:model:update` | 设置默认模型                           |

### 5.3 聊天会话 `ChatRouter` + `WS_AI`

| 方法   | 路径                           | 说明                                                  |
| ------ | ------------------------------ | ----------------------------------------------------- |
| GET    | `/ai/chat/detail/{session_id}` | 会话详情                                              |
| GET    | `/ai/chat/list`                | 会话列表（分页）                                      |
| POST   | `/ai/chat/create`              | 创建会话                                              |
| PUT    | `/ai/chat/update/{session_id}` | 重命名会话                                            |
| DELETE | `/ai/chat/delete`              | 删除会话（批量）                                      |
| POST   | `/ai/chat/ai-chat`             | 非流式对话（`AiChatRequestSchema` 带 `model_id`）     |
| WS     | `/ai/chat/ws`                  | WebSocket 流式对话（`ChatQuerySchema` 带 `model_id`） |

请求体示例（选择模型）：

```json
{ "message": "你好", "model_id": 3 }
```

`model_id` 为空时使用默认模型（`is_default=true`）；chat 侧通过
`AiModelService.build_model_by_id(model_id)` 构建模型实例并按 `api_type` 协议注入 Team。

---

## 六、种子数据（Alembic 迁移 `9a1b2c3d4e5f`）

建表 + 预置 6 个供应商、8 个模型（仅供参考修改，key 需自行填入）：

| 供应商           | vendor         | api_type         | 模型                                                    |
| ---------------- | -------------- | ---------------- | ------------------------------------------------------- |
| mimo-tp          | customendpoint | messages         | mimo-v2.5（思考+视觉+工具）、mimo-v2.5-pro（思考+工具） |
| DeepSeek（默认） | deepseek       | chat-completions | deepseek-chat（默认模型）、deepseek-reasoner            |
| OpenAI           | openai         | chat-completions | gpt-4o                                                  |
| Anthropic        | anthropic      | messages         | claude-3-5-sonnet                                       |
| Google           | google         | gemini           | gemini-1.5-pro                                          |
| Ollama           | ollama         | ollama           | llama3                                                  |

---

## 七、验证

```bash
cd admin
# 迁移链
.venv/bin/python -m alembic heads        # → 9a1b2c3d4e5f (head)
# 协议构建冒烟（mimo→Claude 协议；deepseek→OpenAILike）
.venv/bin/python -c "
from app.plugin.module_ai.model.utils import AgnoModelFactory as F
m = F.build_model({'api_type':'messages','vendor':'customendpoint','model_key':'mimo-v2.5'})
print(type(m).__name__)   # → Claude（SDK 未装时提示 pip install anthropic）
"
# 路由发现
.venv/bin/python -c "from app.core.discover import get_dynamic_router as g; print(len([r for r in g().routes]))"
```

---

## 八、扩展指引

- **新增厂商**：只需在 DB 添加供应商（`api_type` 选已知协议）；若为全新协议，在
  `AgnoModelFactory.API_TYPE_MODEL_MAP` 增加映射 + `SDK_REQUIREMENT` 提示。
- **同供应商多模型**：在 `ai_model` 添加多行（相同 `provider_id`）。
- **前端分类下拉**：先调 `/ai/provider/list`，再调 `/ai/model/by-provider/{provider_id}` 取该供应商模型。
