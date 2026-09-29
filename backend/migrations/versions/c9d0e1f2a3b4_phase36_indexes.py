"""phase36_indexes

فاز ۳۶ — Performance & Query Optimization:
- ایندکس‌های `trades`: prop_stage_id, personal_trading_account_id, is_deleted, close_time
- ایندکس‌های `transactions`: account_id, date, type

فاز ۳۸.۵ (Fix Debt):
- ساخت ایندکس‌ها **idempotent** شد. پیش‌تر `ix_trades_is_deleted` هم این‌جا و هم در
  migration فاز ۲۵ (`f1a2b3c4d5e6`) ساخته می‌شد ⇒ روی DB خالی (زنجیرهٔ کامل migrationها)
  خطای `index ix_trades_is_deleted already exists` می‌داد. الان اگر ایندکس از قبل
  وجود داشته باشد، رد می‌شود (روی هر دیالکتی — SQLite/PG).

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-29 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TRADES_INDEXES = [
    "prop_stage_id",
    "personal_trading_account_id",
    "is_deleted",
    "close_time",
]
_TRANSACTIONS_INDEXES = ["account_id", "date", "type"]


def _existing_indexes(table: str) -> set:
    """نام ایندکس‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table)}


def _create_index_if_missing(index_name: str, table: str, column: str) -> None:
    if index_name in _existing_indexes(table):
        return
    op.create_index(op.f(index_name), table, [column], unique=False)


def _drop_index_if_exists(index_name: str, table: str) -> None:
    if index_name not in _existing_indexes(table):
        return
    op.drop_index(op.f(index_name), table_name=table)


def upgrade() -> None:
    for col in _TRADES_INDEXES:
        _create_index_if_missing(f"ix_trades_{col}", "trades", col)
    for col in _TRANSACTIONS_INDEXES:
        _create_index_if_missing(f"ix_transactions_{col}", "transactions", col)


def downgrade() -> None:
    for col in _TRANSACTIONS_INDEXES:
        _drop_index_if_exists(f"ix_transactions_{col}", "transactions")
    for col in _TRADES_INDEXES:
        _drop_index_if_exists(f"ix_trades_{col}", "trades")
