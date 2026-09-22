"""initial placeholder (bridge missing parent)

Revision ID: 1add412124be
Revises:
Create Date: 2026-07-21 13:19:59.000000

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1add412124be"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Placeholder — parent of 34a1c8187ef6
    pass


def downgrade() -> None:
    pass
