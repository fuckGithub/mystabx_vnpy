# Web Admin AGENTS.md

> 📖 **入口规范**：[AGENTS.md](../../AGENTS.md)

## Overview

管理后台（PC 端），Vue3 + Element Plus + Vite + pnpm。面向 B 端商户管理员。所有开发须遵守根目录 AGENTS.md 中的通用约定。

## Project Structure

```
frontend/web/
├── src/
│   ├── views/            # 页面
│   ├── components/       # 公共组件
│   ├── api/              # API 封装
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia 状态管理
│   ├── layouts/          # 布局组件
│   └── styles/           # 全局样式（Element Plus 变量覆盖）
├── public/               # 静态资源
├── index.html
├── vite.config.ts
├── package.json
└── pnpm-lock.yaml
```

## Design System

- **组件库**：Element Plus（https://element-plus.cn/en-US/guide/design）
- **布局**：深色侧栏 + 内容区，面包屑导航
- **品牌色**：`#FF6B35` 活力橙（覆盖 Element Plus 默认蓝色）
- **原型标准**：高保真可交互 HTML，Element Plus 风格

## Key Commands

```bash
# 安装依赖
pnpm install

# 开发
pnpm dev

# 构建
pnpm build

# 代码检查
pnpm lint

# 单元测试（vitest）
pnpm test        # 单次运行
pnpm test:watch  # 监听模式
```

## 单元测试约定（vitest）

- 配置：根目录 `vitest.config.ts`（独立于 `vite.config.ts`，不加载 Element Plus / UnoCSS 等重型插件）
- 用例位置：`src/**/__tests__/*.spec.ts` —— 放在 `src/` 下才能被 `tsconfig.json` 与 `pnpm lint` 覆盖
- 环境为 `node`，**不挂载 .vue 组件**；需要交互时把依赖模块用 `vi.mock` 换成「有状态的假实现」
- 覆盖重点：登录跳转链路（`resolveRedirectTarget` 嵌套剥离、`redirectToLogin` 防自嵌套、路由守卫的初始化/熔断/降级决策）
- ⚠️ 写守卫用例时注意：vue-router 对「推到当前路径」直接返回冗余导航失败且**不执行守卫**，用例开头需先把位置挪到与目标不同的路径（`beforeEach` 里的 `/blank` 停车位）

## Default Port

管理后台: `http://127.0.0.1:6110`

## Code Style（Prettier + ESLint + Stylelint 约束）

- **Prettier**：`frontend/web/.prettierrc.yaml`
  - `printWidth: 120`，`singleQuote: true`，`tabWidth: 2`
  - `semi: false`（无分号），`trailingComma: es5`
  - `jsxSingleQuote: true`，`endOfLine: auto`
- **ESLint**：`frontend/web/eslint.config.mjs`
  - 基于 `@eslint/js` + `typescript-eslint` + `eslint-plugin-vue`
  - 集成 `eslint-plugin-prettier`，格式化冲突以 Prettier 为准
  - 全局注册 Element Plus 组件（ElInput、ElTable 等），避免 no-undef
  - `vue/block-order` → 固定 `template → script → style`
  - `vue/component-name-in-template-casing: PascalCase`
  - `vue/html-self-closing` → 自闭合标签统一风格
- **Stylelint**：`frontend/web/.stylelintrc.cjs`
  - SCSS + Vue 语法支持，postcss-html / postcss-scss 双解析器
  - 继承 `stylelint-config-recess-order`（CSS 属性排序）
  - Tailwind CSS v4 `@reference` / `@custom-variant` 等 at-rule 白名单
- 运行 `pnpm lint` 检查全部，`pnpm lint:fix` 自动修复
- 提交前通过 Husky + lint-staged 自动检查暂存文件

## TypeScript Conventions

- `ref<ProductTable>({} as ProductTable)` — 空对象必须用 `as` 显式断言，不能直接 `ref<ProductTable>({})`。Vue 的 ref 类型推导对空对象的泛型推断与接口类型不兼容。
- **弹框组件化**：所有 Dialog/Modal 必须抽取为独立 `.vue` 组件，通过 import 引入。通用/可复用的放 `components/`，页面专属的放当前目录。禁止在页面文件中内联大量弹框模板。

## 组件开发规范

### HTTP 拦截器与消息提示

- HTTP 拦截器（`src/utils/http/index.ts`）**自动**对所有非 GET 请求成功后执行 `ElMessage.success(data.msg)`
- **禁止**在业务代码中对非 GET 请求手动调用 `ElMessage.success()`，否则会弹出两条重复消息
- 仅在以下场景手动调用：纯前端操作（如复制成功）、GET 请求的特殊提示

### FaTable 展开行

- FaTable 支持 `#expand` 插槽用于展开行内容（优先级高于 `col.formatter`）
- 无 `#expand` 插槽时回退到 `col.formatter` 返回 VNode
- 展开行内嵌套子表格使用原生 `<ElTable>`，不使用 FaTable（避免递归）
- 展开行内容用 **template 语法**，不用 `h()` 渲染函数

### FaTable 与 ElTable 区别

- FaTable 是封装组件，内部透传 ElTable 属性/事件，但以下需注意：
  - 事件（如 `@expand-change`、`@selection-change`）通过 `attrs` 透传到 ElTable，无需在 FaTable 中显式声明
  - 列配置通过 `columns` prop 传入，不使用默认插槽
  - FaTable 不要同时有 `v-for` 列和 `<template #default>` 插槽——会产生 "Extraneous children" 警告

### 表单 Drawer 模式

- 详情/编辑/新增共用一个 FaDrawer，通过 `dialogVisible.type` 区分模式
- 详情模式：`<ElDescriptions>` 展示
- 编辑/新增模式：`<ElForm>` 表单
- 关闭 Drawer 时必须重置表单 + 清除校验状态

### 嵌套管理（主从表）

- 主表使用 FaTable + 展开行
- 从表在展开行内用原生 `<ElTable>` 渲染
- 从表的 CRUD 操作完成后，通过 `refreshProviderModels(id)` 按主表行 ID 刷新对应从表数据
- 从表新增时自动填充外键（如 `provider_id`），无需用户手动选择

## Reference Docs

- 项目概览：[README.md](../../README.md)
- 全局统一规范：[AGENTS.md](../../AGENTS.md)
