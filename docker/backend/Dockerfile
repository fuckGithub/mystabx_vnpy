# ============================================
# FastapiAdmin 后端镜像（多阶段构建）
# ============================================
# 构建阶段：安装依赖（利用层缓存，业务代码变化不重装）
# 运行阶段：只含运行时依赖 + 源码，体积更小、更安全
# ============================================

# ---- 构建阶段 ----
FROM python:3.14-slim AS builder

WORKDIR /build

# 依赖清单先拷贝：改业务代码时这一层仍命中缓存
COPY ./backend/requirements.txt .

# 安装依赖到隔离前缀，运行阶段只拷贝产物
RUN pip install --no-cache-dir --prefix=/install \
    -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ---- 运行阶段 ----
FROM python:3.14-slim

LABEL maintainer="19979929623@163.com"

# 时区 + 非缓冲输出（容器日志实时可见）
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/home

# 从构建阶段拷贝已安装的依赖（不含 pip/gcc/构建缓存）
COPY --from=builder /install /usr/local

WORKDIR /home

# 安装 healthcheck 需要的 curl（比 python -c urllib 轻量）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    # 创建非 root 用户（uid 1000，容器安全最佳实践）
    && groupadd -r app && useradd -r -g app -u 1000 app \
    && chown -R app:app /home

USER app

# 源码进镜像（COPY --chown 确保 app 用户有权限）
COPY --chown=app:app ./backend/ ./

EXPOSE 6100

CMD ["python", "main.py", "run", "--env=prod"]
