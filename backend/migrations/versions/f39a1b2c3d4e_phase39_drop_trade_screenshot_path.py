"""phase39_drop_trade_screenshot_path

فاز ۳۹.۳ — رفع «Screenshot دوگانه»:
ستون legacy `trades.screenshot_path` حذف می‌شود تا **تنها** جدول `screenshots`
(`models/personal.py::Screenshot` با `entity_type='trade'`) منبع حقیقت اسکرین‌شات باشد.

چرا امن است؟
- ستون `nullable` بود و در کد **هیچ‌گاه** خوانده/نوشته نمی‌شد
  (جستجوی `screenshot_path` در `backend/app/` و `frontend/src/` **صفر** نتیجه)
  ⇒ ستون مرده؛ هیچ داده‌ای که معنادار باشد از دست نمی‌رود.
- `screenshot_path` ایندکس/constraint ندارد ⇒ `ALTER TABLE ... DROP COLUMN`
  روی SQLite (نسخهٔ 3.45.3 ≥ 3.35) مستقیماً کار می‌کند و ایندکس‌های دیگر `trades`
  (`ix_trades_trade_hash`, `ix_trades_is_deleted`, ...) دست‌نخورده می‌مانند.
- `upgrade()`/`downgrade()` **idempotent** هستند (الگوی فاز ۳۸.۵) ⇒ اجرای دوباره
  بی‌اثر است و روی DB خالی و موجود یکسان کار می‌کند.

Revision ID: f39a1b2c3d4e
Revises: c9d0e1f2a3b4
Create Date: 2026-09-29 23:59:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "f39a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "trades"
_COLUMN = "screenshot_path"


def _existing_columns(table: str) -> set:
    """نام ستون‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    """حذف ستون legacy `trades.screenshot_path` (در صورت وجود)."""
    if _COLUMN in _existing_columns(_TABLE):
        op.drop_column(_TABLE, _COLUMN)


def downgrade() -> None:
    """بازگرداندن ستون (nullable — سازگار با دادهٔ موجود)."""
    if _COLUMN not in _existing_columns(_TABLE):
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.String(), nullable=True))
