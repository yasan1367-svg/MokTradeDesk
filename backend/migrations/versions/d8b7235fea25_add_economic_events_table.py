"""add_economic_events_table

فاز NEWS — ایجاد جدول economic_events برای ذخیرهٔ رویدادهای اقتصادی
تقویم Forex Factory (USD/High).

Revision ID: d8b7235fea25
Revises: e4f5a6b7c8d9
Create Date: 2026-10-07 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "d8b7235fea25"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "economic_events"


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if _TABLE in _existing_tables():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("impact", sa.String(length=8), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast", sa.String(length=64), nullable=True),
        sa.Column("previous", sa.String(length=64), nullable=True),
        sa.Column("fetched_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_economic_events_currency_impact_time",
        _TABLE,
        ["currency", "impact", "event_time"],
        unique=False,
    )
    op.create_index(op.f("ix_economic_events_fetched_date"), _TABLE, ["fetched_date"], unique=False)
    op.create_index(op.f("ix_economic_events_id"), _TABLE, ["id"], unique=False)


def downgrade() -> None:
    if _TABLE not in _existing_tables():
        return
    op.drop_index(op.f("ix_economic_events_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_economic_events_fetched_date"), table_name=_TABLE)
    op.drop_index("ix_economic_events_currency_impact_time", table_name=_TABLE)
    op.drop_table(_TABLE)