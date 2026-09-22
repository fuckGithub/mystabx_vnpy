# GitHub Copilot 项目指令

所有代码生成必须严格遵守项目根目录 [AGENTS.md](../AGENTS.md) 中定义的统一规范指南。

## 核心提醒

- Python 代码强制开启类型提示，禁止隐式类型转换
- TypeScript 代码严格开启 strict 模式，禁止无意义的 `any` 类型
- Dart 代码遵循 Flutter 标准 lint 规则
- 生成的接口代码必须符合 FastAPI 异步开发标准，兼容现有项目鉴权体系
- 后端 API 路径以 `/api/v1` 起始，遵循统一响应格式
- 提交信息使用 Conventional Commits 格式：`type(scope): subject`

## 后端插件架构（强制）

后端已 **全面插件化**，全部业务模块位于 `backend/app/plugin/module_*/`，`app/api/` 已删除。

- 新增/修改业务代码一律落在 `app/plugin/module_*/` 下，**禁止新建 `app/api/v1/` 路径**
- 每个插件必须自带 `plugin.toml` + `plugin.py`（模块级 `PLUGIN = Plugin()`）+ `README.md`
- `app/core/**` 不得导入任何具体插件（通过 `app/core/plugin/slots.py` 槽位与 `events.py` 事件总线反向解耦）
- 四条静默失败红线见根目录 `AGENTS.md`「后端插件架构」章节
- 客户端路由前缀 `/api/v1` 由 `settings.ROOT_PATH` 提供（FastAPI `root_path`），业务路由本身不带该前缀，**无需改动前端/nginx**

## 入口文件优先级

1. `AGENTS.md`（根目录）— 项目统一规范入口
2. `backend/AGENTS.md` / `web/AGENTS.md` / `uniapp/AGENTS.md` / `flutter/AGENTS.md` — 子项目详细指令
3. `.agents/skills/*.md` — 按需加载的完整 skill 文档
