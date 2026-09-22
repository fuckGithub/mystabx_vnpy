---
name: uniapp-unibest
description: 'UniApp + Unibest + Wot UI 跨端移动应用开发。关键词：uni-app、Vue3、TypeScript、Wot UI、Pinia、UnoCSS、z-paging。适用于开发小程序/H5/App、移动端 UI/UX、跨端兼容、暗黑模式。'
argument-hint: '页面开发、组件使用、跨端适配、样式规范'
---

# UniApp Unibest 跨端移动应用开发技术文档

> 基于 uni-app 3 + Vue 3 + TypeScript + Wot UI（@wot-ui/ui）的跨端小程序/H5 开发模板。
> 适用于需要覆盖微信/支付宝/百度/抖音/H5/App 等多端的移动端项目。

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 跨端框架 | uni-app 3 (DCloud) | 一套代码适配微信/支付宝/百度/抖音/H5/App 等多端 |
| 模板引擎 | Unibest 4.4+ | 基于 uni-app 的最佳实践开发框架 |
| 前端框架 | Vue 3.4+ | Composition API + `<script setup>` |
| 构建工具 | Vite 5.2+ | 快速开发构建 |
| 语言 | TypeScript 5.8+ | 类型安全 |
| UI 组件库 | Wot UI（@wot-ui/ui） | 官方文档：https://wot-ui.cn/ |
| HTTP 请求 | 原生 uni.request + nativeHttp 封装 | 支持无感 Token 续期、并发请求排队、请求拦截器 |
| 状态管理 | Pinia 2+ | 轻量状态管理，支持持久化 |
| 路由 | uni-app pages.json + 文件系统路由 | `@uni-helper/vite-plugin-uni-pages` 自动生成 |
| 分页列表 | z-paging 2.8+ | 高性能长列表分页组件 |
| CSS 方案 | UnoCSS 66+ + SCSS | 原子化 CSS + 设计 Token 统一管理 |
| 国际化 | vue-i18n 9+ | 多语言支持（可选） |
| 图表 | ECharts | 数据可视化（按需引入） |
| 代码规范 | ESLint 9 + @uni-helper | 统一代码风格 |
| Git 规范 | Husky + lint-staged + commitlint | 提交前自动检查 |
| CI/CD | miniprogram-ci | 微信小程序自动化上传 |

## 项目结构

```
uniapp/
├── src/
│   ├── main.ts                       # 应用入口（SSR 模式）
│   ├── App.vue                       # 根组件（全局样式、全局配置）
│   ├── env.d.ts                      # 环境变量类型声明
│   ├── typings.d.ts / typings.ts     # 全局类型定义
│   ├── pages.json                    # 路由配置（自动生成 + 手动补充）
│   ├── manifest.json                 # 应用配置（图标、名称、权限）
│   ├── api/                          # API 接口层
│   │   ├── system/                   # 系统模块接口
│   │   │   ├── user.ts
│   │   │   └── role.ts
│   │   └── types/
│   ├── components/                   # 全局组件
│   │   ├── UserCard/
│   │   │   └── index.vue
│   │   └── CustomTree/
│   │       └── index.vue
│   ├── hooks/                        # 组合式函数
│   │   ├── useRequest.ts             # 请求封装
│   │   ├── useScroll.ts              # 滚动监听
│   │   └── useUpload.ts              # 上传封装
│   ├── http/                         # HTTP 请求层
│   │   ├── http.ts                   # nativeHttp 封装
│   │   ├── interceptor.ts            # 请求拦截器
│   │   ├── types.ts                  # 请求类型定义
│   │   └── tools/
│   │       ├── enum.ts               # 状态码枚举
│   │       └── queryString.ts        # 查询参数序列化
│   ├── layouts/                      # 布局组件
│   │   └── default.vue               # 默认布局
│   ├── pages/                        # 页面（文件系统路由）
│   │   ├── index/                    # 首页
│   │   ├── login/                    # 登录
│   │   │   └── index.vue
│   │   ├── mine/                     # 我的
│   │   │   └── index.vue
│   │   ├── work/                     # 工作台
│   │   │   ├── menu/
│   │   │   └── user/
│   │   └── ...
│   ├── router/                       # 路由配置
│   │   ├── config.ts                 # 登录策略配置（黑白名单）
│   │   ├── interceptor.ts            # 路由拦截器（登录守卫）
│   │   └── permission.ts             # 权限配置
│   ├── store/                        # Pinia 状态管理
│   │   ├── index.ts                  # Store 入口
│   │   ├── user.ts                   # 用户信息
│   │   ├── token.ts                  # Token 管理（含无感刷新）
│   │   └── app.ts                    # 应用状态
│   ├── style/                        # 全局样式
│   │   ├── variables.scss            # CSS 变量
│   │   ├── index.scss                # 样式入口
│   │   └── uno.scss                  # UnoCSS 配置
│   ├── tabbar/                       # 底部自定义导航栏
│   │   ├── config.ts                 # TabBar 配置
│   │   ├── index.vue                 # TabBar 组件
│   │   ├── TabbarItem.vue            # TabBar 单项
│   │   ├── store.ts                  # TabBar 状态
│   │   └── types.ts                  # TabBar 类型
│   ├── types/                        # 类型定义
│   │   ├── auto-import.d.ts
│   │   └── uni-pages.d.ts
│   └── utils/                        # 工具函数
│       ├── index.ts                  # 通用工具
│       ├── debounce.ts               # 防抖函数
│       ├── systemInfo.ts             # 设备信息
│       ├── toLoginPage.ts            # 跳转登录页
│       ├── uploadFile.ts             # 文件上传
│       └── updateManager.wx.ts       # 微信小程序更新管理器
├── pages.config.ts                   # 页面配置（unibest）
├── manifest.config.ts                # 应用配置（unibest）
├── vite.config.ts                    # Vite 构建配置
├── uno.config.ts                     # UnoCSS 配置 + 设计 Token
├── wot-ui-resolver.ts                # Wot UI 按需导入解析器
├── tsconfig.json                     # TypeScript 配置
└── package.json                      # 依赖管理
```

## 核心架构设计

### 1. 设计体系（Design System）

设计 Token 统一管理，在 `uno.config.ts` 的 `theme` 中定义：

| Token 类别 | 配置项 | 说明 |
|-----------|--------|------|
| 品牌色 | `brand` | 主色，统一品牌标识 |
| 文字色 | `text` → 多级色阶 | 主文/次要/占位反差 |
| 边框色 | `border` → 多级色阶 | 卡片/输入框/分割线 |
| 字号 | 3xs ~ 2xl | 全局字体大小体系 |
| 圆角 | sm ~ full | 按钮/卡片/弹窗圆角 |
| 阴影 | sm ~ lg | 层级阴影深度 |
| 背景色 | `pages.json` → `backgroundColor` | 全局页面背景 |

**布局约束**：
- **禁止 100vh/vw**，根容器使用 `p-safe` 安全区域适配
- **空态不使用 scroll-view**，scroll-view 不设 padding（放内层 view 撑开）

### 2. 路由与登录策略

基于 unibest 的路由方案，使用 `@uni-helper/vite-plugin-uni-pages` 文件系统路由。

**路由配置**：`src/pages.json`（自动生成）+ `src/pages/` 目录结构

**登录策略**（两种模式）：
- **黑名单模式**（默认）：所有页面可访问，仅标记页面需登录
- **白名单模式**：所有页面需登录，白名单页面免登录
- 通过 `router/config.ts` 中的 `LOGIN_STRATEGY` 切换

**路由守卫流程**：
```
uni.switchTab / navigateTo → 路由拦截器 → 检查登录状态 → 未登录跳转登录页
```

**路由拦截器配置**：
- `excludeLoginPathList`：免登录白名单
- `LOGIN_PAGE_ENABLE_IN_MP`：小程序端是否使用 H5 登录页
- `LOGIN_PAGE` / `REGISTER_PAGE`：登录/注册页路径

### 3. HTTP 请求层（nativeHttp）

基于 `uni.request` 的轻量封装（`src/http/http.ts`），命名为 `nativeHttp`：

| 方法 | 功能 |
|------|------|
| `get<T>(url, query?, header?)` | GET 请求 |
| `post<T>(url, data?, query?, header?)` | POST 请求 |
| `put<T>(url, data?, query?, header?)` | PUT 请求 |
| `delete<T>(url, query?, header?)` | DELETE 请求 |

**特性**：
- **无感 Token 续期**：双令牌模式，401 时自动刷新 Token
- **并发请求排队**：多个 401 请求入队等待，续期后统一重放
- **统一错误提示**：Toast 展示业务错误消息
- **请求拦截器**：自动拼接基础 URL、注入 Authorization Header

**请求拦截器流程**（`src/http/interceptor.ts`）：
```
每次请求 → 拦截器 invoke →
  1. 处理 query 参数序列化（支持已有 ? 追加和空?新建）
  2. 拼接 API 基础地址
     - H5：VITE_APP_PROXY_ENABLE=true 时加代理前缀；false 时拼完整 baseUrl + API_PREFIX
     - 小程序：直接拼完整 baseUrl + API_PREFIX
  3. 注入 Authorization: Bearer token
  4. 设置请求超时（60s）
```

### 4. 状态管理

基于 Pinia 的响应式状态管理：

| Store | 用途 | 持久化 |
|-------|------|--------|
| `user.ts` | 用户信息（头像、昵称、手机号等） | ✅ |
| `token.ts` | Token 管理（access_token / refresh_token） | ✅ |
| `app.ts` | 应用状态（主题、配置） | 可选 |

**Token Store 核心逻辑**：
- `validToken`：计算属性，自动检查过期时间，过期自动触发登出
- `refreshToken()`：使用 refresh_token 换取新 access_token，失败时自动登出
- `logout()`：清除所有登录状态，跳转登录页
- `updateNowTime()`：每次访问时更新时间戳，确保持久化 token 时效性准确

### 5. 布局与 TabBar

**布局组件**（`src/layouts/`）：
- `default.vue`：默认布局，集成自定义 TabBar

**TabBar 系统**（`src/tabbar/`）：
- 完全自定义实现，不依赖原生 TabBar
- 支持徽标（badge）、红点（dot）、角标数字（count）
- 多端适配（H5 / 小程序），保持行为一致
- 支持中间突出按钮

### 6. UI 组件体系

基于 Wot UI（`@wot-ui/ui`）的组件库，通过 `wot-ui-resolver.ts` + `unplugin-vue-components` 实现按需自动导入。

**组件优先原则**：能用 Wot UI 官方组件，绝不自定义。

| 需求 | 使用 | 避免 |
|------|------|------|
| 按钮 | `<wd-button>` | 自定义 `.btn` |
| 输入框 | `<wd-input>` | 自定义 `.input` |
| 卡片 | `<wd-card>` / `<wd-cell-group>` | 自定义 `.card` |
| 弹窗 | `<wd-popup>` / `<wd-dialog>` | 自定义弹窗 |
| 列表 | `<wd-cell>` / `<wd-grid>` | 自定义列表 |
| 加载 | `<wd-loading>` / `<wd-skeleton>` | 自定义动画 |
| 空状态 | `<wd-empty>` | 自定义空状态 |

| 组件类别 | 常用组件 |
|----------|----------|
| 基础 | Button、Cell、Icon、Image、Layout、Text |
| 表单 | Input、Picker、Switch、Rate、Upload、Calendar、Slider |
| 反馈 | Dialog、Toast、Notify、ActionSheet、Popup、Loading |
| 展示 | Card、Tag、Badge、Swiper、Steps、Collapse、Skeleton |
| 导航 | Navbar、Tab、Tabs、Sidebar、Sticky、IndexList |

**参考链接**：https://wot-ui.cn/

### 7. 长列表与分页

集成 `z-paging` 提供高性能分页列表：

```vue
<z-paging ref="paging" v-model="dataList" @query="queryData">
  <view v-for="item in dataList" :key="item.id">
    <!-- 列表项 -->
  </view>
</z-paging>
```

**特性**：
- 自动处理分页参数（pageNo / pageSize）
- 下拉刷新 + 上拉加载更多
- 空数据占位图
- 自定义加载/空状态

### 8. 多端适配

通过 unibest 配置支持多平台：

| 平台 | 标识 | 说明 |
|------|------|------|
| H5 | `h5` | 浏览器 Web 端 |
| 微信小程序 | `mp-weixin` | 微信小程序 |
| 支付宝小程序 | `mp-alipay` | 支付宝小程序 |
| App | `app` | 原生 App（iOS / Android） |

**配置**（`package.json` → unibest.platforms）：
```json
{
  "unibest": {
    "platforms": ["h5", "mp-weixin"],
    "uiLibrary": "wot-ui-v2",
    "loginStrategy": true
  }
}
```

**条件编译**：
```vue
<!-- #ifdef H5 -->
H5 专属代码
<!-- #endif -->
<!-- #ifdef MP-WEIXIN -->
微信小程序专属代码
<!-- #endif -->
```

### 9. 微信小程序特有功能

| 功能 | 文件 | 说明 |
|------|------|------|
| 更新管理器 | `utils/updateManager.wx.ts` | 检查小程序新版本并提示更新 |
| 代码上传 | `scripts/upload-weixin.js` | CI/CD 自动化上传体验版 |
| 小程序类型 | `miniprogram-api-typings` | 微信小程序 API 类型声明 |

---

## 强制规则

### 0.1 组件优先原则

能用 Wot UI 官方组件，绝不自定义（参照上面 UI 组件体系表格）。

### 0.2 CSS 统一原则

禁止重复定义相同样式，必须复用：

```scss
// ❌ 错误：每个组件都定义一遍
.user-card { padding: 24rpx; background: var(--color-bg); }
.role-card { padding: 24rpx; background: var(--color-bg); }

// ✅ 正确：统一基础类
.base-card {
  padding: 24rpx;
  background: var(--color-bg);
  border-radius: 16rpx;
}
```

### 0.3 暗黑模式强制要求

所有颜色必须使用 CSS 变量，禁止硬编码：

```scss
// ❌ 错误：硬编码颜色
.card { background: #ffffff; color: #333333; }

// ✅ 正确：使用 CSS 变量
.card { background: var(--color-bg); color: var(--color-text); }
```

---

## CSS 规范

### UnoCSS 原子类 + BEM 混合方案

| 原子类数量 | 方案 |
|-----------|------|
| ≤3 个 | UnoCSS 原子类 |
| >3 个 | BEM CSS 类 |

### 合并原则（元素已有类名时）

```vue
<!-- ❌ 错误：类名 + 原子类混用 -->
<view class="filter-bar flex items-center mt-12rpx"></view>
```

```scss
.filter-bar {
  display: flex;           // 合并 flex
  align-items: center;     // 合并 items-center
  margin-top: 12rpx;       // 合并 mt-12rpx
}
```

### 使用预设快捷类

| 原子类组合 | 预设 | 减少 |
|-----------|------|------|
| `flex items-center` | `flex-start` | 2→1 |
| `flex justify-between items-center` | `flex-between` | 3→1 |
| `flex justify-center items-center` | `flex-center` | 3→1 |

### 暗黑模式 CSS 变量

```scss
:root, page {
  --color-bg: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-bg-tertiary: #ebebeb;
  --color-text: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-placeholder: #9ca3af;
  --color-border: #e5e7eb;
  --color-divider: #f3f4f6;
  --color-primary: #2563eb;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
}

.wot-theme-dark {
  --color-bg: #1f2937;
  --color-bg-secondary: #111827;
  --color-bg-tertiary: #374151;
  --color-text: #f9fafb;
  --color-text-secondary: #9ca3af;
  --color-text-placeholder: #6b7280;
  --color-border: #374151;
  --color-divider: #1f2937;
}
```

### rpx 单位规范

- 设计稿基准：750rpx
- 字体大小：偶数值

| 场景 | 字号 | 说明 |
|------|------|------|
| 辅助信息 | 24rpx | 描述、标签、页脚 |
| 按钮/次要 | 26rpx | 次要操作、筛选按钮 |
| 基础字号 | 28rpx | 正文、列表项 |
| 标题 | 32rpx | 页面标题、重要信息 |

- 间距：4 的倍数（16rpx、24rpx、32rpx）

---

## 命名规范

### 文件命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件 | PascalCase | `UserCard.vue` |
| 页面 | kebab-case 或小写 | `user-profile.vue` |
| 组合式函数 | camelCase + use | `useUserStore.ts` |
| 工具函数 | camelCase | `formatDate.ts` |
| 常量 | UPPER_SNAKE_CASE | `API_PREFIX.ts` |

### 变量命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | camelCase | `userList` |
| 常量 | UPPER_SNAKE_CASE | `MAX_COUNT` |
| 布尔值 | is/has/can 前缀 | `isLoading`, `hasToken` |

### 方法命名

| 动作 | 前缀 | 示例 |
|------|------|------|
| 获取/加载 | fetch/load | `fetchUserList` |
| 提交/保存 | submit/save | `submitForm` |
| 新增 | create | `createUser` |
| 更新 | update | `updateUser` |
| 删除 | delete | `deleteUser` |
| 打开/关闭 | open/close | `openDialog` |
| 事件处理 | handle | `handleSubmit` |

### CSS 命名（BEM）

```scss
.user-card {
  padding: 24rpx;
  background: var(--color-bg);
  border-radius: 16rpx;

  &__header { display: flex; align-items: center; }
  &__avatar { width: 80rpx; height: 80rpx; border-radius: 50%; }
  &__name { font-size: 28rpx; font-weight: 600; color: var(--color-text); }
  &__role { font-size: 24rpx; color: var(--color-text-secondary); }
  &--active { border: 2rpx solid var(--color-primary); }
}
```

---

## 页面模板

### 列表页面模板

```vue
<template>
  <view class="page">
    <wd-search v-model="keyword" placeholder="搜索" @search="handleSearch" />

    <wd-tabs v-model="activeTab" @change="handleTabChange">
      <wd-tab name="all" title="全部" />
      <wd-tab name="active" title="启用" />
      <wd-tab name="inactive" title="禁用" />
    </wd-tabs>

    <scroll-view
      class="list-container"
      scroll-y
      :refresher-enabled="true"
      :refresher-triggered="refreshing"
      @refresherrefresh="handleRefresh"
      @scrolltolower="handleLoadMore">
      <view v-for="item in list" :key="item.id" class="list-item">
        <!-- 列表卡片 -->
      </view>
      <wd-loadmore :state="loadState" />
    </scroll-view>

    <wd-fab icon="add" @click="handleAdd" />
  </view>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

const keyword = ref('')
const activeTab = ref('all')
const list = ref<any[]>([])
const loading = ref(false)
const refreshing = ref(false)
const hasMore = ref(true)
const pageNum = ref(1)

const loadState = computed(() => {
  if (loading.value) return 'loading'
  if (!hasMore.value) return 'finished'
  return 'loading'
})

async function fetchList(isRefresh = false) {
  if (loading.value) return
  loading.value = true
  if (isRefresh) { pageNum.value = 1; list.value = [] }
  try {
    const res = await api.getPage({ keyword: keyword.value, status: activeTab.value, pageNum: pageNum.value })
    list.value = isRefresh ? res.list : [...list.value, ...res.list]
    hasMore.value = res.list.length >= 20
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function handleSearch() { fetchList(true) }
function handleTabChange() { fetchList(true) }
function handleRefresh() { refreshing.value = true; fetchList(true) }
function handleLoadMore() { if (hasMore.value) { pageNum.value++; fetchList() } }
function handleAdd() { /* 跳转新增页 */ }

onLoad(() => fetchList())
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; background-color: var(--color-bg-secondary); }
.list-container { height: calc(100vh - 200rpx); }
</style>
```

---

## 卡片设计规范

### 信息层级原则

**移动端卡片 ≠ Web 表格**

| 层级 | 内容 | 视觉权重 |
|------|------|----------|
| 主信息 | 身份识别 | 最突出 |
| 次信息 | 身份定位 | 中等 |
| 辅助信息 | 联系方式 | 较弱 |
| 元信息 | 时间戳 | 最弱 |

### 卡片规则

- 控制在 3-4 行以内
- 次信息用 `·` 分隔
- 辅助信息用图标前缀
- 操作轻量化：`···` 更多按钮

---

## 小程序兼容性

### 避免使用伪元素

小程序不支持 `::before`、`::after`，改用真实元素：

```vue
<!-- ❌ 错误：使用伪元素 -->
<style>
.hero::after { content: ''; position: absolute; }
</style>

<!-- ✅ 正确：使用真实元素 -->
<view class="hero"><view class="hero-fade"></view></view>
```

### 避免使用 DOM API

小程序不支持 `document`、`window`，使用 UniApp API：

```typescript
// ❌ 错误
document.getElementById('app')

// ✅ 正确
uni.createSelectorQuery().select('#app')
```

---

## 已知陷阱

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| H5 连接服务器超时 | UniApp 页面懒加载 AsyncErrorComponent 问题 | 确保动态导入路径正确，模板页正常即可 |
| 验证码接口返回 500 导致 H5 白屏 | HTTP 500 返回导致 CORS 缺失 | 后端必须返回 `{"enable":false}` 而非 HTTP 500 |
| ref 空对象需要 as 断言 | TypeScript 类型推导限制 | `ref<T>({} as T)` 不可用 `ref<T>({})` |
| 弹框必须组件化 | 维护性要求 | 所有弹框抽取为独立组件 |

---

 ## 代码规范（Prettier + ESLint 约束）
 
 ### Prettier
 
 配置：`uniapp/.prettierrc.yaml`
 
 - `printWidth: 120` — 每行最大 120 字符
 - `singleQuote: true` — 字符串使用单引号
 - `semi: false` — 行尾无分号
 - `tabWidth: 2` — 缩进 2 空格
 - `trailingComma: es5` — ES5 兼容多余逗号
 - `endOfLine: lf` — 换行符使用 LF
 - `bracketSameLine: true` — JSX 右尖括号同行
 
 ### ESLint
 
 配置：`uniapp/eslint.config.mjs`
 
 - 基于 `@uni-helper/eslint-config`（Antfu 风格），集成 `eslint-plugin-prettier` + `eslint-config-prettier`
 - 启用 `unocss`、`vue` 规则集
 - 核心规则：
   - `vue/block-order` → 固定 `script/template` 在 `style` 之前
   - `no-console: off` → 允许 console
   - `ts/no-empty-object-type: off` → 允许空对象类型
   - `unused-imports/no-unused-vars: off` → 关闭未使用变量检查（迁移期容忍）
 
 ### 执行方式
 
 ```bash
 pnpm lint              # 全量 ESLint 检查
 pnpm lint:fix          # 自动修复
 ```
 
 提交前通过 Husky + lint-staged 自动检查暂存文件。
 
 ## 开发规范摘要

1. **文件系统路由**：`src/pages/` 下按功能模块组织目录
2. **页面元数据**：通过 `definePage()` 配置导航栏标题、路由守卫等
3. **API 分层**：`api/` 层定义接口，`service/` 层编排业务逻辑
4. **状态管理**：跨页面共享数据用 Pinia，页面内数据用 `ref`/`reactive`
5. **组件抽取**：通用组件放 `components/`，页面专属组件放当前目录
6. **样式方案**：优先 UnoCSS 原子类（设计 Token 驱动），复杂样式用 SCSS
7. **布局约束**：根容器使用 `p-safe`，禁止 100vh/vw；空态不使用 scroll-view
8. **分页列表**：统一使用 `z-paging` 组件
9. **HTTP 请求**：统一通过 `nativeHttp` 封装，不直接调用 `uni.request`
10. **TypeScript 断言**：`ref<T>({} as T)` 空对象必须用 `as`，不可 `ref<T>({})`

---

## 代码质量检查清单

- [ ] 使用 Wot UI 组件（不自定义）
- [ ] 原子类 ≤3 个，>3 个用 BEM
- [ ] 所有颜色使用 CSS 变量
- [ ] 暗黑模式正常工作
- [ ] 卡片控制在 3-4 行
- [ ] 信息层级清晰
- [ ] 操作使用 `···` 更多按钮
- [ ] 使用 UnoCSS 预设快捷类
- [ ] 所有尺寸使用 rpx 单位
- [ ] 定义 TypeScript 类型
- [ ] 避免伪元素
- [ ] 避免使用 DOM API

## 参考文档

- Wot UI 组件库：https://wot-ui.cn/
 - Wot UI 官方开发技能（组件用法/API/主题/坑位排查）：`.agents/skills/wot-ui-skill.md`
- Unibest 开发框架：https://unibest.tech/
- uni-app 官方文档：https://uniapp.dcloud.net.cn/

## 关于文档

本文档描述了基于 uni-app + Unibest + Wot UI（@wot-ui/ui）的跨端移动应用开发模板的核心架构与开发规范。
模板代码基于 MIT 协议开源，可用于任何商业或非商业项目。
