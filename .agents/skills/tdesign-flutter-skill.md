---
name: tdesign-flutter
description: Use when 需要在 FastapiAdmin Flutter 移动端新增或优化 TDesign（tdesign_flutter fork 0.2.7）组件、排查 TDesign 样式/品牌色问题、或使用按钮/弹窗/Toast/加载/轮播等组件时加载。含 fork 版 API 差异（onTap/TDButtonTheme/TDAlertDialog 等）与落地案例。
---

# TDesign Flutter 组件库指南（fork 0.2.7）

> 适用项目：fastapiadmin_mobile（FastapiAdmin Flutter 移动端）
> 版本：`tdesign_flutter` **0.2.7**（git fork `runoob-coder/tdesign-flutter` @ ref `fix-IconData-for-0.2.7`）
> 包位置：`~/.pub-cache/git/tdesign-flutter-26865fd5c2195c7fbad0afc851a0238815f745a7/tdesign-component`

## ⚠️ 与官方 pub.dev 版的差异（本 fork 必须以下文为准）

- 枚举命名是 **`TDButtonType` / `TDButtonTheme` / `TDTagTheme`**（大写 `TD` 前缀），**不是** `TdButtonType`
- `TDButton` 没有 `onClick` / `block`，而是 **`onTap`** / **`isBlock`**
- **没有 `TDSwiper` 组件**——轮播需直接用 `flutter_swiper_null_safety` 的 `Swiper` + `TDSwiperPagination` 指示器插件
- **没有 `TDDialog` 类**（官方 `showConfirmDialog` 静态方法不存在）——确认框用 `TDAlertDialog`
- `tdesign-adaptation` 包在本 fork 是**空壳**（只有占位类），**不可用，忽略**

---

## 安装与导入

`pubspec.yaml`（本项目已配置）：

```yaml
tdesign_flutter:
  git:
    url: git@github.com:runoob-coder/tdesign-flutter.git
    ref: fix-IconData-for-0.2.7
    path: tdesign-component
flutter_swiper_null_safety: ^1.0.2 # 轮播 Swiper（本项目暂无轮播，按需加入）
```

导入（单入口，无需单独 import 子文件）：

```dart
import 'package:tdesign_flutter/tdesign_flutter.dart';
```

---

## 主题：品牌蓝注入（⚠️ 本项目尚未接入，按需执行）

**TDesign 组件颜色一律读 `TDTheme.of(context).xxx`（`TDThemeData.colorMap`），不读 `MaterialApp.theme`。** 改 `Material` 主题对 TDesign 组件无效。

> ⚠️ **现状**：fastapiadmin 目前只在 `lib/main.dart` 配了 Material `ColorScheme.fromSeed(seedColor: DesignColors.primary)`，**尚未用 `TDTheme` 包裹**——因此 TDesign 组件当前走默认主题色（`#0052D9` 蓝），与品牌蓝 `DesignColors.primary`（#2563EB）不一致。需要对齐品牌色时，在 `lib/main.dart` 用 `TDTheme` 包裹 `MaterialApp`，品牌色对齐 `DesignColors.primary`：

```dart
return TDTheme(
  data: TDThemeData.defaultData().copyWithTDThemeData(
    'default',
    colorMap: {
      'brandNormalColor': DesignColors.primary,       // 主色 #2563EB
      'brandClickColor': const Color(0xFF1D4ED8),     // 按下（深一档）
      'brandHoverColor': const Color(0xFF3B82F6),     // 悬停（浅一档）
      'brandDisabledColor': const Color(0xFF93C5FD),
      'brandLightColor': const Color(0xFFEFF6FF),
      'brandFocusColor': const Color(0xFFDBEAFE),
    },
  ),
  child: MaterialApp.router(...),
);
```

要点：

- `TDTheme` 未开启多主题时把 `data` 存为**全局单例**，根节点包一次全 app 生效，`TDTheme.of(null)` 也能取到
- **只覆盖想要的键即可**，其余键自动回退默认主题（`copyWithTDThemeData` 生成的 map 无 refs，直接命中覆盖键）
- 品牌色 getter：`brandNormalColor / brandClickColor / brandHoverColor / brandDisabledColor / brandLightColor / brandFocusColor`
- **颜色规则**：页面内一律用 `DesignColors` token，不写 `Color(0x…)` / `Colors.xxx`；TDesign 品牌色走 `TDTheme` 注入

---

## 组件速查

### 1. TDButton — 按钮

```dart
const TDButton({
  Key? key,
  this.text,                          // 文本
  this.size = TDButtonSize.medium,    // large 48 / medium 40 / small 32 / extraSmall 28
  this.type = TDButtonType.fill,      // fill 填充 / outline 描边 / text 文字 / ghost 幽灵
  this.shape = TDButtonShape.rectangle, // round 圆角胶囊
  this.theme,                         // primary 品牌蓝 / danger 危险 / light 浅色底 / defaultTheme 灰
  this.child,                         // 自定义子控件（替代 text）
  this.disabled = false,
  this.isBlock = false,               // 通栏
  this.width, this.height,            // 自定义尺寸
  this.onTap,                         // ← 点击回调（没有 onClick！）
  this.icon, this.iconWidget,         // 图标
  this.iconTextSpacing,
  this.iconPosition = TDButtonIconPosition.left,
  this.gradient,                      // 渐变背景
})
```

```dart
enum TDButtonSize { large, medium, small, extraSmall }
enum TDButtonType { fill, outline, text, ghost }
enum TDButtonShape { rectangle, round, square, circle, filled }
enum TDButtonTheme { defaultTheme, primary, danger, light }
```

**示例**（品牌蓝填充主按钮 / 描边按钮）：

```dart
// 品牌蓝填充按钮（登录页）
TDButton(
  text: context.l10n.loginBtn,
  theme: TDButtonTheme.primary,
  size: TDButtonSize.large,
  shape: TDButtonShape.square,
  width: double.maxFinite,
  onTap: onLogin,
)

// 描边按钮（我的页退出登录）
TDButton(
  text: context.l10n.mineLogout,
  type: TDButtonType.outline,
  theme: TDButtonTheme.primary,
  shape: TDButtonShape.square,
  size: TDButtonSize.medium,
  onTap: onTap,
)
```

> 已在 `login_page.dart`（登录按钮）、`mine_tab.dart`（退出登录）落地。

### 2. TDAlertDialog — 确认弹窗

没有静态 `show*Dialog` 方法，需配合 Flutter 原生 `showDialog`：

```dart
const TDAlertDialog({
  this.title, this.content,           // String? 标题/内容
  this.contentWidget,                 // 自定义内容
  this.leftBtn, this.rightBtn,        // TDDialogButtonOptions? 左右按钮
  this.leftBtnAction, this.rightBtnAction, // 不传 leftBtn/rightBtn 时的回调
  this.radius = 12.0,
  this.showCloseButton,
  this.buttonStyle = TDDialogButtonStyle.normal,
  this.padding = const EdgeInsets.fromLTRB(24, 32, 24, 0),
  this.buttonWidget,                  // 完全自定义按钮区
})
```

```dart
TDDialogButtonOptions({
  required this.title,        // 按钮文案
  required this.action,       // 点击回调（必填；为 null 时默认 Navigator.pop）
  this.titleColor, this.titleSize,
  this.style, this.type, this.theme,   // 按钮样式（theme 可选 TDButtonTheme）
  this.height, this.fontWeight,
})
```

**示例**（取消 + 确认，右侧品牌蓝）：

```dart
await showDialog<void>(
  context: context,
  barrierDismissible: true,
  builder: (ctx) => TDAlertDialog(
    title: '发现新版本',
    content: version.comment,
    leftBtn: TDDialogButtonOptions(
      title: '以后再说',
      action: () => Navigator.pop(ctx),
    ),
    rightBtn: TDDialogButtonOptions(
      title: '去更新',
      action: () { Navigator.pop(ctx); context.go('/update'); },
    ),
  ),
);
```

> 落地范式：确认/提示弹框用 `TDAlertDialog` + `showDialog`；本项目暂无现成弹框，建议后续封装统一确认弹框组件。

### 3. TDToast — 轻提示（全静态，context 必填）

```dart
TDToast.showText(String? text, {required BuildContext context, Duration duration = 3000ms, ...});
TDToast.showSuccess(String? text, {required BuildContext context, ...});  // 成功
TDToast.showWarning(String? text, {required BuildContext context, ...});  // 警告
TDToast.showFail(String? text, {required BuildContext context, ...});     // 失败
TDToast.showIconText(String? text, {IconData? icon, required BuildContext context, ...});

final id = TDToast.showLoading(context: context, text: '加载中...');  // duration 默认极长
TDToast.dismissToast(id);   // 或 TDToast.dismissLoading();
```

> 无 `showToast` 这个名字；`context` 是**必填命名参数**。

### 4. TDLoading — 加载指示器（size 必填）

```dart
const TDLoading({
  required this.size,                    // TDLoadingSize.small/medium/large —— 必填
  this.icon = TDLoadingIcon.circle,      // circle/point/activity
  this.iconColor,                        // 图标颜色（要品牌色显式传 TDTheme.of(context).brandNormalColor）
  this.axis = Axis.vertical,
  this.text,
  this.textColor,
  this.duration = 2000,
})
```

```dart
TDLoading(
  size: TDLoadingSize.small,
  icon: TDLoadingIcon.circle,
  iconColor: TDTheme.of(context).whiteColor1,   // 登录按钮内白色 loading
)
```

> ⚠️ `TDLoading` 没有 `theme` 参数；**不自动取品牌色**，需显式传 `iconColor`。
> 已在 `login_page.dart` 落地（登录按钮内 loading）。

### 5. Swiper — 轮播（无 TDSwiper！）

用 `flutter_swiper_null_safety` 的 `Swiper` + TDesign 指示器插件：

```dart
Swiper.children(
  children: [页A, 页B, 页C],
  onIndexChanged: (i) => setState(() => _currentPage = i),
  pagination: TDSwiperPagination(
    margin: const EdgeInsets.only(bottom: 120),   // 指示器位置
    builder: TDSwiperDotsPagination(
      activeColor: TDTheme.of(context).brandNormalColor,  // 选中色（品牌蓝）
      color: DesignColors.textDisabled,                   // 未选色
      size: 8, activeSize: 8, space: 8,
      roundedRectangleWidth: 20,                  // 选中变胶囊
    ),
  ),
)
```

- `TDSwiperPagination.builder` 可选 `TDSwiperPagination.dots`（圆点）/ `dotsBar`（圆点+矩形）/ `fraction`（数字 1/5）/ `controls`（箭头）
- `TDSwiperDotsPagination.activeColor` 默认取 `TDTheme` 品牌色（配置品牌蓝后自动蓝色）
- 注意：`Swiper.children` 的 `children` 参数要放**最后**（满足 `sort_child_properties_last` lint）

> 本项目暂无轮播场景；需要时按此范式（`flutter_swiper_null_safety` 需 `flutter pub add` 加入依赖）。

### 6. TDTag — 标签（纯展示，无整体 onTap）

```dart
const TDTag(this.text, {
  this.theme,                    // TDTagTheme.primary/warning/danger/success/defaultTheme
  this.size = TDTagSize.medium,
  this.shape = TDTagShape.square, // round 胶囊 / mark
  this.isOutline = false,        // 描边
  this.isLight = false,          // 浅色
  this.disable = false,
  this.needCloseIcon = false, this.onCloseTap,
  ...
})
```

> 是 StatelessWidget，**没有整体 onTap**，需点击时外层包 `GestureDetector`，或直接用 `TDButton(type: text/ghost)`。

---

## 常见坑（排错速查）

| 现象                                          | 原因 / 解法                                                                                                          |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 组件不是品牌蓝 `#2563EB` 而是默认蓝 `#0052D9` | 本项目尚未包 `TDTheme`，或 `brandNormalColor` 未覆盖；TDesign 不读 Material `primaryColor`（见「主题：品牌蓝注入」） |
| `TDButton` 报错 `onClick` 不存在              | fork 用 `onTap`；`block` → `isBlock`                                                                                 |
| `TDDialog` / `showConfirmDialog` 不存在       | 用 `TDAlertDialog` + `showDialog`                                                                                    |
| 想用 `TDSwiper` 轮播组件                      | fork 无此组件，用 `flutter_swiper_null_safety` 的 `Swiper` + `TDSwiperPagination`                                    |
| `TDToast.showToast` 不存在                    | 用 `TDToast.showText(...)`，`context` 必填                                                                           |
| `TDLoading` 颜色不对                          | 无 `theme` 参数，显式传 `iconColor: TDTheme.of(context).brandNormalColor`                                            |
| `tdesign_adaptation` 导入失败/无 API          | 该包是空壳，忽略，只用 `tdesign_flutter` 主包                                                                        |
| 指示器不显示 / 位置不对                       | `TDSwiperPagination.margin` 控制（如 `EdgeInsets.only(bottom: 120)` 为底部按钮留位）                                 |
| `children` 参数位置 lint                      | `Swiper.children` 的 `children` 放参数列表末尾                                                                       |

---

## 组件全清单（60+，按需查阅源码）

`~/.pub-cache/git/tdesign-flutter-26865fd5c2195c7fbad0afc851a0238815f745a7/tdesign-component/lib/src/components/`

`action_sheet` `avatar` `badge` `button` `calendar` `cascader` `cell` `checkbox` `collapse` `dialog` `divider` `drawer` `dropdown_menu` `empty` `fab` `footer` `form` `icon` `image` `image_viewer` `indexes` `input` `link` `loading` `message` `navbar` `notice_bar` `picker` `popover` `popup` `progress` `radio` `rate` `refresh` `result` `search` `sidebar` `skeleton` `slider` `stepper` `steps` `swipe_cell` `swiper` `switch` `tabbar` `table` `tabs` `tag` `text` `textarea` `time_counter` `toast` `tree` `upload`

> 使用新组件前，先读对应目录源码确认构造签名（fork 版 API 可能与官方文档不一致，勿凭记忆）。
