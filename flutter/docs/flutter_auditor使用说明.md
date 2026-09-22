# flutter_auditor 使用说明

> 面向 FastapiAdmin Flutter 移动端（`flutter/`）的 `flutter_auditor` 审计工具使用指南。
> 关联实施计划：`docs/superpowers/plans/2026-07-31-flutter-auditor-managed-check.md`

## 简介

`flutter_auditor` 是一款本地运行的 Flutter 项目健康审计 CLI（MIT 协议）。它一次扫描覆盖**平台配置文件**（`AndroidManifest.xml`、Network Security Config、`Info.plist`）、**Dart 源码**和 **`pubspec.yaml` / `pubspec.lock`**，检查：

- **安全配置**：allowBackup、明文流量、exported 组件、debuggable、manifest 权限、备份规则、release 签名（debug key / 硬编码凭据 / key.properties 未忽略）
- **iOS 合规**：ATS 例外、文件共享、使用说明缺失（相机/相册/麦克风等）
- **Dart 源码**：硬编码密钥、不安全网络、不安全存储
- **依赖卫生**：过期 / 弃用 / 未授权 / 声明未使用
- **资源卫生**：声明未引用、超大资源（≥1MB medium、≥5MB high）

所有检查均在本地文件上执行，不上传源码；唯一网络请求是对 pub.dev API 的只读依赖元数据查询。

> ⚠️ **版本提示**：当前使用 v1.1.0（作者非官方发布者，2026-07 发布，迭代较快）。升级前请查看 `CHANGELOG.md` 确认规则变化。

## 安装

```bash
# 全局安装（推荐）
dart pub global activate flutter_auditor

# 将 pub-cache bin 加入 PATH（.zshrc 持久化）
export PATH="$PATH:$HOME/.pub-cache/bin"
```

安装后可随时查看帮助：

```bash
flutter_auditor --help
flutter_auditor audit --help
```

## 基本用法

在 Flutter 项目根目录执行：

```bash
flutter_auditor audit
```

### 常用选项

| 选项                   | 说明                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------ |
| `-v, --verbose`        | 展开显示 low/maintenance 级发现的完整信息                                            |
| `--fail-on <severity>` | 达到该级别即判定失败：`critical` / `high`(默认) / `medium` / `low` / `info` / `none` |
| `--html <path>`        | 生成带图表的 HTML 报告，如 `--html audit_report.html`                                |
| `--open`               | 生成后自动在浏览器打开 HTML 报告                                                     |

示例：

```bash
flutter_auditor audit --html build/audit_report.html --open --fail-on medium
```

## 本项目已集成的命令（Makefile）

在 `flutter/` 下：

```bash
# 运行审计门禁（文本断言，见下方"已知问题"）
make audit

# 生成 HTML 报告
make audit-report
```

- `make audit`：执行审计并以**文本断言**判断门禁——summary 中出现 `High Risk : [1-9]` 即失败（退出码 1）；工具缺失/无法解析汇总时同样失败（fail-closed）。
- `make audit-report`：生成 `build/audit_report.html`（不设门禁，纯报告）。

当前门禁状态：**0 high / 0 medium / 0 low**，`make audit` 输出 `✅ AUDIT GATE PASSED`。

## 审计结果解读

输出包含四段：

```
  ✗  High Risk        : N    ← 高风险（门禁依据）
  ⚠  Medium Risk      : N    ← 中风险
  ⚠  Low Risk         : N    ← 低风险
  ⓘ  Maintenance      : N    ← 维护项（依赖/资源，不影响退出码）
  ✔  Passed Checks    : N    ← 通过项
  Overall Status: ✅ ALL CLEAR (no security issues found)
```

每条发现都带：标题、文件位置（含行号）、严重级、风险说明、**具体修复建议**。

## 忽略 / 压制配置（.flutter_auditor_ignore.yaml）

在项目根目录（`flutter/`）放置 `.flutter_auditor_ignore.yaml` 可压制有依据的发现项，支持三种维度：

```yaml
# 按 audit id 压制整个审计
audits:
  - android_manifest_permissions

# 按 finding id 精确压制
ids:
  - android_exported_components_activity_.MainActivity

# 按文件 glob 压制（相对项目根目录）
files:
  - lib/env/.env.*
```

> 被压制的发现不会静默消失：控制台会显示 `ⓘ N finding(s) suppressed by .flutter_auditor_ignore.yaml`，且被完全压制的审计会以"passed"展示。

**本项目的压制项与依据：**

| 压制对象                                                            | 方式     | 依据                                                                                                                              |
| ------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `.MainActivity` exported                                            | `ids`    | 启动器 Activity（MAIN/LAUNCHER）在 Android 12+ 强制 `exported=true`；项目内无其他 exported 组件                                   |
| CAMERA / RECORD*AUDIO / READ_MEDIA*\* / READ·WRITE_EXTERNAL_STORAGE | `audits` | 对应真实功能（头像拍摄、相册选图、视频通话）；运行时由 `flutter_permission_wizard` 处理；legacy 存储权限均以 `maxSdkVersion` 收敛 |
| `lib/env/.env.{dev,test,prod}`                                      | `files`  | 由 `AppEnv.init()` 运行时按 `ENV` 动态 `dotenv.load()` 加载，静态引用检测为误报，**禁止**从 `pubspec.yaml` 移除                   |

> ⚠️ 注意：`audits` 整类压制会连带掩盖未来新增的危险权限。新增权限前请先评估是否需要细化压制。

## 本项目已完成的修复

| 修复项                                       | 提交      | 说明                                       |
| -------------------------------------------- | --------- | ------------------------------------------ |
| iOS 缺失 `NSPhotoLibraryAddUsageDescription` | `fac501b` | `image_picker` 依赖项，缺失会在 iOS 崩溃   |
| Android 未显式 `allowBackup`                 | `0e654f6` | 管理端存 token，关闭备份防外泄             |
| logo 3MB → 236KB（512×512）                  | `e7f239d` | 消除超大资源                               |
| release 用 debug 密钥签名                    | `0bf1279` | 改为 `key.properties` + 真实 keystore 签名 |

**release 签名说明**：`android/key.properties` 与 `android/app/upload-keystore.jks` 已加入 `.gitignore`，严禁提交；keystore 密码仅存本机。无 `key.properties` 的机器无法打 release 包（预期行为，替代"用公开 debug 密钥发货"）。**团队发版前需将真实 keystore 共享给构建机。**

## 已知问题（上游）

> ⚠️ **`flutter_auditor` v1.1.0 的进程退出码恒为 0**：`main()` 丢弃了 `CommandRunner` 返回码，导致 `--fail-on high` 在"存在高风险项"时进程仍返回 0（报告文本里的 `Exit code: 1` 只是打印，不是真实退出码）。已实测：即使非法命令也退出 0。

因此本项目 `make audit` **不用退出码做门禁**，而是解析输出文本（summary 的 `High Risk : N`），并做 fail-closed（工具缺失/无法解析时失败）：

```make
audit:
	@out=$$(flutter_auditor audit --fail-on high 2>&1); \
	echo "$$out"; \
	echo "$$out" | grep -qE 'High Risk[[:space:]]*:[[:space:]]*[0-9]' || { \
		echo "❌ AUDIT GATE FAILED: cannot parse audit summary (flutter_auditor installed? check PATH)"; \
		exit 1; \
	}; \
	if echo "$$out" | grep -qE 'High Risk[[:space:]]*:[[:space:]]*[1-9]'; then \
		echo "❌ AUDIT GATE FAILED: high-risk findings present (see output above)"; \
		exit 1; \
	fi; \
	echo "✅ AUDIT GATE PASSED"
```

上游修复退出码后，可回归纯 `--fail-on high` 方案（`--fail-on` 已保留）。

## CI 集成建议

`make audit` 已提供可复现的门禁命令，可在任意 CI 中直接使用：

```yaml
# GitHub Actions 示例
- name: flutter_auditor 审计门禁
  run: |
    dart pub global activate flutter_auditor
    export PATH="$PATH:$HOME/.pub-cache/bin"
    cd flutter && make audit
```

> 注意：CI 无 `key.properties` 时 `--fail-on high` 不会触发签名检查的退出码（上游 bug），但 release 构建会失败——这属于预期的安全行为。

## 常见问题（FAQ）

**Q: `flutter_auditor` 找不到命令？**
A: 先 `dart pub global activate flutter_auditor`，并将 `$HOME/.pub-cache/bin` 加入 `PATH`。

**Q: `make audit` 一直失败，提示无法解析汇总？**
A: 说明审计输出里没有 `High Risk : N` 汇总行——通常是 flutter_auditor 未安装或命令出错（fail-closed 设计，宁可失败不静默通过）。

**Q: `.env.prod` / `.env.test` 被报"未使用资源"，能删掉 pubspec 声明吗？**
A: **不能**。它们由 `AppEnv.init()` 运行时按 `ENV` 动态加载，静态检测是误报，已在忽略文件中压制。

**Q: 如何查看被压制的发现项？**
A: 临时把 `.flutter_auditor_ignore.yaml` 改名或清空，再运行 `flutter_auditor audit` 即可看到全部原始发现。

**Q: 依赖升级建议（maintenance 项）怎么处理？**
A: 当前仅剩 `flutter_easyloading`、`connectivity_plus` 有新版本。升级风险较高，建议在独立窗口期升级并回归 `flutter analyze` / `flutter test`。
