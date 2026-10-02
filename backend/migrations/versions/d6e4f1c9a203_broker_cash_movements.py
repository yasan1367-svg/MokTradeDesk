"""Track cash movements between personal broker accounts and financial accounts.

Revision ID: d6e4f1c9a203
Revises: 5c9a4d8f1e20
Create Date: 2026-10-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6e4f1c9a203"
down_revision: Union[str, Sequence[str], None] = "5c9a4d8f1e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_cash_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "personal_trading_account_id",
            sa.Integer(),
            sa.ForeignKey("personal_trading_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "financial_account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column(
            "currency",
            sa.Enum("IRR", "USDT", name="currency", create_type=False),
            nullable=False,
        ),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_broker_cash_movements_id", "broker_cash_movements", ["id"])
    op.create_index(
        "ix_broker_cash_movements_personal_trading_account_id",
        "broker_cash_movements",
        ["personal_trading_account_id"],
    )
    op.create_index(
        "ix_broker_cash_movements_financial_account_id",
        "broker_cash_movements",
        ["financial_account_id"],
    )
    op.create_index(
        "ix_broker_cash_movements_transaction_id",
        "broker_cash_movements",
        ["transaction_id"],
    )
    op.create_index("ix_broker_cash_movements_direction", "broker_cash_movements", ["direction"])
    op.create_index("ix_broker_cash_movements_date", "broker_cash_movements", ["date"])


def downgrade() -> None:
    op.drop_index("ix_broker_cash_movements_date", table_name="broker_cash_movements")
    op.drop_index("ix_broker_cash_movements_direction", table_name="broker_cash_movements")
    op.drop_index("ix_broker_cash_movements_transaction_id", table_name="broker_cash_movements")
    op.drop_index("ix_broker_cash_movements_financial_account_id", table_name="broker_cash_movements")
    op.drop_index("ix_broker_cash_movements_personal_trading_account_id", table_name="broker_cash_movements")
    op.drop_index("ix_broker_cash_movements_id", table_name="broker_cash_movements")
    op.drop_table("broker_cash_movements")
