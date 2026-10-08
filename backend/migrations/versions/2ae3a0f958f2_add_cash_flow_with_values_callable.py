"""add cash_flow with values_callable

Revision ID: 2ae3a0f958f2
Revises: cb282f44503c
Create Date: 2026-10-08 19:52:04.799985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ae3a0f958f2'
down_revision: Union[str, Sequence[str], None] = 'cb282f44503c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column(
            'cash_flow',
            sa.Enum('none', 'expense', 'income', name='cashflow', native_enum=False, length=10),
            nullable=False,
            server_default='none',
        ),
    )
    op.create_index(op.f('ix_transactions_cash_flow'), 'transactions', ['cash_flow'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_cash_flow'), table_name='transactions')
    op.drop_column('transactions', 'cash_flow')
