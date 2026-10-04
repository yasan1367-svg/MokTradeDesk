"""phase4_initial_sl

Add initial_sl to trades as a first-class column.

Before this migration, initial_sl was only stored inside the opaque
raw_data JSON blob (Phase 53.3). This migration:
  1. Adds initial_sl as a nullable Float column.
  2. Backfills existing rows: initial_sl = sl as best-effort when
     raw_data contains no initial_sl that can be promoted.

Revision ID: e4f5a6b7c8d9
Revises: 61b2c3d4e5f6
Create Date: 2026-10-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "61b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "trades"
_COLUMN = "initial_sl"


def _existing_columns(table: str) -> set:
    return {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    # 1. Add column
    if _COLUMN not in _existing_columns(_TABLE):
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.Float(), nullable=True),
        )

    # 2. Backfill: initial_sl = sl for rows where initial_sl IS NULL
    #    If raw_data contains a usable initial_sl, promote it instead.
    bind = op.get_bind()
    # Promote raw_data -> initial_sl where raw_data is valid JSON with an initial_sl key
    try:
        bind.execute(text(
            f"UPDATE {_TABLE} "
            f"SET {_COLUMN} = JSON_EXTRACT(raw_data, '$.initial_sl') "
            f"WHERE {_COLUMN} IS NULL AND raw_data IS NOT NULL "
            f"AND JSON_VALID(raw_data) AND JSON_EXTRACT(raw_data, '$.initial_sl') IS NOT NULL"
        ))
    except Exception:
        # SQLite JSON functions may not be available; fallback below
        pass

    # Remaining NULLs get initial_sl = sl
    bind.execute(text(
        f"UPDATE {_TABLE} "
        f"SET {_COLUMN} = sl "
        f"WHERE {_COLUMN} IS NULL AND sl IS NOT NULL"
    ))


def downgrade() -> None:
    if _COLUMN in _existing_columns(_TABLE):
        op.drop_column(_TABLE, _COLUMN)