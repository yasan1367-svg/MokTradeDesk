"""phase45_accounts_is_archived

فاز ۴۵.۳ — یکپارچگی دفتر کل: حذف نرم حساب مالی.

ستون `accounts.is_archived` اضافه می‌شود تا `DELETE /finance/accounts/{id}` به‌جای
حذف سخت (که با `cascade=all,delete-orphan` تراکنش‌های طرف مقابلِ انتقال‌ها را پاک
می‌کرد)، فقط حساب را آرشیو کند.

ایمن است:
- `nullable=False` با `server_default="0"` ⇒ رکوردهای موجود `False` می‌شوند.
- `upgrade()`/`downgrade()` **idempotent** هستند (الگوی فاز ۳۹/۴۵) ⇒ اجرای دوباره بی‌اثر.
- ایندکس `ix_accounts_is_archived` هم مطابق مدل ساخته می‌شود.

Revision ID: a45c0de1f2a3
Revises: f39a1b2c3d4e
Create Date: 2026-09-30 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a45c0de1f2a3"
down_revision: Union[str, Sequence[str], None] = "f39a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "accounts"
_COLUMN = "is_archived"
_INDEX = "ix_accounts_is_archived"


def _existing_columns(table: str) -> set:
    """نام ستون‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def _existing_indexes(table: str) -> set:
    """نام ایندکس‌های موجود روی جدول."""
    return {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    """افزودن ستون `accounts.is_archived` + ایندکس (در صورت نبود)."""
    if _COLUMN not in _existing_columns(_TABLE):
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.Boolean(), nullable=False, server_default="0"),
        )
    if _INDEX not in _existing_indexes(_TABLE):
        op.create_index(_INDEX, _TABLE, [_COLUMN])


def downgrade() -> None:
    """حذف ایندکس و ستون (در صورت وجود)."""
    if _INDEX in _existing_indexes(_TABLE):
        op.drop_index(_INDEX, table_name=_TABLE)
    if _COLUMN in _existing_columns(_TABLE):
        op.drop_column(_TABLE, _COLUMN)
