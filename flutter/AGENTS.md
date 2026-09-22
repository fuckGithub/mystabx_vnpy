# AGENTS — FastapiAdmin Flutter 移动端

> 📖 **入口规范**：[AGENTS.md](../../AGENTS.md) | **项目概览**：[README.md](../../README.md)

## 项目概览

Flutter 3.44 跨平台移动应用模板，FastApiAdmin 管理客户端。基于统一设计系统。

## Default Port

Flutter Web: `http://127.0.0.1:6150`

| 属性     | 值                                            |
| -------- | --------------------------------------------- |
| 项目名   | fastapiadmin_mobile                           |
| 入口     | `lib/main.dart`                               |
| 框架     | Flutter 3.44.4 / Dart 3.12.2                  |
| 代码量   | ~60 Dart 文件                                 |
| 平台     | Android / iOS / macOS / Windows / Linux / Web |
| 设计规范 | [DESIGN_SPEC.md](./docs/DESIGN_SPEC.md)       |
| Web 兼容 | ✅ 已适配                                     |

---

## 技术栈

| 类别     | 技术                              | 版本   | 备注                        |
| -------- | --------------------------------- | ------ | --------------------------- |
| 状态管理 | Riverpod (flutter_riverpod)       | 3.3.2  | Notifier + NotifierProvider |
| 路由     | GoRouter                          | 17.3.0 | 守卫 + refresh              |
| HTTP     | Dio                               | 5.9.2  | CookieSafeAdapter           |
| UI 组件  | TDesign Flutter (tdesign_flutter) | 0.2.7  | **git 引用** — fork 修复版  |
| 屏幕适配 | flutter_screenutil                | 5.9.3  | `.w`/`.h`/`.r`/`.sp`        |
| 本地存储 | shared_preferences                | 2.5.5  |                             |
| 加密     | dart_sm (SM2)                     | 0.1.4  | 登录密码加密                |
| 加载动画 | flutter_easyloading               | 3.0.5  |                             |
| 代码规范 | flutter_lints                     | 6.x    |                             |

---

## Agent Skills（按需加载）

> 技能文件位于仓库根 `.agents/skills/`（本文件相对路径 `../../.agents/skills/`），遇到对应场景时加载。

| Skill                 | 适用场景                                    | 文件路径                                             |
| --------------------- | ------------------------------------------- | ---------------------------------------------------- |
| TDesign 组件          | TDesign fork 0.2.7 组件 API/品牌色/样式排查 | `../../.agents/skills/tdesign-flutter-skill.md`      |
| url_launcher 最佳实践 | 打开链接/拨号/地图导航 + 平台白名单         | `../../.agents/skills/flutter-url-launcher-skill.md` |

### Android 构建配置

- **AGP**: 9.0.1 / **Kotlin**: 2.3.20 / **Gradle**: 9.1.0
- **Java**: 17 (source + target)
- **AndroidX**: 已启用
- **Gradle DSL**: Kotlin DSL (`build.gradle.kts` / `settings.gradle.kts`)
- **Kotlin 主工程**: `MainActivity.kt`

### iOS 构建配置

- **依赖管理**: Swift Package Manager（无 Podfile）
- **最低版本**: iOS 12.0
- **语言**: Swift（AppDelegate.swift）
- **上线指南**: [iOS上线AppStore指南.md](./docs/iOS上线AppStore指南.md)

### Web 兼容性

| 类别     | 说明                                                                                    |
| -------- | --------------------------------------------------------------------------------------- |
| 初始化   | `web/flutter_bootstrap.js` — Flutter 3.44 新模式，工具链自动注入配置                    |
| API 请求 | `CookieSafeAdapter` 用 `if (dart.library.html)` 条件导入，Web 上使用无 `dart:io` 的存根 |
| 系统UI   | `global.dart` 中 `SystemUiOverlayStyle` 统一设置，Android/iOS 共用，Web 跳过            |
| 渲染引擎 | 默认 CanvasKit（WebGL），不支持时自动降级                                               |
| 本地存储 | `shared_preferences` Web 后端 `localStorage`                                            |
| 加密     | `dart_sm` 纯 Dart，全平台兼容                                                           |

---

## 设计系统

> 完整文档见 [DESIGN_SPEC.md](./docs/DESIGN_SPEC.md)

```
lib/common/style/
├── index.dart       ← barrel export（已通过 common/index.dart 暴露）
├── colors.dart      ← DesignColors 色彩令牌（10+ 语义色值）
├── dimensions.dart  ← DesignSize 尺寸/圆角 + DesignShadow 投影
└── styles.dart      ← DesignTextStyle 字体 + DesignDecoration 装饰工厂
```

编码约束：

- ❌ 禁止 `Color(0xFF...)` 硬编码
- ✅ 必须使用 `DesignColors.*`
- ❌ 禁止裸写数值：间距/圆角/尺寸/高度/字号一律用 `DesignSize` token（`spaceLg`/`radiusXl`/`iconMd` 等）或 screenutil（`.w`/`.h`/`.r`/`.sp`），禁止 `EdgeInsets.all(16)` / `BorderRadius.circular(16)` / `SizedBox(height: 16)` / `TextStyle(fontSize: 16)` 裸数值
- ✅ 例外：无对应 token 的微值（如分隔线 `0.5`/`1`、微偏移 `2` 等）需注释说明，或就近取最接近 token
- ✅ 圆角使用 `DesignSize.radiusXl.r`（配合 screenutil）
- ✅ 投影使用 `DesignShadow.card`
- ✅ 文字使用 `DesignTextStyle.*`

```dart
// 引入设计系统
import 'package:fastapiadmin_mobile/common/style/index.dart';
// 或从 lib 层级的相对路径
import '../../common/style/index.dart';
```

---

## 常用命令

```bash
# 获取依赖
flutter pub get

# 开发运行（默认加载 .env.dev）
make run-dev                        # 或 flutter run --dart-define=ENV=dev
make run-web                        # flutter run -d chrome --web-port 6150 --dart-define=ENV=dev

# 生产构建（加载 .env.prod）
make build-prod                     # flutter build apk --dart-define=ENV=prod
make build-web                      # flutter build web --dart-define=ENV=prod

# 其他
make test                           # flutter test
make analyze                        # flutter analyze
```

## 环境配置

环境变量由 `lib/env/.env.{env}` 文件管理，通过 `--dart-define=ENV=xxx` 选择；Android 版本号由同一份 `.env` 的 `APP_VERSION` / `APP_BUILD` 自动推导。完整机制见 **[docs/环境与版本控制.md](docs/环境与版本控制.md)**，此处仅列要点：

```
lib/env/
├── index.dart           # AppEnv（初始化 + 配置读取）
├── constants.dart       # 存储键名常量（STORAGE_USER_*、AVATAR_BASE64_PREFIX）
├── .env.dev             # 开发环境（默认）
├── .env.test            # 测试环境
└── .env.prod            # 生产环境
```

- 启动时 `AppEnv.init()` 根据 `ENV` 值自动加载对应 `.env.{env}` 文件
- 运行时通过 `AppEnv.apiUrl` / `AppEnv.env` / `AppEnv.isDev` / `AppEnv.appVersion` 等读取配置
- 默认 `ENV=dev`，指定文件不存在时自动回退到 `.env.dev`

---

## 项目结构

```
lib/
├── main.dart                        # 入口（含 ThemeData 主题配置）
├── global.dart                      # 全局初始化
├── services/                        # ★ 服务层（核心）
│   ├── index.dart                   # barrel export（api + models + storage + network）
│   ├── api_result.dart              # ApiResult / PageResult / PageParams
│   ├── api/                         # 按模块拆分的 API 接口
│   │   ├── index.dart
│   │   ├── base_api.dart            # API 基类（get/post/put/listPage）
│   │   ├── auth_api.dart            # 认证登录
│   │   ├── user_api.dart            # 当前用户资料
│   │   ├── user_admin_api.dart      # 后台用户管理
│   │   ├── system_api.dart          # 菜单树
│   │   ├── notice_api.dart          # 通知公告
│   │   ├── dept_api.dart            # 部门
│   │   ├── role_api.dart            # 角色
│   │   └── position_api.dart        # 岗位
│   ├── models/
│   │   ├── index.dart
│   │   └── user_profile.dart        # 用户信息模型（JSON 序列化）
│   ├── storage/
│   │   ├── storage_service.dart     # SharedPreferences 封装
│   │   └── token_storage.dart       # 双 Token 存取
│   └── network/                     # 网络核心
│       ├── index.dart
│       ├── api_client.dart          # ApiClient 单例
│       ├── network_status.dart      # 网络质量检测 + 动态超时
│       ├── circuit_breaker.dart     # 熔断器
│       ├── request_queue.dart       # 断网请求队列
│       ├── cookie_safe_adapter.dart
│       ├── web_http_adapter_stub.dart
│       └── interceptors/           # 6 层拦截器链
│           ├── auth_interceptor.dart
│           ├── network_status_interceptor.dart
│           ├── loading_interceptor.dart
│           ├── retry_interceptor.dart
│           ├── response_interceptor.dart
│           └── error_interceptor.dart
├── env/                             # 环境配置
│   ├── index.dart                   # AppEnv
│   ├── constants.dart               # 存储键名常量
│   ├── .env.dev / .env.test / .env.prod
├── router/
│   └── app_router.dart              # GoRouter 路由定义
├── provider/                        # Riverpod Providers
│   ├── auth/
│   ├── login/
│   ├── main/
│   ├── splash/
│   └── storage/
├── pages/
│   ├── splash/
│   ├── login/
│   ├── main/
│   │   └── widgets/
│   │       ├── home_tab.dart
│   │       └── mine_tab.dart
│   ├── sub/
│   │   ├── profile_page.dart
│   │   ├── settings_page.dart
│   │   ├── account_page.dart
│   │   └── feedback_page.dart
│   └── work/
│       └── work_list_page.dart
├── common/
│   ├── index.dart                   # 导出 style/
│   ├── style/                       # 设计系统
│   │   ├── index.dart               # barrel export
│   │   ├── colors.dart              # DesignColors 色彩令牌
│   │   ├── dimensions.dart          # DesignSize + DesignShadow
│   │   └── styles.dart              # DesignTextStyle
│   ├── components/                  # 公共 UI 组件
│   ├── utils/                       # 工具类
│   ├── extension/                   # 扩展方法
│   └── i18n/                        # 国际化
```

### 服务层导入规范

```dart
// 只需一个 import 即可使用所有服务
import '../../services/index.dart';
// 提供：AuthApi, UserApi, NoticeApi, UserProfile, StorageService,
//       TokenStorage, ApiClient, ApiResult, PageResult, PageParams 等

// 设计系统独立导入
import '../../common/style/index.dart';
// 提供：DesignColors, DesignSize, DesignShadow, DesignTextStyle
```

---

## 路由说明

使用 GoRouter，定义在 `lib/router/app_router.dart`。

| 路径             | 页面                | 说明                                  |
| ---------------- | ------------------- | ------------------------------------- |
| `/splash`        | SplashPage          | 启动页（倒计时 5s，自动跳转）         |
| `/login`         | LoginPage           | 登录（密码 SM2 加密）                 |
| `/home`          | HomeTab             | 首页 Tab（StatefulShellRoute branch） |
| `/work`          | PlaceholderWorkPage | 工作台 Tab（StatefulShellRoute branch）|
| `/mine`          | MineTab             | 我的 Tab（StatefulShellRoute branch） |
| `/profile`       | ProfilePage         | 个人资料（展示 & 编辑）               |
| `/settings`      | SettingsPage        | 设置（通知 / 语言 / 缓存 / 版本）     |
| `/account`       | AccountPage         | 账号设置（修改密码 → 强制重登）       |
| `/feedback`      | FeedbackPage        | 问题反馈                              |
| `/work/user`     | UserListPage        | 用户管理（分页列表）                  |
| `/work/role`     | RoleListPage        | 角色管理                              |
| `/work/notice`   | NoticeListPage      | 通知公告                              |
| `/work/dept`     | DeptListPage        | 部门管理                              |
| `/work/position` | PositionListPage    | 岗位管理                              |
| `/work/menu`     | PlaceholderWorkPage | 菜单管理（占位）                      |
| `/work/dict`     | PlaceholderWorkPage | 字典管理（占位）                      |
| `/work/params`   | PlaceholderWorkPage | 参数管理（占位）                      |
| `/work/log`      | PlaceholderWorkPage | 日志管理（占位）                      |
| `/work/config`   | PlaceholderWorkPage | 系统配置（占位）                      |

**路由守卫**: 未登录时自动跳转 `/login`，`/splash` 不受守卫影响。GoRouter 通过 `Provider` 创建一次，auth 变化时重算守卫。登录成功后跳转 `/home`（首页 Tab）。

### 平台自适应路由（iOS 侧滑返回）

所有 `GoRoute` **必须用 `pageBuilder` + `adaptivePage()`**，禁止用 `builder:`：

- GoRoute.builder 创建 `MaterialPage`，**iOS 上不激活原生侧滑返回手势**（历史 bug：全 App 侧滑失效）
- `adaptivePage()`（`app_router.dart` 已定义）：iOS/macOS 返回 `CupertinoPage`（原生侧滑），其他平台返回 `MaterialPage`

```dart
// ❌ 错误 — iOS 无侧滑返回
GoRoute(
  path: '/profile',
  builder: (_, _) => const ProfilePage(),
),

// ✅ 正确 — iOS CupertinoPage 原生侧滑
GoRoute(
  path: '/profile',
  pageBuilder: (_, state) => adaptivePage(const ProfilePage()),
),
```

**主题层配套**：`MaterialApp.router` 的 `theme` 中已配置 `PageTransitionsTheme`，iOS/macOS 使用 `CupertinoPageTransitionsBuilder`。

**新增路由 Checklist**：
1. 用 `pageBuilder` + `adaptivePage()`（不是 `builder`）
2. 文件已 import `cupertino.dart` / `foundation.dart`
3. 若页面含水平滚动容器（TabBarView/PageView）→ 加 `NeverScrollableScrollPhysics()`

---

## 认证与数据流

1. 启动 → SplashPage → 检查本地 token
2. **Token 存在** → 自动调用 `UserApi.profile()` 拉取用户信息 → 设置 `authProfileProvider` → 进入 MainPage
3. **Token 不存在** → 重定向到 LoginPage
4. 登录 → `UserApi.login`（SM2 加密）→ 保存 token → 获取用户信息 → 跳转 MainPage
5. 修改密码成功 → 强制清除 token → 跳转 LoginPage
6. 认证状态由 `authProvider`（`NotifierProvider<AuthNotifier, AuthStatus>`）管理
7. 用户信息由 `authProfileProvider`（`NotifierProvider<AuthProfileNotifier, UserProfile?>`）管理

---

## 国际化（i18n）

> 官方 `gen_l10n`（ARB 文件）+ Riverpod 语言状态实现运行时热切换。设计参照 `docs/国际化与本地化.md`。

### 结构

| 文件                                       | 说明                                                                                                                                         |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `lib/l10n/app_zh.arb` / `app_en.arb`       | **唯一事实源**（两语言 key 必须一致，缺 key 时 `flutter gen-l10n` 即报错）                                                                   |
| `lib/l10n/generated/`                      | gen_l10n 产物（提交进仓库，相对路径导入）                                                                                                    |
| `lib/provider/locale/locale_provider.dart` | `localeProvider`（`NotifierProvider<LocaleNotifier, Locale>`；state 恒为具体 Locale；持久化 `user_locale`；null=跟随系统，监听系统语言变化） |
| `lib/common/i18n/app_l10n.dart`            | 访问层：`context.l10n.xxx`（Widget）/ `ref.l10n.xxx`（Provider/Service，无 BuildContext 场景）                                               |
| `l10n.yaml`                                | gen_l10n 配置（`nullable-getter: false`、`use-named-parameters: true`）                                                                      |

### 接入

`lib/main.dart` 的 `MaterialApp.router` 已接入：`locale: ref.watch(localeProvider)` + `supportedLocales: LocaleNotifier.supportedLocales` + `localizationsDelegates: AppLocalizations.localizationsDelegates`。

### 使用规则

- **Widget**：`context.l10n.loginTitle`；**Provider/Service**：`ref.l10n.someKey`
- **占位符**：命名参数调用（`context.l10n.workListTotal(total: _total)`），ARB 需 `@key.placeholders` 元数据（`example` 必须为非空字符串）
- **富文本多段链接**：每段独立 key + `Text.rich` 拼接，**禁止 `substring` 按字数切分**（i18n 核心反模式）
- **列表/枚举文案**：不要存本地化字符串做比较——用稳定枚举 + `_typeLabel(type, l10n)` 映射
- **切换入口**：`设置 → 语言设置`（跟随系统 / 中文 / English）
- **新增 key 流程**：同步更新 zh/en ARB → `flutter gen-l10n` → 页面用 `context.l10n.xxx`

---

## UI 规范

### 页面布局模板

```
SafeArea
└─ Scaffold
  ├─ AppBar（白底 + 底部 1px border 分割线）
  ├─ body（16.w 内边距）
  └─ bottomNavigationBar（3 tab，图标 Outlined/Filled 切换）
```

### 卡片统一模式

```dart
Container(
  decoration: BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(12.r),
    boxShadow: [BoxShadow(
      color: Colors.black.withValues(alpha: 0.04),
      blurRadius: 8,
      offset: const Offset(0, 2),
    )],
  ),
)
```

### 交互规范

- 所有可点击项使用 `Material + InkWell`（水波纹反馈）
- 输入框聚焦时显示 1.5px 主题色边框
- 空列表显示图标 + 文字提示
- 加载中按钮禁用 + 显示 spinner

---

## 代码规范

- 文件名: `lowercase_with_underscores`（如 `user_login_model.dart`）
- 页面文件: `view.dart` 放 UI，Provider 放 `lib/provider/` 对应目录
- barrel export: `index.dart` 不写 `library xxx;` 声明
- 颜色: 使用 `DesignColors.*` 令牌，禁止硬编码
- 颜色透明度: 使用 `.withValues(alpha: x)` 而非已弃用的 `.withOpacity(x)`
- 跨 async 使用 BuildContext: 必须检查 `mounted`
- Dart SDK 约束: `>=3.12.0 <4.0.0`
- 缩进: 2 spaces（Dart 标准）

---

## Flutter 布局规范（强制）

> 完整规范（§0-13：溢出根因/修复优先级/各场景范式/检查清单）见 **`docs/布局规范.md`**，写新页面/改共享组件**前先过一遍**。
> 核心原则：**让内容决定尺寸，只在内容确实固定时才固定尺寸**；动态内容进 Flex 一律可约束 + 省略；内联文本用富文本整段排版。

### 关键禁令

- ❌ 内联文本流（协议行/富文本拼接）禁止用 `Wrap` 拼行——用 `Row` + `Flexible` + `Text.rich` 整段排版，链接用 `TextSpan(recognizer: TapGestureRecognizer())`；`Wrap` 仅限固定尺寸 item 流（图片网格/chips）
- ❌ 非必要不固定高度；禁止「固定高容器 + 内部自适应组件」组合（`SizedBox(height:96) + TDTextarea` / 固定高 + 等比网格必溢出）
- ❌ 手写 `Row` 内动态文本必须 `Flexible` + `maxLines:1` + ellipsis（裸 Text 会撑破）
- ❌ `Tab` 自绘内容必须显式 `height`（SDK 不按内容自适应，`height:null` → 46/72）；用内置 `icon:` + `child:` 组合
- ❌ 自绘导航栏/底部栏必须叠加 `MediaQuery.paddingOf(context).top/bottom` 状态栏安全区

### 写新页面/组件前检查清单（与 docs/布局规范.md §13 一致）

1. 内联文本流（协议行/富文本）：`Row` + `Flexible` + `Text.rich`，未用 `Wrap` 拼行？
2. 多行输入：用 `TDTextarea.minLines/maxLines`，未包固定高？
3. 动态文本进 `Row`：`Flexible` + `maxLines:1` + ellipsis？
4. 固定行（44/72 等）+ 动态值：单行省略？
5. 动态列表/网格：内容撑高或 `shrinkWrap`，未包固定高？
6. 固定高输入框：未被容器 padding 挤压到低于固有高度？
7. `Tab` 自绘内容：显式 `height` 或内置 `icon+child`？
8. 自绘导航/底部栏：状态栏安全区？
9. 收尾：`flutter analyze` 0 error + 新布局窄屏 widget 冒烟？

---

## 编码铁律（强制）

### ⚠️ 优先复用 TDesign 组件与主题 token（重构原则）

- 重构/优化页面时，**尽量复用现有主题体系**（`DesignColors` / `DesignSize` / `DesignTextStyle`）与 **TDesign 组件**（`TDButton` / `TDToast` / `TDInput` / `TDTextarea` / `TDAlertDialog` 等），减少原生 Material 组件与裸样式
- 已有可复用的 token / 组件时，**不新造色值、不引入平行实现**
- 目标：页面样式收敛到「token 层（主题）+ 组件层（TDesign）」，页面代码只保留结构与业务逻辑
- 简单确认/提示弹框优先用 TDesign 弹框组件，避免 `showDialog` + `AlertDialog` + `TextButton` 手工拼装；仅当弹框需要自定义布局（进度/输入/多选等）时才保留自定义实现并注释原因

### ⚠️ 核心规则：const 构造函数（性能）

- 遇到 `Use 'const' with the constructor to improve performance`（`prefer_const_constructors`）**必须修复**：构造调用全为字面量/编译期常量时，在构造函数调用前加 `const`
- 外层加 `const` 后内层构造函数自动进入 const 上下文——**一处 const 收敛整棵子树**，不要逐个内层重复加
- `final x = const [...]` 收敛为 `const x = [...]`（`prefer_const_declarations`）

### ⚠️ 核心规则：流程控制一律使用大括号（强制）

- `if` / `for` / `while` / `do` / `switch case` 的语句体**一律用大括号 `{}` 包裹**，禁止「无块单语句」换行写法（`if (x)\n  return y;` 必报错）
- 该规则由 `analysis_options.yaml` 的 `curly_braces_in_flow_control_structures: error` **强制执行**（`flutter analyze` 直接报 error，非 info，无法合入）
- ✅ 正确：`if (errMsg != null && errMsg.toString().isNotEmpty) { return errMsg.toString(); }`
- ❌ 错误：`if (errMsg != null && errMsg.toString().isNotEmpty)\n  return errMsg.toString();`
- 注：单行 `if (x) return y;`（`if` 与语句同行）不触发该 lint，但新代码仍建议统一大括号风格

---

## 通用组件规范（强制）

> 以下 TDesign 封装组件在 `lib/common/components/` 目录，新增页面/弹框/导航栏**必须优先使用**，禁止引入平行实现。

### 确认/提示弹框

- **简单确认/提示弹框一律用 TDesign 弹框组件**（如 `TDAlertDialog`），禁止 `ConfirmModal`（已弃用）或 `showDialog` + `AlertDialog` + `TextButton` 手工拼装
- 仅当弹框需要自定义布局（进度/输入/多选等 TDesign 无法表达的复杂场景）时才保留自定义实现并注释原因

### 顶部导航栏

- **页面顶部导航栏一律用 TDesign 导航组件**（如 `TDNavBar`），替代 Material `AppBar` 与自定义手写导航栏
- 右侧图标统一 22dp + `badge` 支持红点
- ⚠️ **坑**：TDNavBar `preferredSize` **只含自身高度，不含 `belowTitleWidget`**——大块内容（如 TabBar）放 `belowTitleWidget` 会溢出被裁剪 → **放 Scaffold body 顶部独立容器**

### 底部导航栏

- 底部 Tab 用 **`TDBottomTabBar`**（替代 Material `BottomNavigationBar`）
- ⚠️ `currentIndex` **外部控制**（组件内部不自动切换）
- 选中/未选中文字色用 `DesignColors` token

---

## 路由进阶规范

### StatefulShellRoute 保活（主 Tab 页）

主框架多 Tab（首页/工作台/我的等）用 **`StatefulShellRoute.indexedStack`**，各 Tab 持有独立 Navigator + IndexedStack 保活：

- **切 Tab 不销毁重建**，滚动/筛选状态保留
- **代价**：4 Tab 页首次挂载即构建（`initState` 各自拉数据）
- 「切回某 Tab 即刷新」由 Riverpod 的 `ref.listen` 驱动（切回自身时触发 `ref.invalidate`）

### 启动流程

1. **SplashPage** → 检查本地 token
2. **Token 存在** → 拉取用户信息 → 进入主框架
3. **Token 不存在** → 重定向到 LoginPage
4. **登录态门控**：`authState.isLoading` 时**放行**（避免刷新/热重启竞态把已登录用户顶到 `/login`）

### 真机运行（iOS release）

```bash
# 三命令方案（flutter run --release 有产物路径 bug，勿用）
flutter build ios --release
flutter install --release -d <UDID>
xcrun devicectl device process launch --device <UDID> <BundleID>
```

详见 [iOS上线AppStore指南.md](./docs/iOS上线AppStore指南.md)。

---

## 跨平台兼容规范

> 项目目标平台：**Android / iOS / Web**。新增功能必须确保三端均可编译运行。

### 1. `dart:io` 使用规则

```dart
// ✅ 正确：用 kIsWeb 保护 dart:io 调用
import 'package:flutter/foundation.dart' show kIsWeb;
// import 'dart:io' show Platform;  // ❌ 禁止：无条件导入 dart:io

if (!kIsWeb) {
  // 仅 native 平台执行的代码
  if (Platform.isAndroid) { ... }
}
```

| 规则                   | 说明                                               |
| ---------------------- | -------------------------------------------------- |
| ❌ `import 'dart:io'`  | 禁止无条件导入，必须加 `if (dart.library.io)` 条件 |
| ❌ `Platform.*` 裸调用 | 必须用 `kIsWeb` 或 `!kIsWeb` 保护                  |
| ✅ 共用逻辑            | 优先使用 `dart:ui` / `dart:html` 等跨平台 API      |
| ✅ 纯 Dart 库          | `dart:math`、`dart:convert` 等全平台安全           |

### 2. 条件导入模式

涉及平台特有 API 时，使用 Dart 条件导入语法：

```dart
import 'native_adapter.dart'
    if (dart.library.html) 'web_adapter_stub.dart';
```

- native (`dart.library.io`) → 编译 `native_adapter.dart`
- web (`dart.library.html`) → 编译 `web_adapter_stub.dart`（无 `dart:io` 依赖）

### 3. 新增依赖检查清单

引入新 package 前逐一确认：

- [ ] 该 package 有 Web 平台实现？→ 检查 pub.dev 的 Platforms 标签
- [ ] 该 package 是否无条件依赖 `dart:io`？→ 查看源码
- [ ] 如果是 native-only package → 用条件导入隔离，Web 上提供替代/禁用

### 4. Web 特有文件说明

| 文件                                             | 用途                                                  |
| ------------------------------------------------ | ----------------------------------------------------- |
| `web/index.html`                                 | 入口 HTML，引用 `flutter_bootstrap.js`                |
| `web/flutter_bootstrap.js`                       | Flutter 3.44 初始化脚本（`{{ }}` 占位符由工具链替换） |
| `web/manifest.json`                              | PWA 清单（name/short_name 与 App 名称同步）           |
| `lib/common/services/web_http_adapter_stub.dart` | Web 编译期存根，替代 `cookie_safe_adapter.dart`       |

### 5. 构建验证

```bash
# 全部通过才可提交
flutter analyze                              # 零问题
flutter build apk --debug                    # Android 编译
flutter build ios --debug --no-codesign      # iOS 编译
flutter build web --no-tree-shake-icons      # Web 编译
# 可选
flutter run -d chrome                        # Web 运行验证
```

### 6. 已知限制

| 限制                                   | 影响平台 | 说明                                                     |
| -------------------------------------- | -------- | -------------------------------------------------------- |
| `tdesign_flutter` 部分文件有 `dart:io` | Web      | 第三方包，不能修改。图片上传/选择相关组件在 Web 上不可用 |

新增限制时请更新此表。

---

## 本地化引用

- `tdesign_flutter` 依赖源为 git SSH：`git@github.com:runoob-coder/tdesign-flutter.git`（`fix-IconData-for-0.2.7` 分支）
