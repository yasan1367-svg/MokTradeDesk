"""phase33_prop_withdrawal

فاز ۳۳ — چرخه‌ی عمر برداشت پراپ:
- `prop_withdrawals`: `+ currency Enum(Currency)`, `+ status Enum(WithdrawalStatus)`,
  `+ reference`, `+ transaction_id → transactions.id`, `+ created_at`
- سخت‌گیری روی NOT NULL برای `withdrawal_date` و `destination_account_id` (در صورت نبود NULL)
- Backfill: رکوردهای تاریخی ⇒ `status = 'RECEIVED'` (چون قبلاً همین‌جا درآمد ثبت می‌شد)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-29 11:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CURRENCY = sa.Enum("IRR", "USD", name="currency")
_WITHDRAWAL_STATUS = sa.Enum(
    "REQUESTED", "APPROVED", "PROCESSING", "RECEIVED", "CANCELLED",
    name="withdrawalstatus",
)


def upgrade() -> None:
    with op.batch_alter_table("prop_withdrawals") as batch:
        batch.add_column(sa.Column("currency", _CURRENCY, nullable=True))
        batch.add_column(sa.Column("status", _WITHDRAWAL_STATUS, nullable=True))
        batch.add_column(sa.Column("reference", sa.String(), nullable=True))
        batch.add_column(sa.Column("transaction_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            )
        )
        batch.create_foreign_key(
            "fk_prop_withdrawals_transaction_id",
            "transactions",
            ["transaction_id"],
            ["id"],
        )

    # ── Backfill ──
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE prop_withdrawals SET status = 'RECEIVED' WHERE status IS NULL"
    ))
    bind.execute(sa.text(
        "UPDATE prop_withdrawals SET currency = 'USD' WHERE currency IS NULL"
    ))
    bind.execute(sa.text(
        "UPDATE prop_withdrawals SET created_at = COALESCE(withdrawal_date, CURRENT_TIMESTAMP) "
        "WHERE created_at IS NULL"
    ))

    # ── NOT NULL (فقط اگر داده‌ی ناسازگار قدیمی وجود نداشته باشد) ──
    nulls = bind.execute(sa.text(
        "SELECT COUNT(*) FROM prop_withdrawals WHERE currency IS NULL OR status IS NULL "
        "OR withdrawal_date IS NULL OR destination_account_id IS NULL"
    )).scalar()
    if not nulls:
        with op.batch_alter_table("prop_withdrawals") as batch:
            batch.alter_column("currency", existing_type=sa.String(length=3), nullable=False)
            batch.alter_column("status", existing_type=sa.String(length=10), nullable=False)
            batch.alter_column("withdrawal_date", existing_type=sa.DateTime(), nullable=False)
            batch.alter_column("destination_account_id", existing_type=sa.Integer(), nullable=False)

    op.create_index(
        op.f("ix_prop_withdrawals_status"), "prop_withdrawals", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_prop_withdrawals_status"), table_name="prop_withdrawals")
    with op.batch_alter_table("prop_withdrawals") as batch:
        batch.drop_constraint("fk_prop_withdrawals_transaction_id", type_="foreignkey")
        batch.drop_column("created_at")
        batch.drop_column("transaction_id")
        batch.drop_column("reference")
        batch.drop_column("status")
        batch.drop_column("currency")
