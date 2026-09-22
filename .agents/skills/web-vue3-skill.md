---
name: vue3-admin
description: 'Vue3 + Element Plus + Vite 管理后台开发。关键词：Vue3、Element Plus、TypeScript、Pinia、ECharts、Axios。适用于开发 CRUD 页面、数据图表、动态路由、权限控制、国际化。'
argument-hint: '页面开发、组件选型、路由配置、表格逻辑'
---

# Vue3 管理后台前端工程模板技术文档

> 基于 Vue 3 + TypeScript + Vite + Element Plus 的企业级管理后台前端模板。
> 适用于 SaaS 管理后台、电商运营系统、CRM、ERP 等需要复杂表格、图表、权限控制的前端项目。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3.5+ | Composition API + `<script setup>` 组合式开发 |
| 构建 | Vite 7+ | 极速 HMR，按需编译 |
| 语言 | TypeScript 5.8+ | 全量类型检查，严格模式 |
| UI 组件库 | Element Plus 2.11+ | 企业级桌面端组件库 |
| 状态管理 | Pinia 3+ | 类型安全的状态管理，支持持久化 |
| 路由 | Vue Router 4+ | Hash 模式路由，支持动态菜单挂载 |
| HTTP 请求 | Axios 1.12+ | 请求/响应拦截器，无感 Token 续期 |
| 国际化 | vue-i18n 11+ | 多语言支持 |
| 拖拽 | vue-draggable-plus | 可视化拖拽排序 |
| 图表 | ECharts 6+ | 丰富的数据可视化组件 |
| 富文本 | wangEditor-next | 富文本编辑器 |
| 工作流 | Vue Flow (vue-flow) | 基于 Node+Edge 的可视化工作流设计器 |
| 内置终端 | vue-web-terminal | 在线命令行终端 |
| 代码编辑器 | CodeMirror 5 | SQL 等代码编辑 |
| CSS | Tailwind CSS 4 + SCSS | 原子化 CSS + 预处理器 |
| 代码规范 | ESLint 9 + Prettier + Stylelint | 统一代码风格 |
| Git 规范 | Husky + lint-staged + commitizen | 提交前自动检查 |

## 项目结构

```
web/
├── src/
│   ├── main.ts                       # 应用入口
│   ├── App.vue                       # 根组件
│   ├── api/                          # API 接口（按模块拆分）
│   │   ├── module_system/            # 系统管理接口
│   │   │   ├── auth.ts              # 认证相关
│   │   │   ├── user.ts              # 用户管理
│   │   │   ├── role.ts              # 角色管理
│   │   │   ├── menu.ts              # 菜单管理
│   │   │   ├── dept.ts              # 部门管理
│   │   │   ├── dict.ts              # 字典管理
│   │   │   ├── log.ts               # 日志管理
│   │   │   ├── notice.ts            # 通知公告
│   │   │   └── ...
│   │   ├── module_monitor/           # 监控接口
│   │   ├── module_generator/         # 代码生成器接口
│   │   ├── module_order/             # 订单接口
│   │   ├── module_product/           # 商品接口
│   │   └── module_xxx/               # 业务模块接口（与后端对应）
│   ├── assets/                       # 静态资源
│   ├── components/                   # 通用组件
│   │   ├── base/                     # 基础组件
│   │   │   ├── fa-back-to-top/
│   │   │   ├── fa-logo/
│   │   │   └── fa-svg-icon/
│   │   ├── business/                 # 业务组件
│   │   │   └── fa-comment-widget/
│   │   ├── cards/                    # 卡片组件
│   │   │   ├── fa-bar-chart-card/
│   │   │   ├── fa-card-list/
│   │   │   ├── fa-stats-card/
│   │   │   └── ...
│   │   ├── charts/                   # 图表组件
│   │   │   ├── fa-bar-chart/
│   │   │   ├── fa-line-chart/
│   │   │   ├── fa-pie-chart/
│   │   │   ├── fa-radar-chart/
│   │   │   └── ...
│   │   ├── forms/                    # 表单组件
│   │   │   ├── fa-search-bar/        # 搜索栏（多字段组合查询）
│   │   │   ├── fa-table-header/      # 表格顶部操作栏
│   │   │   ├── fa-table-header-left/ # 表格左侧按钮组
│   │   │   ├── fa-upload-image/      # 图片上传
│   │   │   ├── fa-excel-export/      # Excel 导出
│   │   │   ├── fa-excel-import/      # Excel 导入
│   │   │   └── ...
│   │   ├── table/                    # 表格组件
│   │   │   ├── fa-table/             # 通用表格（分页、排序、选择）
│   │   │   ├── fa-table-sortable/    # 可排序表格
│   │   │   └── fa-edit-table/        # 可编辑表格
│   │   └── tree/                     # 树形组件
│   │       └── fa-tree/              # 通用树形组件
│   ├── composables/                  # 组合式函数
│   │   ├── useAuth/
│   │   ├── usePermission/
│   │   └── ...
│   ├── directives/                   # 自定义指令
│   ├── enums/                        # 枚举常量
│   ├── hooks/                        # 业务 Hooks
│   │   ├── core/                     # 核心 Hooks
│   │   │   ├── useTable.ts           # 表格通用逻辑
│   │   │   ├── useTableColumns.ts    # 列配置
│   │   │   ├── useTableHeight.ts     # 自适应高度
│   │   │   ├── useChart.ts           # 图表通用逻辑
│   │   │   ├── useTheme.ts           # 主题切换
│   │   │   ├── useSiteConfig.ts      # 站点配置
│   │   │   └── ...
│   │   └── index.ts
│   ├── layouts/                      # 布局组件
│   │   ├── components/               # 布局子组件
│   │   └── index.vue                 # 主布局
│   ├── locales/                      # 国际化
│   │   ├── lang/                     # 语言包
│   │   └── index.ts
│   ├── mock/                         # Mock 数据
│   ├── plugins/                      # Vue 插件注册
│   │   ├── index.ts                  # 插件入口
│   │   ├── element-plus.ts
│   │   ├── icons.ts
│   │   ├── echarts.ts
│   │   └── ...
│   ├── router/                       # 路由
│   │   ├── index.ts                  # 路由入口
│   │   ├── staticRoutes.ts           # 静态路由（登录页、首页、布局壳）
│   │   ├── dynamicRoutes.ts          # 动态路由注册器
│   │   ├── beforeEach.ts             # 路由前置守卫
│   │   ├── afterEach.ts              # 路由后置守卫
│   │   └── MenuProcessor.ts          # 菜单处理
│   ├── store/                        # Pinia 状态管理
│   │   ├── index.ts
│   │   ├── modules/
│   │   │   ├── app.store.ts          # 应用状态
│   │   │   ├── user.store.ts         # 用户状态
│   │   │   ├── menu.store.ts         # 菜单/路由
│   │   │   ├── setting.store.ts      # 设置/配置
│   │   │   ├── dict.store.ts         # 字典数据
│   │   │   ├── notice.store.ts       # 通知公告
│   │   │   └── table.store.ts        # 表格配置
│   ├── styles/                       # 全局样式
│   │   ├── core/                     # 核心样式
│   │   ├── element/                  # Element Plus 覆盖
│   │   └── index.scss
│   ├── types/                        # TypeScript 类型定义
│   │   ├── router/                   # 路由类型
│   │   ├── store/                    # Store 类型
│   │   ├── component/                # 组件类型
│   │   └── ...
│   ├── utils/                        # 工具函数
│   │   ├── auth/                     # 认证工具
│   │   ├── http/                     # Axios 封装
│   │   ├── storage/                  # 存储工具
│   │   ├── common/                   # 通用工具
│   │   ├── i18n/                     # 国际化工具
│   │   ├── icons/                    # 图标工具
│   │   ├── socket/                   # WebSocket 客户端
│   │   └── ...
│   └── views/                        # 页面视图
│       ├── module_system/            # 系统管理页面
│       │   ├── auth/login/           # 登录页
│       │   ├── user/                  # 用户管理
│       │   ├── role/                  # 角色管理
│       │   ├── menu/                  # 菜单管理
│       │   ├── dept/                  # 部门管理
│       │   ├── dict/                  # 字典管理
│       │   └── ...
│       ├── module_monitor/           # 监控页面
│       ├── module_order/             # 订单管理
│       ├── module_product/           # 商品管理
│       ├── module_merchant/          # 商户管理
│       ├── module_statistics/        # 统计报表
│       ├── module_task/              # 任务调度
│       ├── module_generator/         # 代码生成器
│       └── redirect/                 # 重定向页面
├── public/                           # 公共静态资源
├── vite.config.ts                    # Vite 配置
└── package.json                      # 依赖管理
```

## 核心架构设计

### 1. 动态路由与菜单系统

后端菜单数据驱动前端路由注册，支持多级嵌套、外链、iframe 嵌入。

**流程**：
```
登录 → 获取用户菜单列表 → RouteValidator 校验 → RouteTransformer 转换 → RouteRegistry.addRoute()
```

**核心类**：
- `RouteValidator`：校验重名、缺少 component、嵌套路径合法性
- `ComponentLoader`：基于路径字符串的异步组件加载器（import.glob）
- `RouteTransformer`：将 API 返回的菜单数据转换为 `RouteRecordRaw`
- `RouteRegistry`：注册/注销动态路由，支持热更新

**菜单类型支持**：
- 目录(menu type=0)：折叠分组
- 菜单(menu type=1)：常规页面
- 外链(menu type=2)：`<a target="_blank">` 跳转
- iframe(menu type=3)：内嵌页面

### 2. 认证与权限体系

**登录流程**：
```
登录表单 → 验证码验证 → 账号密码 → OAuth 三方登录 → 获取 token → 存储 → 路由跳转
```

**Token 续期机制**：
- 双令牌模式：access_token（短时效）+ refresh_token（长时效）
- 自动续期：401 响应时静默发起 refresh 请求
- 队列重放：并发 401 请求入队等待，续期成功后统一重放
- 滑动过期：用户操作自动延长 token 有效期

**权限控制**：
- **路由级**：菜单数据驱动，未授权菜单不注册路由
- **组件级**：`v-permission` 自定义指令，按钮级权限控制
- **接口级**：Axios 请求头携带 token，后端校验

### 3. 通用页面开发模式

管理后台遵循统一的 CRUD 页面模式：

```
FaSearchBar（搜索条件）
  ↓
FaTableHeader（操作按钮：新增/编辑/删除/导入/导出）
  ↓
FaTable（数据表格：分页、排序、选择）
  ↓
Dialog/Drawer（表单弹窗：新增/编辑详情）
```

**FaTable 特色功能**：
- 列动态显隐（用户自定义保存）
- 列排序拖拽
- 多行选择 + 批量操作
- 自适应高度
- 导出当前页 / 全部数据
- 内置展开行

**搜索栏 FaSearchBar**：
- 支持文本、下拉、日期、树形选择、用户选择等多种字段类型
- 可折叠展开，配置默认展开状态
- 搜索/重置按钮

### 4. HTTP 请求封装

基于 Axios 的完整封装，位于 `src/utils/http/`：

| 特性 | 说明 |
|------|------|
| 请求/响应拦截器 | 统一添加 token、处理响应格式 |
| 错误分类 | `HttpError` 类，区分网络错误、HTTP 状态码错误、业务错误 |
| 自动续期 | 401 自动刷新 token，并发请求排队重放 |
| 多环境支持 | 通过 Vite 环境变量切换 API 地址 |
| 文件下载 | Blob 响应特殊处理 |
| 国际化错误提示 | 基于 i18n 的错误消息映射 |
| 跳过鉴权 | `NO_AUTH_FLAG` 标记绕过 token |

### 5. 插件化架构

通过 `plugins/index.ts` 统一注册所有 Vue 插件（顺序依赖管理）：
1. Pinia（状态管理就绪）
2. Router（路由就绪后可访问 store）
3. Directives（自定义指令注册）
4. vue-i18n（国际化）
5. Element Plus（组件库）
6. ECharts（图表）
7. CodeMirror（代码编辑器）
8. Terminal（内置终端）

### 6. 主题与国际化

- **主题**：支持亮色/暗色模式，通过 Element Plus CSS 变量切换
- **国际化**：vue-i18n + 语言包，支持运行时切换
- **配置持久化**：用户设置存储到 localStorage

### 7. 自定义 Hooks

| Hook | 用途 | 特性 |
|------|------|------|
| `useTable` | 表格数据管理 | 分页、排序、搜索、刷新 |
| `useTableColumns` | 列配置 | 显隐控制、拖拽排序、持久化 |
| `useTableHeight` | 自适应高度 | 窗口 resize 自动计算表格高度 |
| `useTheme` | 主题切换 | 亮色/暗色模式切换与持久化 |
| `useChart` | ECharts 封装 | 自适应 resize、主题跟随 |

### 8. 页面开发规范

1. **模块目录结构**：`views/module_xxx/` 下按功能组织
2. **API 对应关系**：`api/module_xxx/` 与后端 `module_xxx` 一一对应
3. **Dialog/Modal 抽取**：通用 Dialog 放 `components/`，页面专属 Dialog 放当前目录
4. **TypeScript**：`ref<T>({} as T)` 空对象必须用 `as` 断言
5. **品牌色**：`#FF6B35`，统一使用 CSS 变量
6. **菜单 order**：新菜单追加末尾，不插入中间

### 9. 常用组件速查

| 组件路径 | 用途 | 输入参数 |
|----------|------|----------|
| `forms/fa-search-bar` | 多字段搜索栏 | items（搜索项配置）、rules（校验规则） |
| `forms/fa-table-header` | 表格顶部操作栏 | slots:left（左侧按钮组）、columnsCheck（列显隐） |
| `table/fa-table` | 通用数据表格 | columns、data、loading、pagination、row-key |
| `table/fa-edit-table` | 可编辑表格 | 行内编辑模式，支持校验 |
| `tree/fa-tree` | 树形选择 | data、props（配置键名）、filterable |
| `cards/fa-stats-card` | 统计卡片 | title、value、trend、icon |
| `charts/fa-bar-chart` | 柱状图组件 | data、xField、yField、options |
| `charts/fa-line-chart` | 折线图组件 | data、xField、yField、smooth |
| `forms/fa-upload-image` | 图片上传 | v-model、limit、size、accept |
 | `forms/fa-excel-export` | Excel 导出 | columns、data、filename |
 | `forms/fa-excel-import` | Excel 导入 | template、onSuccess、onError |
 
 ## 代码规范（Prettier + ESLint + Stylelint）
 
 ### Prettier
 
 配置：`web/.prettierrc.yaml`
 
 - `printWidth: 120` — 每行最大 120 字符
 - `singleQuote: true` — 字符串使用单引号
 - `semi: false` — 行尾无分号
 - `tabWidth: 2` — 缩进 2 空格
 - `trailingComma: es5` — ES5 兼容多余逗号
 - `jsxSingleQuote: true` — JSX 内使用单引号
 - `endOfLine: auto` — 自动适配换行符
 
 ### ESLint
 
 配置：`web/eslint.config.mjs`
 
 - 基于 `@eslint/js` + `typescript-eslint` + `eslint-plugin-vue`
 - 集成 `eslint-plugin-prettier`，格式化冲突以 Prettier 为准
 - 核心规则：
   - `no-var` → 禁止 var
   - `prefer-const` → 未重新赋值的优先 const
   - `no-console: warn`（生产环境）→ 禁止遗留 console
   - `@typescript-eslint/no-explicit-any: off` → 容忍 any
   - `vue/block-order` → 固定 `template → script → style`
   - `vue/component-name-in-template-casing: PascalCase`
   - `vue/html-self-closing` → 自闭合标签统一风格
   - `vue/require-explicit-emits` → emits 必须显式声明
 
 ### Stylelint
 
 配置：`web/.stylelintrc.cjs`
 
 - SCSS + Vue 双解析器（postcss-html + postcss-scss）
 - 继承 `stylelint-config-recess-order`（CSS 属性排序）
 - Tailwind CSS v4 at-rule 白名单（`@reference`、`@custom-variant` 等）
 - 集成 `stylelint-prettier`，格式冲突以 Prettier 为准
 
 ### 执行方式
 
 ```bash
 pnpm lint              # 全量检查（ESLint + Prettier + Stylelint）
 pnpm lint:fix          # 自动修复
 pnpm lint:format       # Prettier 格式化
 pnpm lint:style        # Stylelint 检查
 ```
 
 提交前通过 Husky + lint-staged 自动检查暂存文件。

## 关于文档

本文档描述了基于 Vue 3 + Element Plus 的企业级管理后台前端模板的核心架构与开发规范。
模板代码基于 MIT 协议开源，可用于任何商业或非商业项目。
