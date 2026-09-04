# Stabx Web 交易台

用户界面是 **Vue 网页**。默认入口不是桌面 Qt / `main.py`。

## 一键启动（部署默认）

在仓库根目录：

```bash
./start.sh
```

会构建前端，再用 **一个 uvicorn 进程** 同时提供 FastAPI（REST + WebSocket）和 `dist/` 里的 SPA。适合 Linux / macOS 服务器，不需要两个终端。

本机热更新（可选）：

```bash
./start.sh --dev
```

不要让 agent 代为启动服务；也不要启动 Qt。

## 环境变量

可复制 `.env.example` 为 `.env`（已 gitignore）。常用项：

| 变量 | 默认 | 说明 |
|---|---|---|
| `STABX_HOST` | `0.0.0.0` | 监听地址 |
| `STABX_PORT` | `8000` | 监听端口 |
| `STABX_ADMIN_USERNAME` | `admin` | 首次引导管理员名 |
| `STABX_ADMIN_PASSWORD` | `admin123` | 首次引导管理员密码 |
| `STABX_JWT_SECRET` | 自动生成 | JWT 密钥；缺省写入 `.vntrader/web_keys.json` |

不要把真实 SimNow 密码提交进仓库。账户密钥走 Web 后台配置或本机 `.vntrader`，不要写进脚本。

启动后浏览器打开 `http://<主机>:<端口>/`。不要对 vnpy 引擎使用 `uvicorn --workers`（`MainEngine` 在进程内）。

规划文档见 [docs/README.md](docs/README.md)。桌面 `main.py` 仅作遗留代码，不是产品入口。
