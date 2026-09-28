"""phase28_finance_cleanup

فاز ۲۸ — پاک‌سازی FINANCE و حذف پل پراپ:
- `prop_accounts.finance_account_id` → حذف (PropAccount حساب معاملاتی است، نه مالی)
- `accounts`: حذف `broker_name`, `prop_firm_name`, `prop_firm_id`
- حذف ردیف‌های `accounts` با type ∈ {PROP, BROKER} (مهاجرت‌شده در migration قبلی)
- `analysis_results/runs`: scope 'BROKER' → 'PERSONAL_ACCOUNT'
- `analysis_results/runs`: `finance_account_id` → `personal_trading_account_id`

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-28 12:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_analysis_table(bind, table: str) -> None:
    """تبدیل finance_account_id → personal_trading_account_id در یک جدول تحلیل."""
    with op.batch_alter_table(table) as batch_op:
        batch_op.add_column(sa.Column("personal_trading_account_id", sa.Integer(), nullable=True))

    bind.execute(sa.text(
        f"UPDATE {table} SET personal_trading_account_id = finance_account_id "
        f"WHERE finance_account_id IS NOT NULL"
    ))
    bind.execute(sa.text(
        f"UPDATE {table} SET scope='PERSONAL_ACCOUNT' WHERE scope='BROKER'"
    ))

    with op.batch_alter_table(table) as batch_op:
        batch_op.create_foreign_key(
            f"fk_{table}_personal_trading_account_id",
            "personal_trading_accounts", ["personal_trading_account_id"], ["id"],
        )
        batch_op.drop_column("finance_account_id")


def upgrade() -> None:
    bind = op.get_bind()

    # ── ۱) حذف پل پراپ → مالی ──
    with op.batch_alter_table("prop_accounts") as batch_op:
        batch_op.drop_column("finance_account_id")

    # ── ۲) پاک‌سازی FINANCE: حذف فیلدهای غیرمالی ──
    # (FK قدیمی prop_firm_id در مأخذ بدون نام ساخته شده؛ batch recreate خودش آن را حذف می‌کند)
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("broker_name")
        batch_op.drop_column("prop_firm_name")
        batch_op.drop_column("prop_firm_id")

    # ── ۳) حذف حساب‌های غیرمالی باقی‌مانده (PROP) ──
    bind.execute(sa.text("DELETE FROM accounts WHERE type NOT IN ('BANK','EXCHANGE','CRYPTO_WALLET')"))

    # ── ۴) دامنهٔ تحلیل: BROKER → PERSONAL_ACCOUNT + تغییر FK ──
    _migrate_analysis_table(bind, "analysis_results")
    _migrate_analysis_table(bind, "analysis_runs")


def downgrade() -> None:
    bind = op.get_bind()

    for table in ("analysis_runs", "analysis_results"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("finance_account_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                f"fk_{table}_finance_account_id",
                "accounts", ["finance_account_id"], ["id"],
            )
            batch_op.drop_column("personal_trading_account_id")
        bind.execute(sa.text(
            f"UPDATE {table} SET scope='BROKER' WHERE scope='PERSONAL_ACCOUNT'"
        ))

    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(sa.Column("prop_firm_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("prop_firm_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("broker_name", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_accounts_prop_firm_id", "prop_firms", ["prop_firm_id"], ["id"],
        )

    with op.batch_alter_table("prop_accounts") as batch_op:
        batch_op.add_column(sa.Column("finance_account_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_prop_accounts_finance_account_id",
            "accounts", ["finance_account_id"], ["id"],
        )
