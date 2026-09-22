"""Docker 部署配置一致性守卫（无需 Docker 即可运行）。

背景：部署链路上的端口口径曾三处不一致——compose / nginx / 应用监听端口漂移会导致 502。

真值以 ``docker/README.md`` 与根 ``AGENTS.md`` 默认端口表为准：容器内统一 **18080**
（对齐 mystabx ``STABX_PORT``；原上游 fastapiadmin 为 6100）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKER_DIR = REPO_ROOT / "docker"
CONTAINER_PORT = "18080"
LEGACY_PORT = "6100"
IMAGE_REF = "fastapiadmin-backend:${IMAGE_TAG:-3.1.0}"

COMPOSE_FULL = DOCKER_DIR / "docker-compose.yaml"
COMPOSE_DEV = DOCKER_DIR / "docker-compose.dev.yaml"
COMPOSE_BACKEND = DOCKER_DIR / "docker-compose.backend.yaml"
COMPOSE_LOCAL_DEPS = DOCKER_DIR / "docker-compose.local-deps.yaml"
NGINX_CONF = DOCKER_DIR / "nginx" / "nginx.conf"
DOCKERFILE = DOCKER_DIR / "backend" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
DEPLOY_SH = REPO_ROOT / "deploy.sh"

# 本元组随任务增量扩展：后续任务把它新创建的文件加进来，
# 使 test_deployment_file_exists 与 test_no_legacy_port_in_deployment_chain 覆盖到位。
DEPLOYMENT_FILES = (
    COMPOSE_FULL,
    COMPOSE_DEV,
    COMPOSE_BACKEND,
    COMPOSE_LOCAL_DEPS,
    NGINX_CONF,
    DOCKERFILE,
    DOCKERIGNORE,
    DEPLOY_SH,
)


def _text(path: Path) -> str:
    """读取配置文件文本。

    参数:
    - path (Path): 文件路径。

    返回:
    - str: 文件内容（UTF-8）。
    """
    return path.read_text(encoding="utf-8")


def _yaml_only(text: str) -> str:
    """去掉注释行，只留真正生效的 YAML 内容。

    参数:
    - text (str): 文件全文。

    返回:
    - str: 去掉以 ``#`` 开头的行之后的内容。
    """
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


@pytest.mark.parametrize("path", DEPLOYMENT_FILES, ids=[p.name for p in DEPLOYMENT_FILES])
def test_deployment_file_exists(path: Path) -> None:
    """部署链路涉及的文件必须存在（缺文件时后续断言会给出误导性失败）。"""
    assert path.is_file(), f"缺少部署文件: {path.relative_to(REPO_ROOT)}"


def test_no_legacy_port_in_deployment_chain() -> None:
    """部署链路里不得再出现旧端口 8001（改端口时的漏改检测）。"""
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{lineno}"
        for path in DEPLOYMENT_FILES
        for lineno, line in enumerate(_text(path).splitlines(), start=1)
        if LEGACY_PORT in line
    ]
    assert offenders == [], f"以下位置仍引用旧端口 {LEGACY_PORT}: {offenders}"


def test_dockerfile_ships_source_and_pins_port() -> None:
    """镜像必须自带源码，且依赖层与源码层分离。"""
    text = _text(DOCKERFILE)
    assert f"EXPOSE {CONTAINER_PORT}" in text
    # 源码 COPY（多阶段构建用 --chown=app:app 传给非 root 用户）
    assert "COPY" in text and "./backend/" in text and "./" in text.split("./backend/")[-1].split("\n")[0]
    assert text.index("COPY ./backend/requirements.txt .") < text.index("COPY --from=builder /install /usr/local")


def test_full_compose_pins_container_port_and_env_file() -> None:
    """方式 A：端口、镜像名、env_file 三件套对齐，且源码挂载不得出现在主文件里。"""
    text = _text(COMPOSE_FULL)
    assert f'SERVER_PORT: "{CONTAINER_PORT}"' in text
    assert f"${{BACKEND_PORT:-{CONTAINER_PORT}}}:{CONTAINER_PORT}" in text
    assert f"localhost:{CONTAINER_PORT}/common/health" in text
    assert f"image: {IMAGE_REF}" in text
    assert "- ../backend/env/.env.prod" in text
    assert "../backend:/home" not in _yaml_only(text)
    # 构建上下文必须是仓库根：否则 Docker 去找不存在的 backend/.dockerignore，
    # 根 .dockerignore 的全部保护（.env / *.db）静默失效且无任何报错
    assert "context: ../" in text


def test_nginx_proxies_to_container_port() -> None:
    """nginx 必须转发到容器实际监听的端口（通过 upstream 声明）。"""
    text = _text(NGINX_CONF)
    assert f"server backend:{CONTAINER_PORT}" in text  # upstream server 声明
    assert "proxy_pass http://backend_upstream;" in text  # 通过 upstream 转发


def test_dev_override_only_adds_source_mount() -> None:
    """dev 覆盖文件只做源码挂载，其余配置沿用主文件。

    断言「去掉注释与空行后恰好是这 4 行」，而不是逐个 ``not in``：后者只挡字面量，
    往 dev 文件里加 ``ports:`` / ``env_file:`` / ``healthcheck:`` / ``environment:``
    都能在绿态下违反本文件声称的不变量。
    """
    lines = [
        line
        for line in _text(COMPOSE_DEV).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert lines == ["services:", "  backend:", "    volumes:", "      - ../backend:/home"]


def test_backend_only_compose_is_image_driven_and_loopback_only() -> None:
    """方式 B：不构建、只回环暴露、且不得依赖未定义服务。"""
    content = _yaml_only(_text(COMPOSE_BACKEND))
    assert "build:" not in content
    assert f"image: {IMAGE_REF}" in content
    assert "- ./env.prod" in content
    assert "depends_on" not in content
    # 「只绑回环」是排他性约束：存在性断言挡不住再新增一条 0.0.0.0 绑定（静默暴露 API）。
    # 带冒号的列表项即绑定/映射项；方式 B 只允许这一条。
    bindings = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("- ") and ":" in line
    ]
    assert bindings == [f'- "127.0.0.1:${{BACKEND_PORT:-{CONTAINER_PORT}}}:{CONTAINER_PORT}"']


def test_local_deps_override_declares_dependency() -> None:
    """local-deps 覆盖文件补齐 mysql/redis 与启动顺序。"""
    content = _yaml_only(_text(COMPOSE_LOCAL_DEPS))
    assert "depends_on" in content
    assert "condition: service_healthy" in content
    for service in ("mysql:", "redis:"):
        assert f"\n  {service}" in content


def test_dockerignore_blocks_dev_env_and_keeps_examples() -> None:
    """开发态密钥必须被排除，示例文件必须保留（供容器内查阅）。"""
    lines = [ln.strip() for ln in _text(DOCKERIGNORE).splitlines() if ln.strip()]
    assert "backend/env/.env" in lines
    assert "backend/env/.env.*" in lines
    assert lines.index("!backend/env/.env.prod.example") > lines.index("backend/env/.env.*")
    assert "backend/requirements.txt" not in lines


def test_deploy_script_references_existing_compose_files() -> None:
    """deploy.sh 里出现的编排文件名必须真实存在于 docker/。"""
    names = set(re.findall(r"docker-compose[\w.-]*\.ya?ml", _text(DEPLOY_SH)))
    assert names, "deploy.sh 未引用任何编排文件"
    missing = sorted(n for n in names if not (DOCKER_DIR / n).is_file())
    assert missing == [], f"deploy.sh 引用了不存在的编排文件: {missing}"


def test_deploy_script_exposes_both_modes() -> None:
    """deploy.sh 必须暴露双模式入口。"""
    text = _text(DEPLOY_SH)
    for command in ("image:export", "image:load", "db:migrate"):
        assert f"{command})" in text, f"deploy.sh 缺少子命令: {command}"
