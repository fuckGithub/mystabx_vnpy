# Docker AGENTS.md

> 📖 **入口规范**：[AGENTS.md](../AGENTS.md)

## Overview

Docker Compose 部署配置，管理所有服务的容器化运行。

## Project Structure

```
docker/
├── docker-compose.yaml                # 方式 A：全套编排（MySQL + Redis + Backend + Nginx）
├── docker-compose.dev.yaml            # 方式 A 开发档：源码挂载热更新（叠加使用）
├── docker-compose.backend.yaml        # 方式 B：只跑后端镜像（服务器已有依赖）
├── docker-compose.local-deps.yaml     # 方式 B 可选：叠加本机 mysql + redis
├── .env.example                       # compose 变量模板（密码、端口、镜像 tag），使用者 cp 成 .env
├── backend/Dockerfile                 # 后端镜像（源码 COPY 进镜像，监听 6100）
├── nginx/                             # Nginx 反向代理
│   ├── nginx.conf                     # 主配置
│   └── ssl/                           # SSL 证书（certbot 自动管理）
├── mysql/  redis/                     # 方式 A 的数据目录
└── dist/                              # image:export 产物（已 gitignore）
```

## Services（方式 A 全套）

| 服务    | 镜像                  | 端口    | 说明                       |
| ------- | --------------------- | ------- | -------------------------- |
| MySQL   | mysql:8.0             | 3306    | 业务数据库                 |
| Redis   | redis:7-alpine        | 6379    | 缓存/会话                  |
| Backend | fastapiadmin-backend  | 6100    | FastAPI 应用（容器内 6100）|
| Nginx   | nginx:1.25-alpine     | 80/443  | 反向代理 + 静态资源        |

方式 B 只有 Backend 一个服务，见 `docker-compose.backend.yaml`。

## Production

- **服务器**：47.100.136.197（阿里云 ECS）
- **域名**：service.xxcdjl.xyz
- **部署路径**：`/path/to/docker`
- **一键部署**：根目录 `bash deploy.sh`

## SSL Certificate

- Let's Encrypt 证书（exp 2026-08-26）
- 续签 crontab：每周日 3 点
- 使用 Docker 内 certbot 而非宿主机安装

## Known Pitfalls

- Nginx http2 语法已修复
- 验证码接口在 `CAPTCHA_ENABLE=false` 时必须返回 HTTP 200 而非 500（跨域问题）
  （`CaptchaService.get_captcha_service` 在关闭时返回 `enable: false`，无需再进容器改代码）
- **端口口径**：容器内统一 6100（`SERVER_PORT`），改端口必须同步 `Dockerfile` 的
  `EXPOSE`、编排的 `SERVER_PORT`、`nginx.conf` 的 `proxy_pass`
  （`backend/tests/test_docker_deploy_config.py` 已锁住）。
- **配置注入用 `env_file`，不要改成 volumes 挂载单文件**：文件缺失时 docker 会把缺失的
  源路径创建成目录，配置静默丢失；`env_file` 则直接报错退出。
- **`docker-compose.backend.yaml` 里不能写 `depends_on`**：base 文件引用未定义的 service
  时，不带 `docker-compose.local-deps.yaml` 会让整份 compose 项目解析失败。
- 本机若无 docker CLI，可用 `docker-compose config`（离线解析）与 `podman`（缓存镜像）做
  部分验证；`docker.io` 在本机不可达，镜像源只有 `docker.m.daocloud.io` 可达。

## Reference

- 全局统一规范：[AGENTS.md](../AGENTS.md)
