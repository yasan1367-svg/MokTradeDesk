"""phase36_indexes

فاز ۳۶ — Performance & Query Optimization:
- ایندکس‌های `trades`: prop_stage_id, personal_trading_account_id, is_deleted, close_time
- ایندکس‌های `transactions`: account_id, date, type

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-29 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


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


def upgrade() -> None:
    for col in _TRADES_INDEXES:
        op.create_index(op.f(f"ix_trades_{col}"), "trades", [col], unique=False)
    for col in _TRANSACTIONS_INDEXES:
        op.create_index(
            op.f(f"ix_transactions_{col}"), "transactions", [col], unique=False
        )


def downgrade() -> None:
    for col in _TRANSACTIONS_INDEXES:
        op.drop_index(op.f(f"ix_transactions_{col}"), table_name="transactions")
    for col in _TRADES_INDEXES:
        op.drop_index(op.f(f"ix_trades_{col}"), table_name="trades")
