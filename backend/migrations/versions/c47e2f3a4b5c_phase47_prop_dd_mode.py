"""phase47_prop_dd_mode

فاز ۴۷.۱ — افزودن سه ستون به `prop_stages`:
- `dd_mode`  (static | trailing) — مدل Drawdown (D1 کاربر: Static + Balance-based)
- `dd_basis` (balance | equity)
- `day_boundary_utc_offset` (دقیقه) — مرز روز برای Daily DD (D2 کاربر: 00:00 UTC ⇒ 0)

ایمن است: `nullable=False` با `server_default` ⇒ رکوردهای موجود مقدار پیش‌فرض می‌گیرند.
`upgrade()`/`downgrade()` **idempotent** هستند.

Revision ID: c47e2f3a4b5c
Revises: b46d1e2f3a4b
Create Date: 2026-09-30 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c47e2f3a4b5c"
down_revision: Union[str, Sequence[str], None] = "b46d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "prop_stages"
_COLUMNS = (
    ("dd_mode", sa.String(20), "static"),
    ("dd_basis", sa.String(20), "balance"),
    ("day_boundary_utc_offset", sa.Integer(), "0"),
)


def _existing_columns(table: str) -> set:
    """نام ستون‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    """افزودن ستون‌های DD (در صورت نبود)."""
    for name, type_, default in _COLUMNS:
        if name not in _existing_columns(_TABLE):
            op.add_column(
                _TABLE,
                sa.Column(name, type_, nullable=False, server_default=default),
            )


def downgrade() -> None:
    """حذف ستون‌های DD (در صورت وجود)."""
    for name, _type, _default in _COLUMNS:
        if name in _existing_columns(_TABLE):
            op.drop_column(_TABLE, name)
