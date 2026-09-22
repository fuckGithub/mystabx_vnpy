---
name: uniapp
description: UniApp 移动端开发规范。当开发 UniApp + Vue 3 移动应用、使用 uView UI 组件、实现移动端 UI/UX、处理小程序兼容性时使用此 skill。
---

# UniApp 移动端开发规范

## 触发条件

- 开发 UniApp 移动端项目
- 使用 uView UI 组件（组件前缀 `u-`）
- 实现移动端 UI/UX
- 处理小程序兼容性问题
- 使用 UnoCSS 原子类

---

## Part 0: 强制规则

> 以下规则在代码审查时逐条检查，不满足即不通过。

### 0.1 组件优先原则

**能用 uView 官方组件，绝不自定义**

| 需求   | 使用                                  | 避免            | 执行方式 |
| ------ | ------------------------------------- | --------------- | -------- |
| 按钮   | `<u-button>`                          | 自定义 `.btn`   | grep -rn '\.btn\b' pages/ |
| 输入框 | `<u-input>` / `<u--input>`            | 自定义 `.input` | grep -rn '\.input\b' pages/ |
| 卡片   | 复用 `universal.scss` 中的 `.card-flat` / `.card-compact` / `.detail-row` | 各自定义 `.card { }` | grep -rn '\.card\s*{' pages/ |
| 弹窗   | `<u-popup>` / `<u-modal>`             | 自定义弹窗      | grep -rn '\.popup\b' pages/ |
| 列表   | `<u-cell>` / `<u-grid>`               | 自定义列表      | — |
| 加载   | `<u-loading>` / `<u-loadmore>`        | 自定义动画      | — |
| 空状态 | `<u-empty mode="message">`            | 自定义空状态 div | grep -rn 'empty-text\|empty-hint' pages/ |
| 表单   | `<u--form>` + `<u-form-item>`         | 自定义表单      | — |
| 搜索   | `<u-search>`                          | 自定义搜索      | — |
| 标签   | `<u-tag>` / `<u-badge>`               | 自定义标签      | — |

**当前违规修复：**

- `salesRetirementDetails.vue:128`、`salesRetirementAction.vue:271` — 自定义 `.card { }` 改为复用 `.card-flat`
- `salesRetirementAction.vue:295` — 自定义 `.popup_fun` 改为 `<u-popup>`
- `salesRetirementDetails.vue:152` — 同上
- `unBoxsHistory.vue:86`、`boxCheckHistory.vue:97`、`kezhiCheckHistory.vue:116` 等 15+ 个文件 — 自定义 `.card` 改为复用 `universal.scss` 中的 `.card-flat` / `.card-compact`

### 0.2 CSS 统一原则

**禁止重复定义相同样式，必须复用。** 通用类已定义在 `styles/universal.scss` 中：

| 场景           | 复用类                              | 替代各自定义 |
| -------------- | ----------------------------------- | ------------ |
| 卡片容器       | `.card-flat` / `.card-compact`      | `.card { }`  |
| 明细行         | `.detail-row` + `.detail-row-label/value` | 自定义 flex row |
| 统计栏         | `.stats-bar`                        | 自定义 flex 栏 |
| 搜索栏         | `.search-box`                       | 自定义搜索容器 |
| 标签徽章       | `.badge` / `.badge-primary/success/warning/error` | 自定义标签 |
| 全屏居中       | `.xy-c-full`                        | 自定义居中 flex |
| 底部操作栏     | `.fixed-bottom` + `.page-fixed-p-b` | 自定义底部栏 |

```scss
// ❌ 错误：每个组件都定义一遍
.user-card { padding: 24rpx; background: var(--color-bg); }
.role-card { padding: 24rpx; background: var(--color-bg); }

// ✅ 正确：统一复用
<view class="card-flat">...</view>
```

### 0.3 颜色规范

**禁止硬编码色值，必须使用语义变量或设计令牌色值。**

| 违规色值 | 设计系统色值 | 扫描命令 |
| --------- | ------------ | -------- |
| `#2979ff` | `#2563EB` (primary) | grep -rn "#2979ff" pages/ |
| `'red'`   | `#EF4446` (danger)  | grep -rn "'red'" pages/ |
| `#007aff` | `#2563EB` (primary) | grep -rn "#007aff" pages/ |
| `#f5f5f5` | `#F1F5F9` (bg)     | grep -rn "#f5f5f5" pages/ |
| `#2a90df` | `#2563EB` (primary) | grep -rn "#2a90df\|#2a90" pages/ |

```scss
// ❌ 错误：硬编码
:color="flag ? '#2979ff' : 'red'"

// ✅ 正确：使用设计系统色值
:color="flag ? '#2563EB' : '#EF4446'"
```

**当前违规修复：** 所有 `#2979ff` → `#2563EB`，`'red'` → `'#EF4446'`，`#f5f5f5` → `#F1F5F9`

### 0.4 页面高度规范

**禁止设置 `min-height: 100vh`**，UniApp 页面框架自动提供内容高度。

```scss
// ❌ 错误
.page { min-height: 100vh; }

// ✅ 正确
.page { background: var(--color-bg-secondary); }
```

只在需要禁止滚动的空状态页面使用 `height: 100vh; overflow: hidden`。

**执行：** `grep -rn "min-height: 100vh" pages/` — 已清理完毕。

### 0.5 设计令牌系统

**所有颜色值定义在 `styles/tokens.js` 一处，其他地方引用令牌。**

三种引用方式：

| 使用场景 | 写法 | 示例 |
|----------|------|------|
| CSS/SCSS 样式 | `var(--hr-xxx)` 或 `$hr-xxx` | `background: var(--hr-bg)` |
| 模板 JS 绑定 | `$tokens.xxx` | `:color="$tokens.primary"` |
| script 方法内 | `this.$tokens.xxx` | `this.$tokens.danger` |

**令牌文件：**

```
styles/tokens.js    →  JS 令牌（$tokens 全局可用）
uni.scss             →  SCSS 变量 + CSS 自定义属性
```

```js
// styles/tokens.js — 全部色值定义在此
$tokens.primary      // #2563EB  — CTA/选中
$tokens.primaryDark  // #1E40AF  — 导航栏
$tokens.danger       // #EF4446  — 错误/删除
$tokens.bg           // #F1F5F9  — 页面背景
$tokens.text         // #0F172A  — 正文
$tokens.flagOn       // #2563EB  — 标志开启
$tokens.flagOff      // #EF4446  — 标志关闭
```

```scss
// uni.scss — 一致的 CSS 变量
--hr-primary        // #2563EB
--hr-bg             // #F1F5F9
--hr-danger         // #EF4446
```

**修改色值 = 只改 `tokens.js` 和 `uni.scss` = 全局生效。**

**执行：** `grep -rn "'#2563EB'\|\"#2563EB\"\|'#EF4446'\|'#EF4444'\|'#F1F5F9'" pages/` 检查是否还有硬编码

---

## Part 1: 技术栈

- **Vue** 3 - 前端框架（Composition API + `<script setup>`）
- **Uni-app** - 跨平台框架
- **uView UI** 2.x - UI 组件库（组件前缀 `u-`，easycom 自动导入）
- **TypeScript** - 类型安全
- **UnoCSS** - 原子 CSS
- **Pinia** - 状态管理

### easycom 配置

```json
// pages.json
{
  "easycom": {
    "^u-(.*)": "@/uni_modules/uview-ui/components/u-$1/u-$1.vue"
  }
}
```

---

## Part 2: 目录结构

```
src/
├── api/                    # API 请求
│   ├── system/             # 系统模块
│   │   ├── user.ts
│   │   └── role.ts
│   └── index.ts
├── components/             # 全局组件
│   ├── UserCard/
│   │   └── index.vue
│   └── CustomTree/
│       └── index.vue
├── composables/            # 组合式函数
│   ├── useList.ts          # 列表逻辑
│   ├── useForm.ts          # 表单逻辑
│   └── useAuth.ts          # 认证逻辑
├── enums/                  # 枚举定义
│   ├── ResultCode.ts
│   └── Status.ts
├── pages/                  # 页面
│   ├── index/              # 首页
│   │   └── index.vue
│   ├── login/              # 登录
│   │   └── index.vue
│   ├── mine/               # 我的
│   │   └── index.vue
│   └── work/               # 工作台
│       ├── menu/
│       │   └── index.vue
│       └── user/
│           └── index.vue
├── static/                 # 静态资源
│   ├── images/
│   └── icons/
├── stores/                 # Pinia 状态
│   ├── modules/
│   │   ├── user.ts
│   │   └── app.ts
│   └── index.ts
├── styles/                 # 全局样式
│   ├── variables.scss      # CSS 变量
│   ├── index.scss          # 入口
│   └── uno.scss            # UnoCSS 配置
├── utils/                  # 工具函数
│   ├── request.ts          # 请求封装
│   ├── auth.ts             # Token 管理
│   ├── permission.ts       # 权限判断
│   └── format.ts           # 格式化
├── App.vue                 # 根组件
├── main.ts                 # 入口
├── manifest.json           # 应用配置
├── pages.json              # 页面配置
└── uni.scss                # UniApp 样式变量
```

---

## Part 3: CSS 使用边界

### UnoCSS 原子类 + BEM 混合方案

| 原子类数量 | 方案          |
| ---------- | ------------- |
| ≤3 个      | UnoCSS 原子类 |
| >3 个      | BEM CSS 类    |

### 合并原则（元素已有类名时）

```vue
<!-- ❌ 错误：类名 + 原子类混用 -->
<view class="filter-bar flex items-center mt-12rpx">

<!-- ✅ 正确：原子类合并到 CSS 类 -->
<view class="filter-bar">
```

```scss
.filter-bar {
  display: flex; // 合并 flex
  align-items: center; // 合并 items-center
  margin-top: 12rpx; // 合并 mt-12rpx
}
```

### 使用预设快捷类

| 原子类组合                          | 预设           | 减少 |
| ----------------------------------- | -------------- | ---- |
| `flex items-center`                 | `flex-start`   | 2→1  |
| `flex justify-between items-center` | `flex-between` | 3→1  |
| `flex justify-center items-center`  | `flex-center`  | 3→1  |

---

## Part 4: 命名规范

### 文件命名

| 类型       | 规范              | 示例               |
| ---------- | ----------------- | ------------------ |
| 组件       | PascalCase        | `UserCard.vue`     |
| 页面       | kebab-case 或小写 | `user-profile.vue` |
| 组合式函数 | camelCase + use   | `useUserStore.ts`  |
| 工具函数   | camelCase         | `formatDate.ts`    |
| 常量       | UPPER_SNAKE_CASE  | `API_PREFIX.ts`    |

### 变量命名

| 类型     | 规范             | 示例                    |
| -------- | ---------------- | ----------------------- |
| 变量     | camelCase        | `userList`              |
| 常量     | UPPER_SNAKE_CASE | `MAX_COUNT`             |
| 私有变量 | \_ 前缀          | `_internalState`        |
| 布尔值   | is/has/can 前缀  | `isLoading`, `hasToken` |

### 方法命名

| 动作      | 前缀        | 示例            |
| --------- | ----------- | --------------- |
| 获取/加载 | fetch/load  | `fetchUserList` |
| 提交/保存 | submit/save | `submitForm`    |
| 新增      | create      | `createUser`    |
| 更新      | update      | `updateUser`    |
| 删除      | delete      | `deleteUser`    |
| 打开/关闭 | open/close  | `openDialog`    |
| 事件处理  | handle      | `handleSubmit`  |

### CSS 命名（BEM）

```scss
.user-card {
  padding: 24rpx;
  background: var(--color-bg);
  border-radius: 16rpx;

  &__header {
    display: flex;
    align-items: center;
  }

  &__avatar {
    width: 80rpx;
    height: 80rpx;
    border-radius: 50%;
  }

  &__name {
    font-size: 28rpx;
    font-weight: 600;
    color: var(--color-text);
  }

  &__role {
    font-size: 24rpx;
    color: var(--color-text-secondary);
  }

  &--active {
    border: 2rpx solid var(--color-primary);
  }
}
```

---

## Part 5: 页面模板

### 列表页面模板

```vue
<template>
  <view class="page">
    <!-- 搜索栏 -->
    <view class="search-bar">
      <u-search v-model="keyword" placeholder="搜索" @search="handleSearch" />
    </view>

    <!-- 列表 -->
    <scroll-view
      class="list-container"
      scroll-y
      :refresher-enabled="true"
      :refresher-triggered="refreshing"
      @refresherrefresh="handleRefresh"
      @scrolltolower="handleLoadMore"
    >
      <view v-for="item in list" :key="item.id" class="list-item" @click="handleEdit(item.id)">
        <view class="list-item__title">{{ item.name }}</view>
        <view class="list-item__desc">{{ item.desc }}</view>
      </view>
      <u-loadmore :state="loadState" />
    </scroll-view>

    <!-- 空状态 -->
    <u-empty v-if="list.length === 0 && !loading" mode="message" text="暂无数据" icon-color="#CBD5E1" />
  </view>
</template>

<script lang="ts" setup>
import { ref, computed } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import type { ItemVO } from "@/api/system/item/types";

const keyword = ref("");
const list = ref<ItemVO[]>([]);
const loading = ref(false);
const refreshing = ref(false);
const hasMore = ref(true);
const pageNum = ref(1);

const loadState = computed(() => {
  if (loading.value) return "loading";
  if (!hasMore.value) return "noMore";
  return "loading";
});

async function fetchList(isRefresh = false) {
  if (loading.value) return;
  loading.value = true;

  if (isRefresh) {
    pageNum.value = 1;
    list.value = [];
  }

  try {
    const res = await API.getPage({
      keyword: keyword.value,
      pageNum: pageNum.value,
    });
    list.value = isRefresh ? res.data.list : [...list.value, ...res.data.list];
    hasMore.value = res.data.list.length >= 20;
  } finally {
    loading.value = false;
    refreshing.value = false;
  }
}

function handleSearch() { fetchList(true); }
function handleRefresh() { refreshing.value = true; fetchList(true); }
function handleLoadMore() { if (hasMore.value) { pageNum.value++; fetchList(); } }
function handleEdit(id: number) { uni.navigateTo({ url: `/pages/item/edit?id=${id}` }); }

onLoad(() => fetchList());
</script>

<style lang="scss" scoped>
.page {
  background-color: var(--color-bg-secondary);
}

.search-bar {
  padding: 24rpx;
  background-color: var(--color-bg);
}

.list-container {
  height: calc(100vh - 200rpx);
}
</style>
```

---

## Part 6: 卡片设计规范

### 信息层级原则

**移动端卡片 ≠ Web 表格**

| 层级     | 内容     | 视觉权重 | 示例                 |
| -------- | -------- | -------- | -------------------- |
| 主信息   | 身份识别 | 最突出   | 头像 + 用户名 + 状态 |
| 次信息   | 身份定位 | 中等     | 角色 + 部门          |
| 辅助信息 | 联系方式 | 较弱     | 手机号 + 邮箱        |
| 元信息   | 时间戳   | 最弱     | 创建时间             |

### 卡片模板

```vue
<template>
  <view class="user-card">
    <!-- 主信息行 -->
    <view class="user-card__header">
      <u-avatar :src="user.avatar" size="60"></u-avatar>
      <view class="user-card__identity">
        <text class="user-card__name">{{ user.nickname }}</text>
        <text class="user-card__role">{{ user.roleName }} · {{ user.deptName }}</text>
      </view>
      <u-tag :text="user.status === 1 ? '正常' : '禁用'"
        :type="user.status === 1 ? 'success' : 'error'" size="mini" />
    </view>

    <!-- 辅助信息行 -->
    <view class="user-card__contact">
      <u-icon name="phone" size="14" />
      <text>{{ user.mobile }}</text>
      <u-icon v-if="user.email" name="email" size="14" />
      <text v-if="user.email">{{ user.email }}</text>
    </view>

    <!-- 操作按钮 -->
    <view class="user-card__actions" @click.stop="showActions">
      <u-icon name="more-dot-fill" />
    </view>
  </view>
</template>

<script setup lang="ts">
import type { UserVO } from "@/api/system/user/types";

defineProps<{ user: UserVO }>();
const emit = defineEmits<{ edit: [id: number]; delete: [id: number] }>();

function showActions() {
  uni.showActionSheet({
    itemList: ["编辑", "删除"],
    success: ({ tapIndex }) => {
      if (tapIndex === 0) emit("edit", props.user.id);
      if (tapIndex === 1) emit("delete", props.user.id);
    },
  });
}
</script>

<style lang="scss" scoped>
.user-card {
  position: relative;
  padding: 24rpx;
  background: var(--color-bg);
  border-radius: 16rpx;

  &__header {
    display: flex;
    align-items: center;
    gap: 16rpx;
  }

  &__identity {
    flex: 1;
    min-width: 0;
  }

  &__name {
    display: block;
    font-size: 28rpx;
    font-weight: 600;
    color: var(--color-text);
  }

  &__role {
    display: block;
    font-size: 24rpx;
    color: var(--color-text-secondary);
    margin-top: 4rpx;
  }

  &__contact {
    display: flex;
    align-items: center;
    gap: 8rpx;
    margin-top: 12rpx;
    font-size: 24rpx;
    color: var(--color-text-secondary);
  }

  &__actions {
    position: absolute;
    right: 24rpx;
    bottom: 24rpx;
    padding: 16rpx;
  }
}
</style>
```

### 卡片规则

- **控制在 3-4 行以内**
- **次信息用 `·` 分隔**
- **辅助信息用 `u-icon` 图标前缀（不使用 emoji）**
- **操作轻量化：`···` 更多按钮**

---

## Part 7: 暗黑模式 CSS 变量

```scss
:root,
page {
  /* 背景色 */
  --color-bg: #ffffff;
  --color-bg-secondary: #f5f5f5;
  --color-bg-tertiary: #ebebeb;

  /* 文字色 */
  --color-text: #1f2937;
  --color-text-secondary: #6b7280;
  --color-text-placeholder: #9ca3af;

  /* 边框色 */
  --color-border: #e5e7eb;
  --color-divider: #f3f4f6;

  /* 功能色 */
  --color-primary: #2563eb;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;

  /* 渐变背景 */
  --color-primary-light: rgba(37, 99, 235, 0.1);
  --color-success-light: rgba(16, 185, 129, 0.1);
  --color-warning-light: rgba(245, 158, 11, 0.1);
  --color-danger-light: rgba(239, 68, 68, 0.1);
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

---

## Part 8: rpx 单位规范

- 设计稿基准：750rpx
- 字体大小：偶数值

| 场景      | 字号  | 说明               |
| --------- | ----- | ------------------ |
| 辅助信息  | 24rpx | 描述、标签、页脚   |
| 按钮/次要 | 26rpx | 次要操作、筛选按钮 |
| 基础字号  | 28rpx | 正文、列表项       |
| 标题      | 32rpx | 页面标题、重要信息 |

- 间距：4 的倍数 `16rpx`、`24rpx`、`32rpx`

---

## Part 9: 小程序兼容性

### 避免使用伪元素

小程序不支持 `::before`、`::after`，改用真实元素：

```vue
<!-- ❌ 错误：使用伪元素 -->
<style>
.hero::after {
  content: "";
  position: absolute;
  /* ... */
}
</style>

<!-- ✅ 正确：使用真实元素 -->
<template>
  <view class="hero">
    <view class="hero-fade"></view>
  </view>
</template>
```

### 避免使用 DOM API

小程序不支持 `document`、`window`，使用 UniApp API：

```typescript
// ❌ 错误
document.getElementById("app");

// ✅ 正确
uni.createSelectorQuery().select("#app");
```

### uView UI 小程序注意事项

- uView 已内置小程序适配，uni_modules 方式引入无需额外配置
- 使用 `u-icon` 替代 emoji 图标，确保跨平台一致性
- uView 的 `u--input` / `u--form` 等组件支持 `v-model` 双向绑定

---

## Part 10: 代码质量检查清单

### 10.1 扫描命令

在提交前执行以下命令检查违规：

```bash
# 0.1 组件优先 — 扫描自定义卡片
grep -rn '\.card\s*{' pages/ --include="*.vue"
grep -rn 'empty-text\|empty-hint' pages/ --include="*.vue"

# 0.3 硬编码色值 — 扫描禁止色号
grep -rn '"#2979ff"\|"#007aff"\|"#2a90df"\|"#3573fb"\|background-color: #f5f5f5' pages/ --include="*.vue"

# 0.4 页面高度 — 扫描违规
grep -rn 'min-height: 100vh' pages/ --include="*.vue"

# 0.5 令牌引用 — 扫描模板中硬编码 hex 色值
grep -rn "'#2563EB'\|'#EF4446'\|'#F1F5F9'\|'#1E40AF'\|'#10B981'\|'#F59E0B'" pages/ --include="*.vue"
```

### 10.2 逐项检查

- [ ] 使用 uView UI 组件（不自定义）
- [ ] 组件 easycom 配置正确
- [ ] 原子类 ≤3 个，>3 个用 BEM
- [ ] 所有颜色使用 CSS 变量或 `$tokens` 引用
- [ ] 模板 `:color`/`:style` 绑定使用 `$tokens.xxx`，无硬编码 hex
- [ ] 暗黑模式正常工作
- [ ] 卡片控制在 3-4 行
- [ ] 信息层级清晰
- [ ] 操作使用 `···` 更多按钮
- [ ] 使用 UnoCSS 预设快捷类
- [ ] 所有尺寸使用 rpx 单位
- [ ] 定义 TypeScript 类型
- [ ] 避免伪元素
- [ ] 避免使用 DOM API
- [ ] 页面无 `min-height: 100vh`
- [ ] 图标使用 `u-icon`，不使用 emoji

### 10.3 当前执行状态

| 规则 | 状态 | 说明 |
|------|------|------|
| 0.3 `#2979ff` → `#2563EB` | ✅ 已修复 | 9 个文件 39 处 |
| 0.3 `'red'` → `'#EF4446'` | ✅ 已修复 | 同上 |
| 0.3 `#f5f5f5` → `#F1F5F9` | ✅ 已修复 | 2 个文件 |
| 0.4 `min-height: 100vh` | ✅ 已清理 | 6 个文件 |
| 0.1 `.card { }` 复用 | ⚠️ 待处理 | 15+ 文件需要验证后迁移 |
| 0.5 令牌系统建立 | ✅ 已完成 | `styles/tokens.js` + `Vue.prototype.$tokens` + CSS 变量 |
| 0.5 模板迁移 `$tokens` | ✅ 已完成 | 9 个文件 39 处 `:color` 绑定改为 `$tokens.primary/danger` |
| `#f5f5f5` → `var(--hr-bg)` | ✅ 已完成 | 19 个文件 |
