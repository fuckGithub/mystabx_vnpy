# SimNow 官方 CTP 组件（上期技术）

本目录对接 [SimNow](https://www.simnow.com.cn/static/apiDownload.action) 提供的官方 CTP API。macOS 用 **Mac CTP v6.7.13**（测评/生产合并包，本项目 `Create*` 固定生产模式）。Linux 用官方 **Linux `.so`**，不要拷贝 Mac `.framework`。

CTP API 版权归上海期货信息技术有限公司，**不是** vn.py 的一部分，也不得当作本仓库 MIT/包装层许可覆盖的内容。二进制 **不要提交进 git**。

## 目录

```text
vendor/simnow-ctp/
  README.md
  config/                 # 公开前置（无账号密码）
  docs/                   # 官方 Mac API 说明摘录
  macos/                  # 本机解压后的 *.framework（gitignore）
  linux/                  # 本机解压后的 libthost*.so（gitignore）
```

**macOS**：默认从本机已下载的组件复制 `/Users/x/Documents/Stabx/simnow-ctp/production/api/macos/`，或设 `STABX_SIMNOW_CTP` 指向含 `thostmduserapi_se.framework` 的目录，然后 `./scripts/install_macos.sh`。脚本会覆盖 6.7.13 头文件与 framework，并打 Darwin 补丁。

**Linux**：把 `libthostmduserapi_se.so` / `libthosttraderapi_se.so`（或无 `lib` 前缀的同名文件）放到 `linux/`，或设 `STABX_SIMNOW_CTP` 指向该目录，然后 `./scripts/install_linux.sh`。未提供外部 so 时使用 vnpy_ctp 自带的 Linux 库。**不会**打 Darwin 补丁。
