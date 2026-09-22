# fastapiadmin_mobile

FastapiAdmin Flutter 移动端管理系统客户端，基于 Flutter 3.44 跨平台开发。

## 功能模块

| 模块        | 路由             | 说明                                    |
| ----------- | ---------------- | --------------------------------------- |
| 启动页      | `/splash`        | 渐变背景 + 倒计时自动跳转               |
| 登录        | `/login`         | 账号密码登录，SM2 加密传输              |
| 主框架      | `/main`          | 底部三 Tab 导航（首页 / 工作台 / 我的） |
| **首页**    | Tab              | 轮播图、快捷导航、通知公告、访问统计    |
| **我的**    | Tab              | 用户信息、常用工具（8格）、推荐服务     |
| 个人资料    | `/profile`       | 展示 & 编辑用户基本信息                 |
| 账号设置    | `/account`       | 修改密码，成功后强制重登                |
| 设置        | `/settings`      | 通知、语言、清缓存、版本信息            |
| 问题反馈    | `/feedback`      | 类型选择 + 内容填写 + 联系方式          |
| 用户管理    | `/work/user`     | 分页列表，支持下拉刷新 & 上拉加载更多   |
| 角色管理    | `/work/role`     | 角色列表                                |
| 通知公告    | `/work/notice`   | 公告列表                                |
| 部门管理    | `/work/dept`     | 部门列表                                |
| 岗位管理    | `/work/position` | 岗位列表                                |
| 菜单/字典等 | `/work/*`        | 占位页，后续接入                        |

## 快速开始

```bash
# 获取依赖
flutter pub get

# ---------- 开发 ----------
# 运行（开发环境，默认加载 .env.dev）
make run-dev
# 或者
flutter run --dart-define=ENV=dev

# 运行 Web（端口 6150）
make run-web
# 或者
flutter run -d chrome --web-port 6150 --dart-define=ENV=dev

# ---------- 构建 ----------
# 构建 APK（生产环境，加载 .env.prod）
make build-prod
# 或者
flutter build apk --dart-define=ENV=prod

# 构建 Web（生产环境）
make build-web
# 或者
flutter build web --dart-define=ENV=prod

# ---------- 其他 ----------
# 运行测试
make test
# 或者
flutter test

# 静态分析
make analyze
# 或者
flutter analyze

# 格式化整个项目（推荐，lib + test）
dart format lib test
```

> 注：
>
> - iOS debug 构建通过桌面图标冷启动存在已知 Flutter 引擎闪退问题（flutter/flutter #67624），请始终用 `flutter run` 启动 debug
> - **iOS 日常重装不要 `flutter clean`**：clean 会清空原生编译产物 + SPM 缓存，触发全量重建，非常慢。
>   增量重装用 `make reinstall-ios`（`xcrun devicectl device uninstall app` 卸载旧版 + `flutter run` 增量构建安装）。
>   仅当遇到 SPM/Pod 解析异常时才考虑清缓存，路径见 `docs/实践记录_真机Release运行与SPM修复.md`
> - **真机 release 部署走三命令方案**（`flutter run --release` 有产物路径 bug，勿用）：
>   ```bash
>   flutter build ios --release                    # 构建 → build/ios/iphoneos/Runner.app（make build-ios-release）
>   flutter install --release -d <UDID>            # 安装到 iPhone（自动卸载旧版）
>   xcrun devicectl device process launch --device <UDID> com.transcendtech.qiyun  # 启动
>   ```

## 环境配置

API 地址等环境变量由 `lib/env/.env.{env}` 文件管理，通过 `--dart-define=ENV=xxx` 选择环境（`dev` / `test` / `prod`）；Android 版本号由同一份 `.env` 的 `APP_VERSION` / `APP_BUILD` 自动推导。完整机制见 **[docs/环境与版本控制.md](docs/环境与版本控制.md)**。

| 命令                     | 加载的文件          |
| ------------------------ | ------------------- |
| `make run-dev`           | `lib/env/.env.dev`  |
| `make build-android-dev` | `lib/env/.env.dev`  |
| `make build-android`     | `lib/env/.env.prod` |

代码中使用 `AppEnv.apiUrl` / `AppEnv.appVersion` 读取（详见 `lib/env/index.dart`）。

## 技术栈

| 类别     | 技术                       | 版本   |
| -------- | -------------------------- | ------ |
| 状态管理 | flutter_riverpod           | 3.3.2  |
| 路由     | go_router                  | 17.3.0 |
| HTTP     | dio                        | 5.9.2  |
| UI 组件  | tdesign_flutter (git fork) | 0.2.7  |
| 屏幕适配 | flutter_screenutil         | 5.9.3  |
| 本地存储 | shared_preferences         | 2.5.5  |
| 加载动画 | flutter_easyloading        | 3.0.5  |

## 项目结构

```
lib/
├── main.dart / global.dart          # 入口 & 全局初始化
├── router/app_router.dart           # GoRouter（含守卫 + 15 条路由）
├── env/                           # 环境配置（AppEnv + .env 文件 + 常量）
│   ├── index.dart                 # AppEnv（加载 + 读取）
│   ├── constants.dart             # 存储键名常量等
│   ├── .env.dev / .env.test / .env.prod
├── common/
│   ├── api/user.dart                # UserApi（登录/用户信息/列表/修改密码等）
│   ├── models/user_profile.dart     # 用户数据模型
│   ├── services/                    # HTTP/Storage 基础设施
│   └── style/                       # 设计令牌（DesignColors/DesignTextStyle）
├── pages/
│   ├── splash/                      # 启动页
│   ├── login/                       # 登录页
│   ├── main/                        # 主框架 + HomeTab + MineTab
│   ├── sub/                         # 个人中心子页（profile/settings/account/feedback）
│   └── work/work_list_page.dart     # 通用工作列表页 + 各模块工厂
└── provider/
    ├── auth/auth_provider.dart      # 认证状态 + 自动加载 profile
    ├── main/main_provider.dart      # 底部导航索引
    └── ...
```

## 设计规范

详见 [AGENTS.md](./AGENTS.md) 和 [DESIGN_SPEC.md](./docs/DESIGN_SPEC.md)。

- 颜色：统一使用 `DesignColors.*`，禁止硬编码
- 适配：使用 `.w`/`.h`/`.r`/`.sp` 后缀（flutter_screenutil）
- 透明度：使用 `.withValues(alpha: x)`，禁止 `.withOpacity()`
