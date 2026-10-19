"""clear legacy xml events

Revision ID: 5691cf13a881
Revises: d8b7235fea25
Create Date: 2026-10-07 13:33:09.415144

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5691cf13a881'
down_revision: Union[str, Sequence[str], None] = 'd8b7235fea25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("economic_events"):
        op.execute("DELETE FROM economic_events")


def downgrade() -> None:
    pass
