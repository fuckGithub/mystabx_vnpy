# 分平台 CTP 搭建（Windows / macOS / Linux）

本文说明本仓库如何按操作系统安装 **vnpy_ctp** 与 **SimNow / 上期技术 CTP** 动态库。产品入口仍是 Web（`python main.py` / `./start.sh`）；本文**不启动**应用。

相关文件：

| 路径 | 作用 |
|---|---|
| [`scripts/install_macos.sh`](../scripts/install_macos.sh) | macOS：源码编译 + SimNow Mac `.framework` |
| [`scripts/install_linux.sh`](../scripts/install_linux.sh) | Linux x86_64：源码编译 + Linux `.so` |
| [`scripts/install_windows.ps1`](../scripts/install_windows.ps1) | Windows：优先 PyPI wheel（自带 `.dll`） |
| [`scripts/load_simnow_ctp.sh`](../scripts/load_simnow_ctp.sh) | 仅 macOS / Linux：覆盖官方二进制并（仅 Darwin）打补丁 |
| [`vendor/simnow-ctp/README.md`](../vendor/simnow-ctp/README.md) | 官方组件目录约定（二进制不进 git） |

**绝对不要**跨平台混用动态库：Mac `.framework` ≠ Linux `.so` ≠ Windows `.dll`。不要把本机 Mac 编译产物拷到 Linux / Windows。

CTP API 版权属上海期货信息技术有限公司；SimNow 下载页：<https://www.simnow.com.cn/static/apiDownload.action>。

---

## 对照总表

| 项 | Windows | macOS | Linux |
|---|---|---|---|
| 安装脚本 | `scripts/install_windows.ps1` | `scripts/install_macos.sh` | `scripts/install_linux.sh` |
| Python 封装 | `vnpy_ctp` **6.7.7.2** | 同左（源码编译） | 同左（源码编译） |
| 柜台动态库 | `.dll`（PyPI wheel 自带穿透式实盘库；可选覆盖 `vendor/simnow-ctp/windows/`） | SimNow 官方 Mac **v6.7.13** `.framework` | Linux `.so`（vnpy_ctp 自带，或覆盖 `vendor/simnow-ctp/linux/`） |
| 推荐安装方式 | `pip install vnpy_ctp`（有 Windows wheel） | 必须本机编译（无可用 Mac wheel 时） | 本机编译 |
| 架构 | x86_64 / AMD64（与 wheel 一致） | Apple Silicon / Intel（跟本机 framework） | **仅 x86_64** |
| Web 启动 | 见下文「Windows 启动」；或 **WSL2** 走 Linux 路径 | `./start.sh` / `python main.py` | `./start.sh` / `python main.py` |
| 断开原生会话 | 可 `gateway.close()` | **禁止** `exit()`/`close()`（会 segfault） | 可 `gateway.close()` |

通道里「柜台环境」固定为「实盘」；SimNow 走生产前置（看穿式）。账号密码只写 Web 通道配置或本机 `.env`，**不要**写进仓库。

---

## macOS

### 前置

- Python ≥ 3.10、本机 `.venv`
- [uv](https://github.com/astral-sh/uv)、Homebrew `ta-lib`（脚本默认读 `/opt/homebrew`）
- Xcode Command Line Tools（编译 C++ 扩展）
- SimNow **Mac** CTP v6.7.13：`thostmduserapi_se.framework` / `thosttraderapi_se.framework`

放置方式（二选一）：

- 解压到 `vendor/simnow-ctp/macos/`
- 或设环境变量 `STABX_SIMNOW_CTP` 指向含上述 framework 的目录  
  （脚本还会尝试本机路径 `/Users/x/Documents/Stabx/simnow-ctp/production/api/macos`）

### 安装命令

```bash
python3 -m venv .venv
./scripts/install_macos.sh
```

脚本会：`uv pip install -e .` → clone `vnpy_ctp` 标签 `6.7.7.2` 到 `.deps/vnpy_ctp` → `load_simnow_ctp.sh` 覆盖 framework/头文件并打 Darwin 补丁（`Create*` 生产模式、`ReqUserLogin` 两参）→ `uv pip install .deps/vnpy_ctp`。**不要**对 `vnpy_ctp` 使用 `pip install -e`。

### 已知限制（务必保留）

SimNow CTP **6.7.13** 在 macOS 上对 `TdApi` / `MdApi` 调用 `exit()` / `close()` 会导致**进程崩溃**。Web 在 Darwin 上「断开」只清本地状态并禁止自动重连，不拆原生会话；真正释放需**重启进程**。Linux / Windows 可正常 `gateway.close()`。实现见 `core/gateways.py`。

---

## Linux（x86_64）

### 前置

Ubuntu / Debian 示例：

```bash
sudo apt-get install -y python3 python3-venv python3-dev build-essential git nodejs npm
```

可选：系统 TA-Lib（`TA_INCLUDE_PATH` / `TA_LIBRARY_PATH`）；脚本会探测常见路径，不假设 Homebrew。

官方 CTP Linux 库**仅支持 x86_64**。可选把 SimNow / 官方 Linux 包中的 `libthostmduserapi_se.so`、`libthosttraderapi_se.so`（或无 `lib` 前缀的同名文件）放到 `vendor/simnow-ctp/linux/`，或设 `STABX_SIMNOW_CTP`。未提供时使用 `vnpy_ctp` 自带 `.so`。

### 安装命令

```bash
python3 -m venv .venv
./scripts/install_linux.sh
```

**不要**运行 `install_macos.sh`，**不要**拷贝 Mac `.framework`。`load_simnow_ctp.sh` 在 Linux 上**不会**打 Darwin 补丁。

启动：

```bash
./start.sh
# 或 python main.py
```

`start.sh` 会把 `vnpy_ctp` 的 `api` 目录加入 `LD_LIBRARY_PATH`，并拒绝「只有 Mac framework、没有 `.so`」的错误安装。

---

## Windows

### 推荐路径 A：WSL2（与 Linux 一致）

在 WSL2（Ubuntu x86_64）里按上一节执行 `install_linux.sh` 与 `./start.sh`。CTP 与本仓库脚本路径与 Linux 服务器相同，联调成本最低。

### 路径 B：原生 Windows（PowerShell）

#### 前置

- Windows 10/11 **x64**
- [Python](https://www.python.org/downloads/) ≥ 3.10（安装时勾选 Add to PATH）
- [Node.js](https://nodejs.org/) + npm（构建 Vue）
- Git（可选；源码编译 `vnpy_ctp` 时需要）
- **Visual Studio Build Tools**（仅当不用 PyPI wheel、改为源码编译时需要 C++ 工作负载）

`vnpy_ctp` 官方说明：接口自带【穿透式实盘环境】的 **dll**；Windows 上通常可直接：

```text
pip install vnpy_ctp
```

有匹配的 wheel 时**不必**本机编译。源码安装才需要 Visual Studio。

#### 安装命令

在仓库根目录 **PowerShell**：

```powershell
python -m venv .venv
.\scripts\install_windows.ps1
```

脚本会：创建/使用 `.venv` → `pip install -e .` → 默认 `pip install vnpy_ctp==6.7.7.2`（PyPI wheel + 自带 `.dll`）。

可选覆盖官方 / SimNow Windows 动态库：将 `thostmduserapi_se.dll`、`thosttraderapi_se.dll` 放到 `vendor/simnow-ctp/windows/`（或设 `STABX_SIMNOW_CTP` 指向该目录），再跑一次脚本；脚本会复制到已安装的 `vnpy_ctp\api\`。

强制源码编译（需 Git + MSVC）：

```powershell
$env:STABX_CTP_FROM_SOURCE = "1"
.\scripts\install_windows.ps1
```

#### Windows 启动（原生）

仓库根目录的 `./start.sh` / `uv run start` 面向 **Linux / macOS**（`core/start.py` 会 `exec` bash）。原生 Windows 请自行：

```powershell
# 前端（若尚无 dist）
npm install
npm run build

# 后端（单进程；不要 uvicorn --workers）
.\.venv\Scripts\python.exe -m uvicorn core.main:app --host 0.0.0.0 --port 8000
```

或在 **Git Bash / WSL** 中使用与 macOS/Linux 相同的 `./start.sh`（须已按对应平台装好 CTP）。

开发热更新可在两终端分别起 Vite（`ui/`）与带 `--reload` 的 uvicorn；参数以本机 `package.json` / 现有 Mac `--dev` 流程为准。

---

## SimNow 联调备忘

- 经纪商 `9999`，产品名称 `simnow_client_test`，授权编码 `0000000000000000`，柜台环境 **实盘**
- 未手动指定前置时按上海时间在交易时段 / 7×24 前置间切换（见 README「业务操作流程」）
- 新账号连 7×24 可能要过若干交易日才可用
- 切勿把 InvestorID / 密码提交进 git

---

## 校验（不启动常驻服务）

各平台在对应 venv 中：

```bash
# macOS / Linux
.venv/bin/python -c "import vnpy_ctp; from vnpy_ctp import CtpGateway; print(vnpy_ctp.__file__)"

# Windows PowerShell
.\.venv\Scripts\python.exe -c "import vnpy_ctp; from vnpy_ctp import CtpGateway; print(vnpy_ctp.__file__)"
```

可选冒烟（不常驻 uvicorn）：`scripts/smoke_imports.py` / `scripts/smoke_web.py`。
