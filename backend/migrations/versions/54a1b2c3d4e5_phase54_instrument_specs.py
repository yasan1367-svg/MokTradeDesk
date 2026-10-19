"""phase54_instrument_specs

Create broker-independent instrument specifications and seed common instruments.
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "54a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "f53a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instrument_specs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("canonical_symbol", sa.String(length=50), nullable=False),
        sa.Column("broker_symbol", sa.String(length=50), nullable=True),
        sa.Column("contract_size", sa.Float(), nullable=False),
        sa.Column("tick_size", sa.Float(), nullable=False),
        sa.Column("tick_value", sa.Float(), nullable=False),
        sa.Column("point_size", sa.Float(), nullable=True),
        sa.Column("min_lot", sa.Float(), nullable=False),
        sa.Column("max_lot", sa.Float(), nullable=False),
        sa.Column("lot_step", sa.Float(), nullable=False),
        sa.Column("commission_one_side", sa.Float(), nullable=False),
        sa.Column("currency", sa.Enum("IRR", "USDT", name="currency"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_symbol"),
    )

    instrument_specs = sa.table(
        "instrument_specs",
        sa.column("canonical_symbol", sa.String(length=50)),
        sa.column("broker_symbol", sa.String(length=50)),
        sa.column("contract_size", sa.Float()),
        sa.column("tick_size", sa.Float()),
        sa.column("tick_value", sa.Float()),
        sa.column("point_size", sa.Float()),
        sa.column("min_lot", sa.Float()),
        sa.column("max_lot", sa.Float()),
        sa.column("lot_step", sa.Float()),
        sa.column("commission_one_side", sa.Float()),
        sa.column("currency", sa.String(length=4)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    created_at = datetime.now(timezone.utc)
    common = {
        "broker_symbol": None,
        "min_lot": 0.01,
        "max_lot": 100.0,
        "lot_step": 0.01,
        "commission_one_side": 0.0,
        "currency": "USDT",
        "created_at": created_at,
    }
    op.bulk_insert(
        instrument_specs,
        [
            {
                **common,
                "canonical_symbol": "EURUSD",
                "contract_size": 100000.0,
                "tick_size": 0.0001,
                "tick_value": 10.0,
                "point_size": 0.0001,
            },
            {
                **common,
                "canonical_symbol": "GBPUSD",
                "contract_size": 100000.0,
                "tick_size": 0.0001,
                "tick_value": 10.0,
                "point_size": 0.0001,
            },
            {
                **common,
                "canonical_symbol": "XAUUSD",
                "contract_size": 100.0,
                "tick_size": 0.01,
                "tick_value": 1.0,
                "point_size": 0.01,
            },
            {
                **common,
                "canonical_symbol": "DJI30",
                "contract_size": 1.0,
                "tick_size": 1.0,
                "tick_value": 1.0,
                "point_size": 1.0,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("instrument_specs")