# SSL 证书目录

Let's Encrypt 证书文件存储在此目录下，通过 Docker bind mount 挂载到 nginx 和 certbot 容器。

```
ssl/
├── www/          # ACME 验证目录（webroot 模式）
├── live/         # 当前生效的证书（符号链接）
├── archive/      # 证书归档
└── renewal/      # 续签配置
```

**签发**: `bash deploy.sh cert:init`
**续签**: `bash deploy.sh cert:renew`
**自动续签 crontab**: `0 3 * * 0 deploy.sh cert:renew`

> ⚠ `live/`、`archive/`、`renewal/` 由 certbot 自动生成，不提交到 Git。
