"""add is_deleted to trades — Phase 25

فاز ۲۵ — حذف نرم (Soft Delete) معاملات:

- افزودن ستون `is_deleted` (Boolean, NOT NULL, default=0) به جدول `trades`
- افزودن ایندکس `ix_trades_is_deleted` برای فیلتر سریع در `get_trades`

رفتار:
- تمام رکوردهای موجود مقدار 0 (حذف‌نشده) می‌گیرند.
- `server_default="0"` تا SQLite رکوردهای موجود را بدون خطا پر کند.

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-09-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_deleted column + index to trades."""
    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )
    op.create_index("ix_trades_is_deleted", "trades", ["is_deleted"], unique=False)


def downgrade() -> None:
    """Remove is_deleted column + index from trades."""
    op.drop_index("ix_trades_is_deleted", table_name="trades")
    with op.batch_alter_table("trades") as batch_op:
        batch_op.drop_column("is_deleted")
