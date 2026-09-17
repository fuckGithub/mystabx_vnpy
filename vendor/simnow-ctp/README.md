# SimNow 官方 CTP 组件（上期技术）

本目录对接 [SimNow](https://www.simnow.com.cn/static/apiDownload.action) 提供的官方 CTP API。

| 平台 | 动态库形态 | 本目录子路径 |
|---|---|---|
| macOS | `.framework`（本项目用 SimNow Mac **v6.7.13**，测评/生产合并包；`Create*` 固定生产模式） | `macos/` |
| Linux | `.so`（`libthostmduserapi_se.so` / `libthosttraderapi_se.so`） | `linux/` |
| Windows | `.dll`（`thostmduserapi_se.dll` / `thosttraderapi_se.dll`） | `windows/` |

**不要**跨平台混用。CTP API 版权归上海期货信息技术有限公司，**不是** vn.py 的一部分，也不得当作本仓库 MIT/包装层许可覆盖的内容。二进制 **不要提交进 git**。

分平台安装步骤见仓库 [docs/CTP分平台搭建.md](../../docs/CTP分平台搭建.md)。

## 目录

```text
vendor/simnow-ctp/
  README.md
  config/                 # 公开前置（无账号密码）
  docs/                   # 官方 Mac API 说明摘录
  macos/                  # 本机解压后的 *.framework（gitignore）
  linux/                  # 本机解压后的 libthost*.so（gitignore）
  windows/                # 本机解压后的 thost*_se.dll（gitignore）
```

**macOS**：默认从本机已下载的组件复制 `/Users/x/Documents/Stabx/simnow-ctp/production/api/macos/`，或设 `STABX_SIMNOW_CTP` 指向含 `thostmduserapi_se.framework` 的目录，然后 `./scripts/install_macos.sh`。脚本会覆盖 6.7.13 头文件与 framework，并打 Darwin 补丁。

**Linux**：把 `libthostmduserapi_se.so` / `libthosttraderapi_se.so`（或无 `lib` 前缀的同名文件）放到 `linux/`，或设 `STABX_SIMNOW_CTP` 指向该目录，然后 `./scripts/install_linux.sh`。未提供外部 so 时使用 vnpy_ctp 自带的 Linux 库。**不会**打 Darwin 补丁。

**Windows**：优先 `.\scripts\install_windows.ps1`（`pip install vnpy_ctp`，wheel 自带穿透式 dll）。可选把官方 / SimNow Windows dll 放到 `windows/` 或设 `STABX_SIMNOW_CTP`，脚本会覆盖到已安装的 `vnpy_ctp\api\`。不要拷贝 Mac / Linux 库。
