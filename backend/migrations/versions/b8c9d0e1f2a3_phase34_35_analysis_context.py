"""phase34_35_analysis_context

فاز ۳۴ — Analysis Context:
- جدول جدید `analysis_scopes` (مدل `AnalysisScopeRecord`)
- قانون: همه‌ی تحلیل‌ها از این دامنه استفاده کنند

فاز ۳۵ — AnalysisRun & Historical Results (افزودنی):
- `analysis_runs`:  + scope_id (FK), + filters_snapshot (JSON), + trade_count, + status
- `analysis_results`: + analysis_run_id (FK ← analysis_runs.id)
- بدون حذف/تغییر ستون‌های موجود؛ Run #1 ثابت می‌ماند و اجرای جدید Run #2 جدا می‌سازد.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-29 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TEST_TYPE = sa.Enum(
    "BACKTEST", "FORWARD", "REAL_PERSONAL", "REAL_PROP", name="testtype"
)
_ANALYSIS_STATUS = sa.Enum(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", name="analysisstatus"
)


def upgrade() -> None:
    # ── ۱) جدول دامنه‌ی تحلیل (فاز ۳۴) ──
    op.create_table(
        "analysis_scopes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_version_id", sa.Integer(), nullable=True),
        sa.Column("trade_type", _TEST_TYPE, nullable=False),
        sa.Column("personal_trading_account_id", sa.Integer(), nullable=True),
        sa.Column("prop_stage_id", sa.Integer(), nullable=True),
        sa.Column("from_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("to_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted_filter", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"]),
        sa.ForeignKeyConstraint(["personal_trading_account_id"], ["personal_trading_accounts.id"]),
        sa.ForeignKeyConstraint(["prop_stage_id"], ["prop_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_scopes_id"), "analysis_scopes", ["id"], unique=False)

    # ── ۲) ستون‌های analysis_runs (فاز ۳۵) ──
    with op.batch_alter_table("analysis_runs") as batch:
        batch.add_column(sa.Column("scope_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("filters_snapshot", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("trade_count", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("status", _ANALYSIS_STATUS, nullable=True))
        batch.create_foreign_key(
            "fk_analysis_runs_scope_id", "analysis_scopes", ["scope_id"], ["id"]
        )
    op.create_index(op.f("ix_analysis_runs_scope_id"), "analysis_runs", ["scope_id"], unique=False)

    # ── ۳) ستون analysis_results (فاز ۳۵) ──
    with op.batch_alter_table("analysis_results") as batch:
        batch.add_column(sa.Column("analysis_run_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_analysis_results_analysis_run_id", "analysis_runs", ["analysis_run_id"], ["id"]
        )
    op.create_index(
        op.f("ix_analysis_results_analysis_run_id"),
        "analysis_results",
        ["analysis_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_analysis_results_analysis_run_id"), table_name="analysis_results"
    )
    with op.batch_alter_table("analysis_results") as batch:
        batch.drop_constraint("fk_analysis_results_analysis_run_id", type_="foreignkey")
        batch.drop_column("analysis_run_id")

    op.drop_index(op.f("ix_analysis_runs_scope_id"), table_name="analysis_runs")
    with op.batch_alter_table("analysis_runs") as batch:
        batch.drop_constraint("fk_analysis_runs_scope_id", type_="foreignkey")
        batch.drop_column("status")
        batch.drop_column("trade_count")
        batch.drop_column("filters_snapshot")
        batch.drop_column("scope_id")

    op.drop_index(op.f("ix_analysis_scopes_id"), table_name="analysis_scopes")
    op.drop_table("analysis_scopes")
