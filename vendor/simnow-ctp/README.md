# SimNow 官方 CTP 组件（上期技术）

本目录对接 [SimNow](https://www.simnow.com.cn/static/apiDownload.action) 提供的 **Mac CTP API v6.7.13**（测评版与生产版合并包，通过 `CreateFtdcTraderApi` / `CreateFtdcMdApi` 的 `bIsProductionMode` 选择；本项目固定走**生产**以连接 SimNow 看穿式前置）。

CTP API 版权归上海期货信息技术有限公司，**不是** vn.py 的一部分，也不得当作本仓库 MIT/包装层许可覆盖的内容。二进制 framework **不要提交进 git**。

## 目录

```text
vendor/simnow-ctp/
  README.md
  config/                 # 公开前置（无账号密码）
  docs/                   # 官方 Mac API 说明摘录
  macos/                  # 本机解压后的 *.framework（gitignore）
```

默认从本机已下载的组件复制：

- `/Users/x/Documents/Stabx/simnow-ctp/production/api/macos/`
- 或环境变量 `STABX_SIMNOW_CTP` 指向含 `thostmduserapi_se.framework` 的目录

然后执行：

```bash
./scripts/install_macos.sh
```

脚本会把 6.7.13 头文件与 framework 覆盖进 `.deps/vnpy_ctp`，按生产模式编译 `vnpy_ctp`，再装进 `.venv`。
