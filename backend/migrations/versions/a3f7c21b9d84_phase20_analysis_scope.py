"""phase20_analysis_scope

فاز ۲۰.۱ — دامنه‌ی تحلیل (AnalysisScope)

- افزودن `scope` + `scope_key` به `analysis_results` و `analysis_runs`
- افزودن `prop_stage_id` + `finance_account_id` (FK) به هر دو جدول
- `version_id` از NOT NULL به NULL (تحلیل پراپ/بروکر version_id ندارد)
- `UniqueConstraint(scope, scope_key)` روی `analysis_results` (وضعیت جاری)
  — `analysis_runs` بدون unique چون تاریخچه‌ی اجراهاست

مقدار `scope` به‌صورت NAME ذخیره می‌شود: 'VERSION' / 'PROP_STAGE' / 'BROKER'
رکوردهای موجود → scope='VERSION' و scope_key=str(version_id)

Revision ID: a3f7c21b9d84
Revises: 9f1a2b3c4d5e
Create Date: 2026-09-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c21b9d84'
down_revision: Union[str, Sequence[str], None] = '9f1a2b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _scope_enum() -> sa.Enum:
    """نمونه‌ی تازه از Enum — هر جدول نمونه‌ی مستقل خودش را می‌گیرد"""
    return sa.Enum('VERSION', 'PROP_STAGE', 'BROKER', name='analysisscope')


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # ═════════════════════════════════════════════
    # ۱) analysis_results — افزودن ستون‌ها (موقتاً nullable)
    # ═════════════════════════════════════════════
    with op.batch_alter_table('analysis_results') as batch_op:
        batch_op.add_column(sa.Column('scope', _scope_enum(), nullable=True))
        batch_op.add_column(sa.Column('scope_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('prop_stage_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('finance_account_id', sa.Integer(), nullable=True))

    # ── پرکردن رکوردهای موجود ──
    bind.execute(sa.text(
        "UPDATE analysis_results "
        "SET scope = 'VERSION', scope_key = CAST(version_id AS TEXT) "
        "WHERE scope IS NULL"
    ))

    # ═════════════════════════════════════════════
    # ۲) analysis_results — اعمال قیدها
    # ═════════════════════════════════════════════
    with op.batch_alter_table('analysis_results') as batch_op:
        batch_op.alter_column('scope', existing_type=_scope_enum(),
                              existing_nullable=True, nullable=False)
        batch_op.alter_column('scope_key', existing_type=sa.String(),
                              existing_nullable=True, nullable=False)
        batch_op.alter_column('version_id', existing_type=sa.Integer(),
                              existing_nullable=False, nullable=True)
        batch_op.create_foreign_key(
            'fk_analysis_results_prop_stage_id', 'prop_stages',
            ['prop_stage_id'], ['id'],
        )
        batch_op.create_foreign_key(
            'fk_analysis_results_finance_account_id', 'accounts',
            ['finance_account_id'], ['id'],
        )
        batch_op.create_unique_constraint(
            'uq_analysis_results_scope_key', ['scope', 'scope_key'],
        )
        batch_op.create_index('ix_analysis_results_scope', ['scope'])
        batch_op.create_index('ix_analysis_results_scope_key', ['scope_key'])

    # ═════════════════════════════════════════════
    # ۳) analysis_runs — افزودن ستون‌ها (موقتاً nullable)
    # ═════════════════════════════════════════════
    with op.batch_alter_table('analysis_runs') as batch_op:
        batch_op.add_column(sa.Column('scope', _scope_enum(), nullable=True))
        batch_op.add_column(sa.Column('scope_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('prop_stage_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('finance_account_id', sa.Integer(), nullable=True))

    bind.execute(sa.text(
        "UPDATE analysis_runs "
        "SET scope = 'VERSION', scope_key = CAST(version_id AS TEXT) "
        "WHERE scope IS NULL"
    ))

    # ═════════════════════════════════════════════
    # ۴) analysis_runs — اعمال قیدها (بدون unique — تاریخچه)
    # ═════════════════════════════════════════════
    with op.batch_alter_table('analysis_runs') as batch_op:
        batch_op.alter_column('scope', existing_type=_scope_enum(),
                              existing_nullable=True, nullable=False)
        batch_op.alter_column('scope_key', existing_type=sa.String(),
                              existing_nullable=True, nullable=False)
        batch_op.alter_column('version_id', existing_type=sa.Integer(),
                              existing_nullable=False, nullable=True)
        batch_op.create_foreign_key(
            'fk_analysis_runs_prop_stage_id', 'prop_stages',
            ['prop_stage_id'], ['id'],
        )
        batch_op.create_foreign_key(
            'fk_analysis_runs_finance_account_id', 'accounts',
            ['finance_account_id'], ['id'],
        )
        batch_op.create_index('ix_analysis_runs_scope', ['scope'])
        batch_op.create_index('ix_analysis_runs_scope_key', ['scope_key'])


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # رکوردهای غیر-VERSION بدون version_id معنا ندارند → حذف
    bind.execute(sa.text("DELETE FROM analysis_results WHERE scope != 'VERSION'"))
    bind.execute(sa.text("DELETE FROM analysis_runs WHERE scope != 'VERSION'"))

    # ── analysis_results ──
    op.drop_index('ix_analysis_results_scope_key', table_name='analysis_results')
    op.drop_index('ix_analysis_results_scope', table_name='analysis_results')
    with op.batch_alter_table('analysis_results') as batch_op:
        batch_op.drop_constraint('uq_analysis_results_scope_key', type_='unique')
        batch_op.drop_constraint('fk_analysis_results_finance_account_id', type_='foreignkey')
        batch_op.drop_constraint('fk_analysis_results_prop_stage_id', type_='foreignkey')
        batch_op.alter_column('version_id', existing_type=sa.Integer(),
                              existing_nullable=True, nullable=False)
        batch_op.drop_column('finance_account_id')
        batch_op.drop_column('prop_stage_id')
        batch_op.drop_column('scope_key')
        batch_op.drop_column('scope')

    # ── analysis_runs ──
    op.drop_index('ix_analysis_runs_scope_key', table_name='analysis_runs')
    op.drop_index('ix_analysis_runs_scope', table_name='analysis_runs')
    with op.batch_alter_table('analysis_runs') as batch_op:
        batch_op.drop_constraint('fk_analysis_runs_finance_account_id', type_='foreignkey')
        batch_op.drop_constraint('fk_analysis_runs_prop_stage_id', type_='foreignkey')
        batch_op.alter_column('version_id', existing_type=sa.Integer(),
                              existing_nullable=True, nullable=False)
        batch_op.drop_column('finance_account_id')
        batch_op.drop_column('prop_stage_id')
        batch_op.drop_column('scope_key')
        batch_op.drop_column('scope')

