"""Use USDT as the application's dollar-denominated unit.

Revision ID: 5c9a4d8f1e20
Revises: c47e2f3a4b5c
Create Date: 2026-10-02

Amounts are preserved. This migration relabels the stored currency only; it does
not perform currency conversion.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "5c9a4d8f1e20"
down_revision: Union[str, Sequence[str], None] = "c47e2f3a4b5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CURRENCY_COLUMNS = (
    ("accounts", "currency"),
    ("transactions", "currency"),
    ("personal_trading_accounts", "currency"),
    ("prop_accounts", "currency"),
    ("prop_withdrawals", "currency"),
    ("prop_costs", "currency"),
    ("user_settings", "currency"),
)


def _existing_columns(table: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _currency_enum_labels() -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return set()
    for item in inspect(bind).get_enums():
        if item["name"] == "currency":
            return set(item["labels"])
    return set()


def _rename_postgres_currency(old: str, new: str) -> bool:
    """Rename the shared PostgreSQL enum label when that is the stored schema."""
    labels = _currency_enum_labels()
    if old not in labels or new in labels:
        return False
    op.execute(f'ALTER TYPE currency RENAME VALUE \'{old}\' TO \'{new}\'')
    return True


def _rewrite_currency_values(old: str, new: str) -> None:
    bind = op.get_bind()
    for table, column in _CURRENCY_COLUMNS:
        if column in _existing_columns(table):
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET {column} = :new "
                    f"WHERE UPPER(CAST({column} AS TEXT)) = :old"
                ),
                {"old": old, "new": new},
            )


def upgrade() -> None:
    bind = op.get_bind()
    enum_renamed = bind.dialect.name == "postgresql" and _rename_postgres_currency("USD", "USDT")
    if not enum_renamed:
        _rewrite_currency_values("USD", "USDT")
    if "currency" in _existing_columns("user_settings"):
        bind.execute(
            sa.text(
                "UPDATE user_settings SET currency = 'USDT' "
                "WHERE UPPER(currency) NOT IN ('IRR', 'USDT')"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    enum_renamed = bind.dialect.name == "postgresql" and _rename_postgres_currency("USDT", "USD")
    if not enum_renamed:
        _rewrite_currency_values("USDT", "USD")
    if "currency" in _existing_columns("user_settings"):
        bind.execute(
            sa.text(
                "UPDATE user_settings SET currency = 'USD' "
                "WHERE UPPER(currency) = 'USDT'"
            )
        )
