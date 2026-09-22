# Flutter AI 开发规范约束

> 基于 Skills + Rules 机制，统一 Flutter 项目的 AI 辅助开发标准。

---

## 一、技能分级体系

### 层级总览

```
L1 通用技能  ← flutter/skills（官方，首选）
L2 专项技能  ← CPF-Flutter/skills（鸿蒙适配，按需）
L3 定制技能  ← 团队自建 Rules + Skills（强制约束）
```

### 选择策略

| 项目类型       | L1 官方 | L2 鸿蒙 | L3 定制 | 说明              |
| -------------- | ------- | ------- | ------- | ----------------- |
| 纯 iOS/Android | ✅ 必须 | ❌      | 可选    | 标准 Flutter 项目 |
| 鸿蒙跨端       | ✅ 必须 | ✅ 必须 | 可选    | OpenHarmony 适配  |
| 团队协同       | ✅ 必须 | 按需    | ✅ 建议 | 统一架构规范      |

---

## 二、L1 — 官方 Flutter Skills

> 仓库: [flutter/skills](https://github.com/flutter/skills)
> 适用于绝大多数 Flutter 项目，显著提升 AI 生成代码的准确性和架构规范性。

### 安装方式

```bash
# CLI 安装全部技能
npx skills add flutter/skills --skill '*' --agent universal --yes

# 安装指定技能
npx skills add flutter/skills --skill flutter-architecture --agent universal
```

IDE 用户（如 Cursor）也可将仓库放入 `.cursor/skills/` 目录。

### 推荐技能矩阵

#### 基础架构

| 技能                                | 强制内容                | 效果                                        |
| ----------------------------------- | ----------------------- | ------------------------------------------- |
| `flutter-architecture`              | Clean Architecture 分层 | 避免逻辑混杂，View / Domain / Data 三层分离 |
| `flutter-setup-declarative-routing` | GoRouter 声明式路由     | 统一导航配置，支持深度链接                  |

#### UI 构建

| 技能                              | 强制内容              | 效果                               |
| --------------------------------- | --------------------- | ---------------------------------- |
| `flutter-layout`                  | 响应式约束 + 溢出修复 | 自动检测 `Overflowed` 报错并修正   |
| `flutter-theming`                 | Material 3 主题规范   | 统一 Design Token，避免硬编码色值  |
| `flutter-build-responsive-layout` | 多屏适配模式          | Tablet / Desktop / Mobile 三端布局 |
| `flutter-add-widget-preview`      | Widget 预览           | 组件级热重载预览                   |

#### 数据层

| 技能                                   | 强制内容                 | 效果                                          |
| -------------------------------------- | ------------------------ | --------------------------------------------- |
| `flutter-http-and-json`                | 类型安全 JSON 序列化     | 含 Pattern Matching 示例，杜绝 `dynamic` 蔓延 |
| `flutter-state-management`             | 单向数据流规范           | Provider / Riverpod / Bloc 统一写法           |
| `flutter-implement-json-serialization` | `fromJson`/`toJson` 模板 | 自动生成序列化代码                            |

#### 测试与优化

| 技能                           | 强制内容                  | 效果                                   |
| ------------------------------ | ------------------------- | -------------------------------------- |
| `flutter-testing`              | Widget / 集成测试标准流程 | 统一测试目录结构 + Mock 策略           |
| `flutter-add-widget-test`      | Widget 测试模板           | 组件级测试覆盖率                       |
| `flutter-add-integration-test` | 集成测试流程              | 端到端场景验证                         |
| `flutter-performance`          | 16ms 帧预算优化策略       | 针对 Build / Layout / Paint 各阶段分析 |

---

## 三、L2 — 鸿蒙适配技能（专项）

> 仓库: [CPF-Flutter/skills](https://github.com/CPF-Flutter/skills)
> MIT 开源，专用于 OpenHarmony 生态。普通 iOS/Android 项目无需引入。

### 核心能力

| 技能                                             | 用途                                           |
| ------------------------------------------------ | ---------------------------------------------- |
| `flutter-ohos-setup`                             | 一键配置鸿蒙编译链（DevEco Studio + OHOS SDK） |
| `ohos-flutter-plugin-adaptation-necessity-check` | 自动检测需改造的原生插件                       |
| `flutter-ohos-memory-leak`                       | 鸿蒙引擎内存泄漏专项诊断                       |
| `ohos-flutter-crash-analyzer`                    | 鸿蒙崩溃日志解析                               |

### 使用场景

- 鸿蒙 App 初次迁移：运行 `flutter-ohos-setup` 配置环境
- 插件兼容检查：`ohos-flutter-plugin-adaptation-necessity-check` 扫描 `pubspec.yaml`
- 线上问题排查：`ohos-flutter-crash-analyzer` + `flutter-ohos-memory-leak` 组合定位

---

## 四、L3 — 自定义团队规范

> 当官方技能无法满足团队特定架构时（如强制使用 Riverpod / Bloc），通过自建 Skills 和 Rules 补充。

### 机制说明

```
Skills（动态操作指南） + Rules（静态强制约束）
  ↓                        ↓
"怎么做"               "必须遵守什么"
  ↓                        ↓
SKILL.md 定义流程      CLAUDE.md / AGENTS.md 声明规则
```

### 推荐实践

参考 [evanca/flutter-ai-rules](https://github.com/evanca/flutter-ai-rules) 项目结构：

```
项目根/
├── AGENTS.md              ← 完整配置 + 技术栈 + 目录结构
├── CLAUDE.md              ← 快速参考 + 硬性约束
├── .agents/skills/        ← 自定义 Skills
│   └── <skill-name>/
│       └── SKILL.md
```

#### 自定义 Skill 模板

````markdown
# <skill-name>

## 约束

- <强制规则 1>
- <强制规则 2>

## 示例

```dart
// ✅ 正确写法
<code>

// ❌ 禁止写法
<code>
```
````

## 检查清单

- [ ] 规则 1 是否遵守
- [ ] 规则 2 是否遵守

```

### 本项目的自定义约束

记录在 [AGENTS.md](../AGENTS.md) 中，当前强制项：

| 约束 | 类型 | 来源 |
|------|------|------|
| 状态管理使用 Riverpod（Notifier/NotifierProvider） | 架构强制 | AGENTS.md |
| 路由使用 GoRouter（声明式） | 架构强制 | AGENTS.md |
| 颜色透明度使用 `.withValues(alpha:)` | 代码规范 | flutter_lints |
| 文件名使用 `lowercase_with_underscores` | 代码规范 | flutter_lints |
| `BuildContext` 跨 async 需检查 `mounted` | 安全规范 | AGENTS.md |

---

## 五、生效检查清单

### 新项目初始化

- [ ] `flutter create` 标准模板
- [ ] 安装 L1 `flutter/skills` 全部技能
- [ ] 创建 `AGENTS.md` + `CLAUDE.md`
- [ ] 配置 `analysis_options.yaml`（依赖 `flutter_lints`）
- [ ] 初始化 Git + `.gitignore`

### 接入鸿蒙

- [ ] 额外安装 L2 `CPF-Flutter/skills`
- [ ] 运行 `flutter-ohos-setup` 环境检测
- [ ] 运行 `ohos-flutter-plugin-adaptation-necessity-check`

### 持续维护

- [ ] `flutter analyze` 零 error（info/warning 按需清理）
- [ ] Skills 随 flutter/skills 仓库更新
- [ ] L3 自定义规则随团队演进迭代
- [ ] 大版本升级时（如 Flutter 4.0）重新评估技能兼容性

---

## 六、参考资源

- [Flutter Skills 官方仓库](https://github.com/flutter/skills)
- [CPF-Flutter 鸿蒙适配技能](https://github.com/CPF-Flutter/skills)
- [evanca/flutter-ai-rules](https://github.com/evanca/flutter-ai-rules) — 自定义 Rules 参考
- [Flutter 官方文档](https://docs.flutter.dev)
- [Dart 3.12 更新日志](https://dart.dev/resources/dart-3-12)
```
