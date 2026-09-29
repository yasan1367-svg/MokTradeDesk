"""phase32_rule_engine

فاز ۳۲ — موتور قوانین پراپ:
- `rule_violations` : تاریخچه‌ی ارزیابی قوانین هر مرحله پراپ
  (RuleType × Severity: PASS/WARNING/VIOLATION)

Revision ID: f6a7b8c9d0e1
Revises: d4e5f6a7b8c9
Create Date: 2026-09-29 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rule_violations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prop_stage_id", sa.Integer(), nullable=False),
        sa.Column(
            "rule_type",
            sa.Enum(
                "DAILY_DRAWDOWN",
                "MAX_DRAWDOWN",
                "PROFIT_TARGET",
                "MIN_TRADING_DAYS",
                "EQUITY_BALANCE",
                "FLOATING_PNL",
                "STAGE_STATUS",
                name="ruletype",
            ),
            nullable=False,
        ),
        sa.Column("actual_value", sa.Float(), nullable=False),
        sa.Column("limit_value", sa.Float(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("PASS", "WARNING", "VIOLATION", name="severity"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["prop_stage_id"], ["prop_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rule_violations_id"), "rule_violations", ["id"], unique=False)
    op.create_index(
        op.f("ix_rule_violations_prop_stage_id"), "rule_violations", ["prop_stage_id"], unique=False
    )
    op.create_index(op.f("ix_rule_violations_rule_type"), "rule_violations", ["rule_type"], unique=False)
    op.create_index(op.f("ix_rule_violations_severity"), "rule_violations", ["severity"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rule_violations_severity"), table_name="rule_violations")
    op.drop_index(op.f("ix_rule_violations_rule_type"), table_name="rule_violations")
    op.drop_index(op.f("ix_rule_violations_prop_stage_id"), table_name="rule_violations")
    op.drop_index(op.f("ix_rule_violations_id"), table_name="rule_violations")
    op.drop_table("rule_violations")
