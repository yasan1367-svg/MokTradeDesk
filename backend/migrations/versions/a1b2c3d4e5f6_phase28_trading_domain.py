"""phase28_trading_domain

فاز ۲۸ — دامنهٔ TRADING + نگاشت test_type:
- نگاشت `trades.test_type`: REAL + finance_account_id → REAL_PERSONAL، REAL + prop_stage_id → REAL_PROP
- حذف معاملات با `version_id IS NULL` (تصمیم فاز ۲۸)
- ساخت جدول‌های `brokers` و `personal_trading_accounts`
- مهاجرت `accounts(type=BROKER)` → Broker + PersonalTradingAccount
- افزودن `trades.personal_trading_account_id` و حذف `trades.finance_account_id`

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-09-28 12:00:00.000000
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _now():
    return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()

    # ── ۱) نگاشت test_type قدیمی (REAL) به قرارداد جدید (قبل از حذف ستون) ──
    bind.execute(sa.text(
        "UPDATE trades SET test_type='REAL_PERSONAL' "
        "WHERE test_type='REAL' AND finance_account_id IS NOT NULL"
    ))
    bind.execute(sa.text(
        "UPDATE trades SET test_type='REAL_PROP' "
        "WHERE test_type='REAL' AND prop_stage_id IS NOT NULL"
    ))
    # REAL نامعتبر (نه حساب شخصی، نه پراپ) → حذف
    bind.execute(sa.text("DELETE FROM trades WHERE test_type='REAL'"))
    # قرارداد جدید: version_id اجباری → رکوردهای NULL (باگ import) حذف می‌شوند
    bind.execute(sa.text("DELETE FROM trades WHERE version_id IS NULL"))

    # ── ۲) جداول دامنهٔ TRADING ──
    op.create_table(
        "brokers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brokers_id"), "brokers", ["id"], unique=False)

    op.create_table(
        "personal_trading_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("broker_id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("account_label", sa.String(), nullable=True),
        sa.Column("currency", sa.Enum("IRR", "USD", name="currency"), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=False),
        sa.Column("current_balance", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["broker_id"], ["brokers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_personal_trading_accounts_id"), "personal_trading_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_personal_trading_accounts_broker_id"), "personal_trading_accounts", ["broker_id"], unique=False)

    # ── ۳) مهاجرت accounts(type=BROKER) → Broker + PersonalTradingAccount ──
    rows = bind.execute(sa.text(
        "SELECT id, name, currency, balance, broker_name, created_at "
        "FROM accounts WHERE type='BROKER'"
    )).fetchall()
    pta_map = {}
    for acc_id, name, currency, balance, broker_name, created_at in rows:
        broker_label = broker_name or name
        existing = bind.execute(
            sa.text("SELECT id FROM brokers WHERE name=:n"), {"n": broker_label}
        ).fetchone()
        if existing:
            broker_id = existing[0]
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO brokers (name, website, notes, is_active, created_at) "
                    "VALUES (:n, NULL, NULL, 1, :c)"
                ),
                {"n": broker_label, "c": created_at or _now()},
            )
            broker_id = bind.execute(sa.text("SELECT last_insert_rowid()")).scalar()

        cur = "IRR" if str(currency or "USD").upper() == "IRR" else "USD"
        bal = float(balance or 0.0)
        bind.execute(
            sa.text(
                "INSERT INTO personal_trading_accounts "
                "(broker_id, account_number, account_label, currency, initial_balance, "
                " current_balance, is_active, created_at) "
                "VALUES (:b, :num, :label, :cur, :ib, :cb, 1, :c)"
            ),
            {"b": broker_id, "num": name, "label": name, "cur": cur,
             "ib": bal, "cb": bal, "c": created_at or _now()},
        )
        pta_id = bind.execute(sa.text("SELECT last_insert_rowid()")).scalar()
        pta_map[acc_id] = pta_id

    # ── ۴) trades.personal_trading_account_id (backfill + حذف finance_account_id) ──
    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(sa.Column("personal_trading_account_id", sa.Integer(), nullable=True))

    for acc_id, pta_id in pta_map.items():
        bind.execute(
            sa.text("UPDATE trades SET personal_trading_account_id=:p WHERE finance_account_id=:a"),
            {"p": pta_id, "a": acc_id},
        )

    with op.batch_alter_table("trades") as batch_op:
        batch_op.create_foreign_key(
            "fk_trades_personal_trading_account_id",
            "personal_trading_accounts", ["personal_trading_account_id"], ["id"],
        )
        batch_op.drop_column("finance_account_id")

    # ── ۵) حذف حساب‌های BROKER که به TRADING منتقل شدند ──
    bind.execute(sa.text("DELETE FROM accounts WHERE type='BROKER'"))


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(sa.Column("finance_account_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_trades_finance_account_id",
            "accounts", ["finance_account_id"], ["id"],
        )
        batch_op.drop_column("personal_trading_account_id")

    bind.execute(sa.text(
        "UPDATE trades SET test_type='REAL' WHERE test_type IN ('REAL_PERSONAL','REAL_PROP')"
    ))

    op.drop_index(op.f("ix_personal_trading_accounts_broker_id"), table_name="personal_trading_accounts")
    op.drop_index(op.f("ix_personal_trading_accounts_id"), table_name="personal_trading_accounts")
    op.drop_table("personal_trading_accounts")
    op.drop_index(op.f("ix_brokers_id"), table_name="brokers")
    op.drop_table("brokers")
