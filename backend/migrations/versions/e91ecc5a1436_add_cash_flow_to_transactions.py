"""add cash_flow to transactions

Revision ID: e91ecc5a1436
Revises: cb282f44503c
Create Date: 2026-10-08 15:27:38.560815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e91ecc5a1436'
down_revision: Union[str, Sequence[str], None] = 'cb282f44503c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('cash_flow', sa.Enum('none', 'expense', 'income', name='cashflow'), nullable=False, server_default='none'))
    op.create_index(op.f('ix_transactions_cash_flow'), 'transactions', ['cash_flow'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_cash_flow'), table_name='transactions')
    op.drop_column('transactions', 'cash_flow')
