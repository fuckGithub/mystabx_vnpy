import os
from typing import Annotated

import typer
import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.common.enums import EnvironmentEnum

fastapiadmin_cli = typer.Typer()
alembic_cfg = Config("alembic.ini")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例并完成日志、中间件、路由与静态资源注册。

    返回:
    - FastAPI: 已配置生命周期的应用对象。
    """
    from app.config.setting import settings
    from app.scripts.init_app import (
        lifespan,
        register_exceptions,
        register_files,
        register_middlewares,
        register_routers,
        reset_api_docs,
    )

    # 创建FastAPI应用
    app = FastAPI(**settings.FASTAPI_CONFIG, lifespan=lifespan)

    # 预置 Redis 占位（None）。REDIS_ENABLE=False 时 setting.EVENT_LIST 不会注册
    # app.core.database.redis_connect，app.state.redis 也就永不被赋值；若不预置，
    # lifespan 里对 app.state.redis 的访问会抛 AttributeError。
    app.state.redis = None

    from app.core.logger import setup_logging

    # 初始化日志
    setup_logging()
    # 注册各种组件
    register_exceptions(app)
    # 注册中间件
    register_middlewares(app)
    # 注册路由
    register_routers(app)
    # 注册静态文件
    register_files(app)
    # 重设API文档
    reset_api_docs(app)

    return app


# typer.Option是非必填；typer.Argument是必填
@fastapiadmin_cli.command(
    name="run",
    help="启动 FastapiAdmin 服务, 运行 python main.py run --env=dev 不加参数默认 dev 环境",
)
def run(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    按指定环境加载配置并启动 Uvicorn（开发环境开启 reload）。

    参数:
    - env (EnvironmentEnum): 运行环境，对应 `--env`。

    返回:
    - None
    """

    try:
        # 设置环境变量
        os.environ["ENVIRONMENT"] = env.value
        typer.echo("项目启动中...")

        # 清除配置缓存，确保重新加载配置
        from app.config.setting import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        from app.core.logger import setup_logging

        setup_logging()

        # 显示启动横幅
        from app.utils.banner import worship

        worship(env.value)

        # 启动uvicorn服务
        uvicorn.run(
            app="main:create_app",
            host=settings.SERVER_HOST,
            port=settings.SERVER_PORT,
            reload=env.value == EnvironmentEnum.DEV.value,
            factory=True,
            log_config=None,
        )
    finally:
        from app.core.logger import cleanup_logging

        cleanup_logging()


@fastapiadmin_cli.command(
    name="revision",
    help="生成新的 Alembic 迁移脚本, 运行 python main.py revision --env=dev",
)
def revision(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    使用 Alembic 自动生成迁移脚本（autogenerate）。

    参数:
    - env (EnvironmentEnum): 运行环境，用于加载对应数据库模型元数据。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import get_settings

    get_settings.cache_clear()
    command.revision(alembic_cfg, autogenerate=True, message="迁移脚本")
    typer.echo("迁移脚本已生成")


@fastapiadmin_cli.command(
    name="upgrade",
    help="应用最新的 Alembic 迁移, 运行 python main.py upgrade --env=dev",
)
def upgrade(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    将数据库升级到 Alembic 最新版本（head）。

    参数:
    - env (EnvironmentEnum): 运行环境。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import get_settings

    get_settings.cache_clear()
    command.upgrade(alembic_cfg, "head")
    typer.echo("所有迁移已应用。")


@fastapiadmin_cli.command(
    name="reset-passwords",
    help="重置所有用户密码为默认值（用于国密迁移后强制重置）, 运行 python main.py reset-passwords --env=dev --default-pwd=123456",
)
def reset_passwords(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
    default_pwd: Annotated[
        str, typer.Option("--default-pwd", help="默认密码")
    ] = "123456",
) -> None:
    """
    重置所有用户密码为默认值。

    参数:
    - env (EnvironmentEnum): 运行环境。
    - default_pwd (str): 重置后的默认密码。

    返回:
    - None
    """
    import asyncio

    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import get_settings

    get_settings.cache_clear()

    from app.core.database import async_db_session
    from app.plugin.module_system.user.model import UserModel
    from app.utils.sm_crypto_util import PwdUtil

    async def _reset():
        async with async_db_session() as session:
            from sqlalchemy import select, update

            # 查询所有用户
            result = await session.execute(select(UserModel))
            users = result.scalars().all()
            typer.echo(f"找到 {len(users)} 个用户")

            # 生成新密码哈希
            new_hash = PwdUtil.set_password_hash(default_pwd)

            # 逐个更新
            count = 0
            for user in users:
                stmt = (
                    update(UserModel)
                    .where(UserModel.id == user.id)
                    .values(password=new_hash)
                )
                await session.execute(stmt)
                count += 1
                if count % 10 == 0:
                    typer.echo(f"  已重置 {count} 个用户...")

            await session.commit()
            typer.echo(f"✅ 已重置 {count} 个用户的密码为: {default_pwd}")

    asyncio.run(_reset())


if __name__ == "__main__":
    fastapiadmin_cli()
