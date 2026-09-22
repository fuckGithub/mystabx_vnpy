# Backend AGENTS.md

> 📖 **入口规范**：[AGENTS.md](../AGENTS.md) | **项目结构**：[README.md](../README.md#-工程结构)

## Overview

FastAPI 后端，Python ≥ 3.14（当前 3.14.7），MySQL 8.0，Redis 7。所有 API 开发须遵守根目录 AGENTS.md 中的通用约定。

> 🐍 **Python 版本以 `admin/.python-version` 为准（当前 3.14.7），
> 且 `pyproject.toml` 的 `requires-python = ">=3.14"` 是其约束表达。**
> 本地 `uv sync` 会按 `.python-version` **重建 venv**，因此改这个文件等于切换解释器。
> 修改 `requires-python` 会同时改变 ruff 推断的 `target-version`，从而改变 lint 基线 ——
> 改之前先用 `ruff check app tests --no-fix` 记录旧基线。
> 注意本机 `uv` 可用解释器：`uv python list --only-installed`。

## Project Structure

```
admin/
├── app/
│   ├── common/          # 公共工具（常量、枚举、响应封装）
│   ├── config/          # 配置（路径、环境变量）
│   ├── core/            # 核心基础设施（DB、Auth、缓存、插件框架）
│   │   ├── plugin/      # 插件框架内核（零业务代码）
│   │   └── discover.py  # 控制器自动发现（内核白名单之一）
│   ├── plugin/          # 全部业务模块（均为插件）
│   │   ├── module_system/   # 系统基础（用户/角色/菜单/部门/参数/字典）
│   │   ├── module_ai/       # AI 对话
│   │   ├── module_task/     # 定时任务
│   │   ├── module_monitor/  # 监控
│   │   ├── module_application/  # 应用管理
│   │   ├── module_generator/    # 代码生成器
│   │   ├── module_common/       # 通用（健康检查/上传等）
│   │   └── module_example/      # 示例
│   ├── scripts/         # 启动装配（init_app）、路由工具
│   └── alembic/         # 数据库迁移（核心）
├── env/                 # 环境配置目录
├── tests/               # 测试
├── main.py              # 启动入口（typer CLI）
├── pyproject.toml       # 依赖管理（uv sync）
├── alembic.ini          # 迁移配置（version_locations 聚合插件迁移）
└── requirements.txt     # 兼容依赖列表
```

> ⚠️ `app/api/` 已删除：全部 HTTP 路由现由插件提供。

## Default Port

后端 API: `http://127.0.0.1:18080` | Swagger: `http://127.0.0.1:18080/api/v1/docs`

## Key Commands

```bash
# 启动（REDIS_ENABLE=False 时自动降级：限流器用内存桶、中间件跳过系统配置读取）
.venv/bin/python main.py run --env=dev

# 数据库迁移
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic heads          # 期望单 head

# 测试
.venv/bin/python -m pytest tests -q        # 期望 188 passed / 2 既有 errors

# 静态检查（两条都必须全绿）
.venv/bin/python -m ruff check app tests main.py --no-fix   # 期望 All checks passed!
.venv/bin/pyright                                           # 期望 0 errors, 0 warnings

# 依赖管理
uv sync
```

## 验证门禁（改完代码必须逐级跑完）

**ruff 只做 lint，不做类型检查 —— 只跑 ruff 不等于没错误。** 历史上
`FileResponse(method=...)`（Starlette 已移除该参数，构造即 TypeError、文件下载全废）、
未拦 `bool` 导致的 `.strip()` 属性错误、以及协程漏 `await`，**全部逃过了 ruff**，
只有 Pyright 类型诊断或真实调用才暴露。故检查顺序固定为：

1. `ruff check` —— 风格与显而易见的缺陷
2. **`pyright`** —— **类型检查，不可省**（配置见 `pyrightconfig.json`）
3. `pytest` —— 行为契约
4. **真实服务端到端调用** —— 最后一步同样不可省：上述下载缺陷只有真发一次
   `POST /api/v1/common/file/download` 才会暴露

`pyrightconfig.json` 要点：`venvPath`/`venv` 必须指向本目录 `.venv`（缺失会让
`reportMissingImports` 凭空多出 300+ 条）；`extraPaths` 含 `scripts`（测试用
`sys.path.insert` 引入 `route_walker.py`）；`reportUnusedCoroutine` 显式设为 `error`
（standard 模式默认关闭，可捕获"裸调用协程未 await"）。

**已知检测盲区（须靠测试兜底）**：`reportUnusedCoroutine` **只**捕获"裸调用"形态；
若协程返回值被赋值后再 `str()` 转换，类型错误会被 `str()` 掩盖，任何静态检查都抓不到
（`RUF029` 也不行 —— 它跳过 `@classmethod`/`staticmethod` 与实例方法）。此类问题的
防线是回归测试，参考 `tests/core/test_file_response_regression.py`。

## Model & Module Convention

新业务模块在 `app/plugin/` 下创建 `module_xxx/` 目录，**不需要任何集中注册**
（旧版的 `app/plugin/__init__.py` 路由聚合已移除）。目录约定：

```
module_xxx/
├── plugin.py      # 必须有模块级 `PLUGIN = Plugin()`，否则整个插件被静默跳过
├── plugin.toml    # name 与目录名一致（剥掉 module_ 前缀），dependencies 无环
├── README.md      # 必备，缺失只记 WARNING 但测试会红
├── model.py / service.py / controller.py / schemas/
└── seeds/data/*.json   # 可选，按外键依赖顺序在 setup() 中声明
```

硬性约定：

- `plugin.py` 中**不要**用 `ctx.add_router()` 重复声明 `controller.py` 顶层 `APIRouter`
  （已由 `app/core/discover.py` 自动挂载，重复即双挂载）；非 `controller.py` 路由才走 `add_router`。
- 模型一律显式声明：`ctx.add_models(*MODEL_PATHS)`，只 import 单个模型会破坏映射器注册表。
- 槽位提供方在 `start()` 里 `provide(...)`；消费方判空降级并记日志，禁止静默丢弃。
- 新菜单必须在末尾追加（order 最大+1），不得插入已有菜单之间。
- 插件自带迁移时，必须把 `%(here)s/app/plugin/module_xxx/migrations` 加进 `alembic.ini`
  的 `version_locations`（`alembic heads`/`history` 不执行 `env.py`，否则静默漏报）。

完整自检清单见 `app/core/plugin/README.md`。

## Known Pitfalls

- **FastApiAdmin 插件开发**参考 `fastapiadmin-plugin-engineering` skill
- 代码生成器生成的 CRUD 需要手动调整响应字段和权限配置
- **`fastapi-limiter` 已升至 `0.2.0`**：`__init__` 改用 `pyrate-limiter` 可插拔桶后端，
  但 `__call__` 仍遍历 `app.routes` 读 `route.path`（FastAPI ≥ 0.141 下 `_IncludedRouter` 无此属性）。
  项目在 `app/core/http_limit.py` 覆盖 `__call__`（改用 `request.scope["endpoint"]`），
  并提供 `build_limiter()` 工厂根据 Redis 可用性自动选桶（RedisBucket / InMemoryBucket）。
  统一从 `app.core.http_limit` 导入 `RateLimiter`，不要直接从 `fastapi_limiter.depends` 导入。

## Reference Docs

- 插件框架内核与迁移自检清单：`app/core/plugin/README.md`
- AI 模块说明：`docs/module_ai-插件说明.md`
- 模块 README 规范模板：`app/plugin/TEMPLATE_README.md`
- 全局统一规范：[AGENTS.md](../AGENTS.md)
