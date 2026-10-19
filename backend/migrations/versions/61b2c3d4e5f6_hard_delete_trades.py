"""Remove trade soft-delete state and normalize legacy import row status.

Revision ID: 61b2c3d4e5f6
Revises: 58a1b2c3d4e5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "61b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "58a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "import_batch_rows" in inspector.get_table_names() and bind.dialect.name == "sqlite":
        # The former app-only state may exist in SQLite's plain text enum column.
        op.execute(
            sa.text("UPDATE import_batch_rows SET status = 'NEW' WHERE status = 'RESTORED'")
        )

    if "trades" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("trades")}
        if "is_deleted" in columns:
            # Permanently purge rows hidden by the old soft-delete flag before
            # dropping it, so they do not reappear as active journal entries.
            deleted_ids = "SELECT id FROM trades WHERE is_deleted IS TRUE"
            tables = set(inspector.get_table_names())
            if "screenshots" in tables:
                if "journal_reviews" in tables:
                    op.execute(sa.text(
                        "DELETE FROM screenshots WHERE review_id IN "
                        f"(SELECT id FROM journal_reviews WHERE trade_id IN ({deleted_ids}))"
                    ))
                op.execute(sa.text(
                    "DELETE FROM screenshots WHERE entity_type = 'trade' "
                    f"AND entity_id IN ({deleted_ids})"
                ))
            if "import_identities" in tables:
                op.execute(sa.text(
                    f"DELETE FROM import_identities WHERE trade_id IN ({deleted_ids})"
                ))
            if "journal_reviews" in tables:
                op.execute(sa.text(
                    f"DELETE FROM journal_reviews WHERE trade_id IN ({deleted_ids})"
                ))
            if "transactions" in tables:
                transaction_columns = {
                    column["name"] for column in inspector.get_columns("transactions")
                }
                if "related_trade_id" in transaction_columns:
                    op.execute(sa.text(
                        "UPDATE transactions SET related_trade_id = NULL "
                        f"WHERE related_trade_id IN ({deleted_ids})"
                    ))
            op.execute(sa.text(f"DELETE FROM trades WHERE id IN ({deleted_ids})"))

            indexes = {index["name"] for index in inspector.get_indexes("trades")}
            if "ix_trades_is_deleted" in indexes:
                op.drop_index("ix_trades_is_deleted", table_name="trades")
            with op.batch_alter_table("trades") as batch_op:
                batch_op.drop_column("is_deleted")


def downgrade() -> None:
    with op.batch_alter_table("trades") as batch_op:
        batch_op.add_column(
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0")
        )
    op.create_index("ix_trades_is_deleted", "trades", ["is_deleted"], unique=False)
