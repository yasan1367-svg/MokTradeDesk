"""merge_personal_into_finance

Phase 9 — ادغام دفتر کل شخصی ↔ مالی:
- personal_accounts   → accounts  (type=BROKER)
- ledger_transactions → transactions (با نگاشت نوع و علامت)
- trades.personal_account_id → trades.finance_account_id (FK → accounts.id)
- حذف جدول‌های personal_accounts و ledger_transactions

Revision ID: 9f1a2b3c4d5e
Revises: b7d4e19c2f83
Create Date: 2026-09-25 02:20:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f1a2b3c4d5e'
down_revision: Union[str, Sequence[str], None] = 'b7d4e19c2f83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# نگاشت transaction_type دفتر کل → type مالی
LEDGER_TYPE_MAP = {
    "DEPOSIT": "DEPOSIT",
    "WITHDRAWAL": "WITHDRAWAL",
    "PROP_PAYOUT": "PROFIT",
    "CHALLENGE_FEE": "PURCHASE",
    "EXPENSE": "FEE",
}


def _fetchall(bind, sql, **params):
    return bind.execute(sa.text(sql), params).fetchall()


def _scalar(bind, sql, **params):
    return bind.execute(sa.text(sql), params).scalar()


def _last_id(bind):
    return bind.execute(sa.text("SELECT last_insert_rowid()")).scalar()


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # ═════════════════════════════════════════════
    # ۱) افزودن trades.finance_account_id (FK → accounts.id)
    # ═════════════════════════════════════════════
    with op.batch_alter_table('trades') as batch_op:
        batch_op.add_column(sa.Column('finance_account_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_trades_finance_account_id',
            'accounts', ['finance_account_id'], ['id'],
        )

    # ═════════════════════════════════════════════
    # ۲) personal_accounts → accounts  (نگاشت id ها)
    # ═════════════════════════════════════════════
    personal_rows = _fetchall(
        bind,
        "SELECT id, name, broker_name, currency, initial_balance, created_at "
        "FROM personal_accounts",
    )
    account_map = {}
    for r in personal_rows:
        pa_id, name, broker_name, currency, initial_balance, created_at = r
        flow = _scalar(
            bind,
            "SELECT COALESCE(SUM(amount), 0) FROM ledger_transactions "
            "WHERE personal_account_id = :aid",
            aid=pa_id,
        ) or 0.0
        cur = "IRR" if str(currency or "USD").upper() == "IRR" else "USD"
        bind.execute(
            sa.text(
                "INSERT INTO accounts "
                "(name, type, currency, balance, card_number, broker_name, "
                " prop_firm_name, prop_firm_id, created_at) "
                "VALUES (:name, 'BROKER', :cur, :bal, NULL, :broker, NULL, NULL, :created)"
            ),
            {
                "name": name,
                "cur": cur,
                "bal": float(initial_balance or 0.0) + float(flow),
                "broker": broker_name,
                "created": created_at,
            },
        )
        account_map[pa_id] = _last_id(bind)

    # ═════════════════════════════════════════════
    # ۳) ledger_transactions → transactions
    # ═════════════════════════════════════════════
    default_account_holder = {}

    def get_default_account_id():
        if "id" in default_account_holder:
            return default_account_holder["id"]
        aid = _scalar(bind, "SELECT id FROM accounts ORDER BY id LIMIT 1")
        if aid is None:
            bind.execute(
                sa.text(
                    "INSERT INTO accounts "
                    "(name, type, currency, balance, card_number, broker_name, "
                    " prop_firm_name, prop_firm_id, created_at) "
                    "VALUES ('حساب پیش‌فرض', 'BROKER', 'USD', 0.0, NULL, NULL, NULL, NULL, :created)"
                ),
                {"created": datetime.now(timezone.utc)},
            )
            aid = _last_id(bind)
        default_account_holder["id"] = aid
        return aid

    ledger_rows = _fetchall(
        bind,
        "SELECT id, transaction_type, source_type, source_id, personal_account_id, "
        "prop_account_id, amount, currency, description, transaction_date, created_at "
        "FROM ledger_transactions",
    )

    for r in ledger_rows:
        (l_id, ttype, source_type, source_id, pa_id, prop_account_id,
         amount, currency, description, tx_date, created_at) = r
        amount = float(amount or 0.0)

        # تعیین حساب مقصد
        account_id = account_map.get(pa_id)
        if account_id is None and prop_account_id is not None:
            account_id = _scalar(
                bind,
                "SELECT finance_account_id FROM prop_accounts WHERE id = :pid",
                pid=prop_account_id,
            )
        if account_id is None:
            account_id = get_default_account_id()

        # نگاشت نوع (بدون علامت؛ جهت با type مشخص می‌شود)
        if ttype == "TRADE_PNL":
            ftype = "PROFIT" if amount >= 0 else "LOSS"
        elif ttype == "MANUAL_ADJUSTMENT":
            ftype = "DEPOSIT" if amount >= 0 else "WITHDRAWAL"
        else:
            ftype = LEDGER_TYPE_MAP.get(ttype, "DEPOSIT")

        cur = "IRR" if str(currency or "USD").upper() == "IRR" else "USD"
        related_trade_id = (
            source_id
            if (source_type and "trade" in str(source_type).lower())
            else None
        )

        bind.execute(
            sa.text(
                "INSERT INTO transactions "
                "(account_id, category_id, amount, currency, date, description, type, "
                " from_account_id, to_account_id, related_trade_id, related_prop_account_id, "
                " is_deleted, created_at) "
                "VALUES (:acct, NULL, :amount, :cur, :date, :desc, :type, "
                " NULL, NULL, :rtid, :rpid, 0, :created)"
            ),
            {
                "acct": account_id,
                "amount": abs(amount),
                "cur": cur,
                "date": tx_date,
                "desc": description,
                "type": ftype,
                "rtid": related_trade_id,
                "rpid": prop_account_id,
                "created": created_at,
            },
        )

    # ═════════════════════════════════════════════
    # ۴) trades.personal_account_id → finance_account_id
    # ═════════════════════════════════════════════
    trade_rows = _fetchall(
        bind,
        "SELECT id, personal_account_id FROM trades WHERE personal_account_id IS NOT NULL",
    )
    for tid, pa_id in trade_rows:
        if pa_id in account_map:
            bind.execute(
                sa.text("UPDATE trades SET finance_account_id = :faid WHERE id = :tid"),
                {"faid": account_map[pa_id], "tid": tid},
            )

    # ═════════════════════════════════════════════
    # ۵) حذف ستون قدیمی و جدول‌های قدیمی
    # ═════════════════════════════════════════════
    with op.batch_alter_table('trades') as batch_op:
        batch_op.drop_column('personal_account_id')

    op.drop_index(op.f('ix_ledger_transactions_id'), table_name='ledger_transactions')
    op.drop_table('ledger_transactions')
    op.drop_index(op.f('ix_personal_accounts_id'), table_name='personal_accounts')
    op.drop_table('personal_accounts')


def downgrade() -> None:
    """Downgrade schema (ساختار جدول‌های قدیمی بازسازی می‌شود؛ داده‌ها برنمی‌گردند)."""
    op.create_table(
        'personal_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('broker_name', sa.String(), nullable=False),
        sa.Column('account_number', sa.String(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('initial_balance', sa.Float(), nullable=True),
        sa.Column('current_balance', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_personal_accounts_id'), 'personal_accounts', ['id'], unique=False)

    op.create_table(
        'ledger_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(length=17), nullable=False),
        sa.Column('source_type', sa.String(), nullable=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('personal_account_id', sa.Integer(), nullable=True),
        sa.Column('prop_account_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['personal_account_id'], ['personal_accounts.id']),
        sa.ForeignKeyConstraint(['prop_account_id'], ['prop_accounts.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ledger_transactions_id'), 'ledger_transactions', ['id'], unique=False)

    with op.batch_alter_table('trades') as batch_op:
        batch_op.drop_constraint('fk_trades_finance_account_id', type_='foreignkey')
        batch_op.drop_column('finance_account_id')
        batch_op.add_column(sa.Column('personal_account_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_trades_personal_account_id',
            'personal_accounts', ['personal_account_id'], ['id'],
        )
