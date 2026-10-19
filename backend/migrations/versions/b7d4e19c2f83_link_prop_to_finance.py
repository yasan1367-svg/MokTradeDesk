"""link_prop_to_finance

Revision ID: b7d4e19c2f83
Revises: 51ea09b4aa3d
Create Date: 2026-09-24 22:40:00.000000

فاز ۵ — یکپارچگی پراپ ↔ مالی:
- prop_accounts.finance_account_id  → accounts.id
- prop_withdrawals.destination_account_id → accounts.id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d4e19c2f83'
down_revision: Union[str, Sequence[str], None] = '51ea09b4aa3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('prop_accounts') as batch_op:
        batch_op.add_column(sa.Column('finance_account_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_prop_accounts_finance_account_id',
            'accounts', ['finance_account_id'], ['id'],
        )

    with op.batch_alter_table('prop_withdrawals') as batch_op:
        batch_op.add_column(sa.Column('destination_account_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_prop_withdrawals_destination_account_id',
            'accounts', ['destination_account_id'], ['id'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('prop_withdrawals') as batch_op:
        batch_op.drop_constraint(
            'fk_prop_withdrawals_destination_account_id', type_='foreignkey'
        )
        batch_op.drop_column('destination_account_id')

    with op.batch_alter_table('prop_accounts') as batch_op:
        batch_op.drop_constraint(
            'fk_prop_accounts_finance_account_id', type_='foreignkey'
        )
        batch_op.drop_column('finance_account_id')
