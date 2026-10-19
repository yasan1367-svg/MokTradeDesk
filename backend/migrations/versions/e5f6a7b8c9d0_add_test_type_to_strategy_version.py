"""add test_type to strategy_version — Phase 24

Revision ID: e5f6a7b8c9d0
Revises: a3f7c21b9d84
Create Date: 2026-09-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "a3f7c21b9d84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add test_type column to strategy_versions."""
    op.add_column(
        "strategy_versions",
        sa.Column("test_type", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove test_type column from strategy_versions."""
    op.drop_column("strategy_versions", "test_type")
