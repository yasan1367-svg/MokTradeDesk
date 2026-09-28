"""phase28_trade_contract

فاز ۲۸ — اعمال قرارداد در سطح DB:
- `trades.version_id` → NOT NULL (برای همهٔ انواع اجباری)
- `trades.test_type`    → NOT NULL
- CheckConstraint `ck_trades_classification` (XOR بین REAL_PERSONAL و REAL_PROP)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-28 12:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CLASSIFICATION_CHECK = (
    "(test_type IN ('BACKTEST','FORWARD') "
    "   AND personal_trading_account_id IS NULL AND prop_stage_id IS NULL) "
    "OR (test_type = 'REAL_PERSONAL' "
    "   AND personal_trading_account_id IS NOT NULL AND prop_stage_id IS NULL) "
    "OR (test_type = 'REAL_PROP' "
    "   AND prop_stage_id IS NOT NULL AND personal_trading_account_id IS NULL)"
)


def upgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.alter_column("version_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("test_type", existing_type=sa.String(), nullable=False)
        batch_op.create_check_constraint("ck_trades_classification", CLASSIFICATION_CHECK)

    op.create_index(op.f("ix_trades_version_id"), "trades", ["version_id"], unique=False)
    op.create_index(op.f("ix_trades_test_type"), "trades", ["test_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_trades_test_type"), table_name="trades")
    op.drop_index(op.f("ix_trades_version_id"), table_name="trades")

    with op.batch_alter_table("trades") as batch_op:
        batch_op.drop_constraint("ck_trades_classification", type_="check")
        batch_op.alter_column("test_type", existing_type=sa.String(), nullable=True)
        batch_op.alter_column("version_id", existing_type=sa.Integer(), nullable=True)
