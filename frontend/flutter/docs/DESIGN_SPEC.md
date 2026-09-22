# FastapiAdmin Flutter 移动端 — 设计规范

> 基于 Flutter 3.44 + Material Design 3，统一设计语言。
>
> 所有设计令牌代码入口：`lib/common/style/index.dart`（已通过 `common/index.dart` 间接暴露）
>
> 📐 **跨平台统一规范**：参见 [`../../docs/移动端统一设计规范.md`](../../docs/移动端统一设计规范.md)
> 该文档与 UniApp 共享色彩、间距、圆角、字体等设计令牌，**一次设计决策，两端自动对齐**。

---

## 1. 色彩系统

```dart
import 'package:fastapiadmin_mobile/common/style/index.dart';
```

### 品牌色

| 代码                                     | 色值            | 用途                       |
| ---------------------------------------- | --------------- | -------------------------- |
| `DesignColors.primary`                   | `#2563EB`       | 主色：按钮、导航选中、链接 |
| `DesignColors.primaryContainer(opacity)` | `primary @ 0.1` | 容器背景：徽章、选中项背景 |

### 功能色

| 代码                     | 色值      | 用途          |
| ------------------------ | --------- | ------------- |
| `DesignColors.success`   | `#10B981` | 成功状态      |
| `DesignColors.error`     | `#EF4444` | 错误、危险    |
| `DesignColors.warning`   | `#F97316` | 待处理、紧急  |
| `DesignColors.statusOn`  | `#10B981` | 已通过/已完成 |
| `DesignColors.statusOff` | `#EF4444` | 未通过/待处理 |

### 中性色

| 代码                         | 色值      | 用途               |
| ---------------------------- | --------- | ------------------ |
| `DesignColors.textPrimary`   | `#1E293B` | 标题、重点信息     |
| `DesignColors.textSecondary` | `#334155` | 正文、表单项标签   |
| `DesignColors.textMuted`     | `#64748B` | 次要说明、辅助文字 |
| `DesignColors.textDisabled`  | `#94A3B8` | 禁用状态、占位符   |
| `DesignColors.border`        | `#E2E8F0` | 分割线、卡片描边   |
| `DesignColors.inputFill`     | `#F1F5F9` | 输入框背景填充     |
| `DesignColors.background`    | `#F8FAFC` | 页面背景           |
| `DesignColors.surface`       | `#FFFFFF` | 卡片、弹窗背景     |

---

## 2. 间距系统

```dart
EdgeInsets.all(DesignSize.spaceLg.w);  // 配合 flutter_screenutil
```

| 代码                  | 逻辑值 | 场景                     |
| --------------------- | ------ | ------------------------ |
| `DesignSize.spaceXs`  | 4      | 极小间距                 |
| `DesignSize.spaceSm`  | 8      | 图标与文字间距           |
| `DesignSize.spaceMd`  | 12     | 列表项间距               |
| `DesignSize.spaceLg`  | 16     | 卡片内边距、页面 Padding |
| `DesignSize.spaceXl`  | 20     | 卡片间距、分段间距       |
| `DesignSize.spaceXxl` | 24     | 大块间距                 |

其他常用尺寸：

| 代码                  | 值  | 场景     |
| --------------------- | --- | -------- |
| `DesignSize.iconSm`   | 16  | 小图标   |
| `DesignSize.iconMd`   | 20  | 标准图标 |
| `DesignSize.iconLg`   | 22  | 大图标   |
| `DesignSize.iconXl`   | 24  | 最大图标 |
| `DesignSize.avatarSm` | 40  | 小头像   |
| `DesignSize.avatarMd` | 60  | 标准头像 |
| `DesignSize.avatarLg` | 80  | 大头像   |

---

## 3. 圆角系统

```dart
BorderRadius.circular(DesignSize.radiusXl.r);
```

| 代码                    | 值  | 场景               |
| ----------------------- | --- | ------------------ |
| `DesignSize.radiusSm`   | 4   | 标签、小徽章       |
| `DesignSize.radiusMd`   | 8   | 次要卡片           |
| `DesignSize.radiusLg`   | 10  | 输入框、图标容器   |
| `DesignSize.radiusXl`   | 12  | 主卡片、弹窗       |
| `DesignSize.radiusXxl`  | 16  | 较大容器           |
| `DesignSize.radiusFull` | 999 | 圆形头像、胶囊按钮 |

---

## 4. 投影系统

```dart
boxShadow: [DesignShadow.card];
```

| 代码                    | blur | 不透度 | 场景           |
| ----------------------- | ---- | ------ | -------------- |
| `DesignShadow.card`     | 8    | 4%     | 普通卡片       |
| `DesignShadow.elevated` | 12   | 8%     | 弹窗、高亮卡片 |
| `DesignShadow.floating` | 20   | 10%    | 浮动元素       |

---

## 5. 字体系统

```dart
Text('标题', style: DesignTextStyle.titleLg);
Text('正文', style: DesignTextStyle.bodyOf(context));  // 从 Theme 读取
```

### 字号与字重

| 代码                       | px  | Weight | 场景                  |
| -------------------------- | --- | ------ | --------------------- |
| `DesignTextStyle.display`  | 28  | w700   | 品牌展示、启动页标题  |
| `DesignTextStyle.headline` | 22  | w600   | 页面大标题            |
| `DesignTextStyle.titleLg`  | 18  | w600   | AppBar 标题、区块标题 |
| `DesignTextStyle.titleMd`  | 16  | w500   | 卡片标题、列表主文字  |
| `DesignTextStyle.bodyLg`   | 16  | w400   | 大字正文              |
| `DesignTextStyle.body`     | 14  | w400   | 正文、表单项          |
| `DesignTextStyle.caption`  | 12  | w500   | 标签、角标、次要信息  |
| `DesignTextStyle.tiny`     | 11  | w400   | 极小文字              |

### Theme 上下文

| 代码                                 | 对应 Theme 令牌           |
| ------------------------------------ | ------------------------- |
| `DesignTextStyle.displayOf(context)` | `textTheme.headlineLarge` |
| `DesignTextStyle.titleLgOf(context)` | `textTheme.titleLarge`    |
| `DesignTextStyle.bodyOf(context)`    | `textTheme.bodyLarge`     |

---

## 6. 图标系统

- 图标库：Material Icons（Outlined 风格为主）
- 默认尺寸：
  - Bar/导航内：`20.r` (DesignSize.iconMd)
  - 列表/卡片：`22.r` (DesignSize.iconLg)
  - 页面级：`24.r` (DesignSize.iconXl)
- 选中态切换：导航栏图标 Outlined → Filled（`icon` / `activeIcon`）

---

## 7. 组件装饰器工厂

```dart
import 'package:fastapiadmin_mobile/common/style/index.dart';
```

`DesignDecoration` 提供快速构建常见容器样式：

```dart
// 标准卡片
decoration: DesignDecoration.card(),

// 自定义卡片
decoration: DesignDecoration.card(
  radius: 8,
  color: DesignColors.background,
),

// 状态标签
decoration: DesignDecoration.statusChip(Color(0xFFFEF2F2)),
```

---

## 8. 组件规范速查

| 组件           | 圆角              | 背景色        | 投影         | 内边距        |
| -------------- | ----------------- | ------------- | ------------ | ------------- |
| 卡片 Card      | `radiusXl`(12)    | `surface`     | `shadowCard` | `spaceLg`(16) |
| 输入框 Input   | `radiusLg`(10)    | `inputFill`   | —            | h16 v14       |
| 按钮 Button    | round(10)/pill    | `primary`     | —            | 按尺寸        |
| 标签 Badge     | `radiusSm`(4)     | 功能色@10%    | —            | h6 v2         |
| 头像 Avatar    | `radiusFull`(50%) | `primary@10%` | —            | —             |
| 分割线 Divider | —                 | `border` 1px  | —            | —             |

---

## 9. 布局结构模板

```
SafeArea
 └─ Scaffold
      ├─ AppBar
      │    ├─ background: Colors.white
      │    ├─ bottom: 1px DesignColors.border
      │    └─ title: Text(headline) + centerTitle
      ├─ body
      │    ├─ pagePadding: EdgeInsets.all(DesignSize.spaceLg.w)
      │    └─ cardPadding: EdgeInsets.all(DesignSize.spaceLg.w)
      └─ bottomNavigationBar
           ├─ background: Colors.white
           ├─ selectedItemColor: primary
           └─ unselectedItemColor: textDisabled
```

---

## 10. 代码入口速查

```dart
// 统一引入
import 'package:fastapiadmin_mobile/common/style/index.dart';

// ── 色彩 ──
Container(color: DesignColors.background);
Container(color: colorScheme.primary.withValues(alpha: 0.1));

// ── 间距 ──（配合 screenutil）
EdgeInsets.all(DesignSize.spaceLg.w);
SizedBox(height: DesignSize.spaceMd.h);

// ── 圆角 ──（配合 screenutil）
BorderRadius.circular(DesignSize.radiusXl.r);

// ── 阴影 ──
boxShadow: [DesignShadow.card];

// ── 文字 ──
Text('标题', style: DesignTextStyle.titleLg);
Text('正文', style: DesignTextStyle.bodyOf(context));

// ── 装饰器 ──
decoration: DesignDecoration.card();
decoration: DesignDecoration.card(color: DesignColors.background);

---

## 11. 跨平台参考

> 以下内容在 [`../../docs/移动端统一设计规范.md`](../../docs/移动端统一设计规范.md) 中统一定义，本文仅保留 Flutter 专用部分。

| 统一概念 | 查看位置 | 说明 |
|---------|---------|------|
| 色值表（品牌色/功能色/中性色/暗黑） | 统一规范 §1 | 两端共用同一套色值 |
| 间距系统 | 统一规范 §2 | `spaceXs` ~ `spaceXxl` 6 级 |
| 圆角系统 | 统一规范 §3 | `radiusSm` ~ `radiusFull` 6 级 |
| 投影系统 | 统一规范 §4 | 3 级阴影 |
| 字体系统 | 统一规范 §5 | 8 级字号 + 字重规范 |
| 组件映射表 | 统一规范 §6 | Wot UI ↔ Flutter 组件对照 |
| 卡片设计规范 | 统一规范 §7 | 信息层级 + 模板 |
| 页面布局结构 | 统一规范 §8 | 统一骨架 |
| 命名规范 | 统一规范 §10 | 文件/方法/布尔命名 |
| 跨平台映射速查表 | 统一规范 §11 | UniApp ↔ Flutter API 对照 |
| 设计原则 | 统一规范 §12 | 5 条核心原则 |
| 代码质量检查清单 | 统一规范 §13 | 通用 + 专项检查项 |
```
