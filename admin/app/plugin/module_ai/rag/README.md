# module_ai/rag — 知识库 / 向量库能力库

## 模块定位

检索增强生成（RAG）的能力库：Agno `Knowledge` 封装、向量数据库（PgVector）连接、
Embedding 模型工厂、系统知识文档加载与系统查询工具。
边界：没有 `controller.py`（无 HTTP 入口）、没有 `model.py`（无 ORM 表）；由
`chat/service.py` 在聊天链路中注入（非 PostgreSQL 后端由 `rag_supported()` 降级为不注入）。

## 入口

| 入口类型        | 路径                     | 说明                                                   |
| --------------- | ------------------------ | ------------------------------------------------------ |
| HTTP 路由       | 无                       | 无 `controller.py`，目录扫描不会挂载任何路由           |
| WebSocket       | 无                       | —                                                      |
| ORM 模型        | 无                       | 无 `model.py`                                          |
| 公开模块        | `knowledge_base.py`      | Agno `Knowledge` 封装                                  |
| 公开模块        | `vector_db.py`           | 向量库（PgVector）连接                                  |
| 公开模块        | `embedder_factory.py`    | Embedding 模型工厂                                      |
| 公开模块        | `knowledge_content.py`   | 系统知识文档加载（`ensure_knowledge_loaded`）与降级判定（`rag_supported`） |
| 公开模块        | `system_tools.py`        | 系统实时数据查询工具（Agno `@tool`，底层为原生 SQL；不依赖任何插件） |
| 知识文档        | `../knowledge/*.md`      | 随插件存放，由 `knowledge_content.py` 幂等写入向量库     |
| 种子数据        | 无                       | —                                                      |

## 依赖

- 内核槽位：无。
- 其它插件：无直接依赖（`system_tools.py` 用原生 SQL 读取表，不 import 任何插件模块）。
- 第三方：`agno`（含向量库集成）、`fastembed`（默认 Embedding）。
- 调用方：`chat/service.py`（`chat_query` 与 `chat_non_stream` 两处注入）。

## 删除影响

删除本子模块后：

- `chat/service.py` 导入失败——聊天链路（含 WebSocket）整体不可用；删除需同步改该文件。
- 无路由、无表、无种子受影响。
- 知识库与系统查询工具能力消失，AI 对话回到普通问答。
