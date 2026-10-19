"""phase53_trade_updated_at

فاز ۵۳.۱ — یکپارچگی داده: ستون `trades.updated_at`.

ستون `updated_at` به جدول معاملات اضافه می‌شود تا گارد «تحلیل کهنه» بتواند
فراتر از **تعداد** معاملات، **آخرین ویرایش** را هم بسنجد. اگر سود/حدضرر/زمان
یک معامله ویرایش شود ولی تعداد ثابت بماند، تحلیل قبلی دیگر معتبر نیست.

ایمن است:
- `nullable=True` ⇒ رکوردهای موجود مقدار NULL می‌گیرند (بدون خطا).
- `upgrade()`/`downgrade()` **idempotent** هستند (الگوی فاز ۳۹/۴۵/۵۳).

Revision ID: f53a1b2c3d4e
Revises: d6e4f1c9a203
Create Date: 2026-10-02 22:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "f53a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "d6e4f1c9a203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "trades"
_COLUMN = "updated_at"


def _existing_columns(table: str) -> set:
    """نام ستون‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    """افزودن ستون `trades.updated_at` (در صورت نبود)."""
    if _COLUMN not in _existing_columns(_TABLE):
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """حذف ستون `trades.updated_at` (در صورت وجود)."""
    if _COLUMN in _existing_columns(_TABLE):
        op.drop_column(_TABLE, _COLUMN)
