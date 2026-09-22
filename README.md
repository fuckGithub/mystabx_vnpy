# mystabx_vnpy

`main` 正在按开源项目风格重构，当前仅为脚手架起点。

## 完整实现（归档）

截至分支创建当日的完整产品代码保留在 **`vnpy`** 分支，未做历史改写。

查看或运行旧版：

```bash
git fetch origin
git checkout vnpy
```

远程：

- Gitee `origin`：`vnpy` / `main`
- GitHub `github`：若网络可达，同步同名分支

## 本分支保留

- `LICENSE`
- `.gitignore`
- 最小 `package.json` / `pyproject.toml`（占位，待重构填充）
- 本地 `.cursor/rules`（若存在；通常被 gitignore）

请勿将 `.env` / `.env.ecs` 等密钥提交入库。
