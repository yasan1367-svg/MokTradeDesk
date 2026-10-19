"""phase58_prop_dd_config

Add configurable drawdown basis and daily/total drawdown calculation modes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "58a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "54a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS = (
    ("daily_dd_mode", "static"),
    ("total_dd_mode", "static"),
)


def _existing_columns() -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns("prop_stages")}


def upgrade() -> None:
    existing = _existing_columns()
    for name, default in _COLUMNS:
        if name not in existing:
            op.add_column(
                "prop_stages",
                sa.Column(name, sa.String(length=20), nullable=False, server_default=default),
            )
    # The legacy Phase 47 `dd_mode` stored the Total DD policy.
    existing = _existing_columns()
    if "dd_mode" in existing and "total_dd_mode" in existing:
        op.execute(
            "UPDATE prop_stages SET total_dd_mode = dd_mode "
            "WHERE dd_mode IN ('static', 'trailing')"
        )


def downgrade() -> None:
    existing = _existing_columns()
    for name, _default in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("prop_stages", name)