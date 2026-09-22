"""add username mobile login_platform to sys_log

Revision ID: 13efd604ba30
Revises: 34a1c8187ef6
Create Date: 2026-07-23 12:50:55.759672

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '13efd604ba30'
down_revision: str | None = '34a1c8187ef6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### 添加 sys_log 表的冗余字段 ###
    op.add_column("sys_log", sa.Column("username", sa.String(64), nullable=True, comment="操作人账号（冗余）"))
    op.add_column("sys_log", sa.Column("mobile", sa.String(11), nullable=True, comment="操作人手机号（冗余）"))
    op.add_column("sys_log", sa.Column("login_platform", sa.String(32), nullable=True, comment="登录平台(PC/FLUTTER/UNIAPP)"))


def downgrade() -> None:
    op.drop_column("sys_log", "login_platform")
    op.drop_column("sys_log", "mobile")
    op.drop_column("sys_log", "username")
