# AI 工具统一规范配置指南

采用 **「核心规范单一入口 + 工具专属轻量引用」** 架构：`AGENTS.md` 作为全项目唯一的规则事实来源，各 AI 工具在其原生配置文件中通过简短引用关联到 `AGENTS.md`。既保证全项目规则完全统一，又完全适配各 AI 工具的原生生态。

---

## 文件结构

```
fastapiadmin/
├── AGENTS.md                          ← 全局唯一核心规范
├── CLAUDE.md                          ← Claude Code / Cline / Windsurf 入口
├── .github/
│   └── copilot-instructions.md        ← GitHub Copilot 入口
├── .cursor/
│   └── rules/
│       └── general.mdc                ← Cursor 入口
├── .windsurfrules                     ← Windsurf 入口（或复用 CLAUDE.md）
├── .traerc                            ← Trae-CN 入口
└── docs/
    └── ai-tool-config-guide.md        ← 本文件
```

**设计原则**：`AGENTS.md` 写入所有通用开发规范（代码风格、命名规范、技术栈约束、安全要求等），各工具入口文件只写几行引用和专属补充规则。后续所有规则更新仅需修改 `AGENTS.md` 一个文件。

---

## 各工具配置对照

| 工具                 | 读取文件                              | 配置方式                                                         |
| -------------------- | ------------------------------------- | ---------------------------------------------------------------- |
| **Claude Code**      | 根目录 `CLAUDE.md`                    | 原生支持，文件头部引用 `AGENTS.md`，补充 Claude 专属工具调用规则 |
| **Codex / OpenCode** | 根目录 `AGENTS.md`                    | 原生支持，无需额外配置                                           |
| **Cline**            | 根目录 `CLAUDE.md`                    | 与 Claude Code 共用，无需额外操作                                |
| **Windsurf**         | `.windsurfrules` 或根目录 `CLAUDE.md` | 可直接复用 `CLAUDE.md` 内容                                      |
| **GitHub Copilot**   | `.github/copilot-instructions.md`     | 官方标准路径，写入引用语句指向根目录 `AGENTS.md`                 |
| **Cursor**           | `.cursor/rules/*.mdc`                 | 模块化规则，支持按文件后缀匹配，引用 `AGENTS.md`                 |
| **Trae-CN**          | 根目录 `.traerc` 或 `.trae/rules.md`  | 写入引用语句指向 `AGENTS.md`，或在设置面板手动指定路径           |

---

## 落地操作

### 1. 确认核心规范文件

`AGENTS.md` 已有（项目概述/技术栈/快速开始/开发约定），可根据需要补充详细编码规范章节。

### 2. 创建各工具入口文件

#### Claude Code（`CLAUDE.md`）

```markdown
# Claude Code 项目规则

本项目所有开发规范完全遵循 [AGENTS.md](./AGENTS.md) 中定义的标准，请严格执行。

## Claude 专属补充规则

- 优先使用内置文件操作工具完成代码修改，不生成冗余的独立脚本
- 涉及多文件修改时，自动生成变更清单，标注每个文件的修改目的
- 调用终端命令前，自动校验命令是否符合项目安全规范，禁止执行高危系统操作
```

#### GitHub Copilot（`.github/copilot-instructions.md`）

```markdown
# GitHub Copilot 项目指令

所有代码生成必须严格遵守项目根目录 [AGENTS.md](../AGENTS.md) 中定义的开发规范。

## 核心提醒

- Python 代码强制开启类型提示，禁止隐式类型转换
- TypeScript 代码严格开启 strict 模式，禁止无意义的 `any` 类型
- 生成的接口代码必须符合 FastAPI 异步开发标准，兼容现有项目鉴权体系
```

#### Cursor（`.cursor/rules/general.mdc`）

```markdown
---
description: FastapiAdmin 全局通用开发规则
globs: ["**/*.py", "**/*.vue", "**/*.ts", "**/*.dart"]
---

所有代码生成完全遵循 @AGENTS.md 中定义的全栈开发标准，不同端代码禁止混用其他技术栈语法。
```

#### Windsurf（`.windsurfrules`）

可直接复用根目录 `CLAUDE.md` 内容（内容同上），无需额外配置。

#### Trae-CN（`.traerc`）

```ini
[general]
rules = ./AGENTS.md
```

或在编辑器设置面板中手动指定 `AGENTS.md` 路径。

### 3. 执行命令

```bash
cd /Users/jerome/Developer/AI/fastapiadmin

# Claude Code（如果使用软链接简化，不单独维护 CLAUDE.md）
ln -sf AGENTS.md CLAUDE.md

# GitHub Copilot
mkdir -p .github
ln -sf ../AGENTS.md .github/copilot-instructions.md

# Cursor
mkdir -p .cursor/rules
# 手动创建 .cursor/rules/general.mdc（内容见上）
```

> **Windows 注意**：软链接需要管理员权限或开发者模式。Windows 开发者请直接复制入口文件内容而非使用 `ln -sf`。

---

## 配置校验

完成配置后，在项目中用任意 AI 工具测试以下验证点：

- [ ] 提问"本项目后端使用的 ORM 框架是什么"→ 应回答 **SQLAlchemy 2.0**
- [ ] 生成 Flutter 代码 → 应遵循 Material 3 设计规范
- [ ] 生成 unibest 小程序代码 → 应适配微信端跨条件编译语法
- [ ] Windows 环境无路径不存在或软链接报错

### 常见问题

**Q：修改规范后需要做什么？**

A：只需修改 `AGENTS.md` 这一个文件，各工具入口文件通过引用自动获取最新内容。

**Q：工具不支持引用外部文件怎么办？**

A：直接将 `AGENTS.md` 完整内容复制到工具要求的配置文件中。
