"""add convert transaction fields

Revision ID: cb282f44503c
Revises: 5691cf13a881
Create Date: 2026-10-08 12:29:06.852428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb282f44503c'
down_revision: Union[str, Sequence[str], None] = '5691cf13a881'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transactions', sa.Column('to_amount', sa.Float(), nullable=True))
    op.add_column('transactions', sa.Column('to_currency', sa.Enum('IRR', 'USDT', name='currency'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transactions') as batch:
        batch.drop_column('to_currency')
        batch.drop_column('to_amount')
