"""phase46_server_utc_offset

فاز ۴۶.۱ — افزودن `server_utc_offset_minutes` (پیش‌فرض 0) به سه جدول:
`brokers`، `personal_trading_accounts`، `prop_accounts`.

هدف: ثبت اختلاف ساعت سرور بروکر/پراپ با UTC تا ورود زمان‌ها درست تفسیر شود.
(تصمیم D3 کاربر: ساعت MT4 = GMT+0 ⇒ فعلاً مقدار پیش‌فرض 0 کافی است.)

ایمن است:
- `nullable=False` با `server_default="0"` ⇒ رکوردهای موجود 0 می‌شوند.
- `upgrade()`/`downgrade()` **idempotent** هستند.

Revision ID: b46d1e2f3a4b
Revises: a45c0de1f2a3
Create Date: 2026-09-30 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b46d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "a45c0de1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMN = "server_utc_offset_minutes"
_TABLES = ("brokers", "personal_trading_accounts", "prop_accounts")


def _existing_columns(table: str) -> set:
    """نام ستون‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    """افزودن ستون `server_utc_offset_minutes` به سه جدول (در صورت نبود)."""
    for table in _TABLES:
        if _COLUMN not in _existing_columns(table):
            op.add_column(
                table,
                sa.Column(_COLUMN, sa.Integer(), nullable=False, server_default="0"),
            )


def downgrade() -> None:
    """حذف ستون از سه جدول (در صورت وجود)."""
    for table in _TABLES:
        if _COLUMN in _existing_columns(table):
            op.drop_column(table, _COLUMN)
