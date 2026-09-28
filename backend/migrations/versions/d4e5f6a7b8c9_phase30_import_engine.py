"""phase30_import_engine

فاز ۳۰ — موتور ایمپورت:
- `import_profiles`   : پروفایل ایمپورت (Broker/SourceFormat/Symbol+Column Mapping/Default Context)
- `import_batches`    : سرشماری هر اجرای ایمپورت
- `import_batch_rows` : ردیف‌های staging (خروجی Preview، ورودی Commit)

فاز ۳۱ — یکپارچگی تکرار:
- `import_identities` : هویت هر معامله‌ی واردشده + Backfill از معاملات موجود
  (شامل معاملات Soft-Deleted، طبق قانون فاز ۳۱)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-28 13:00:00.000000
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional, Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═════════════════════════════════════════════
# کپیِ تثبیت‌شده‌ی منطق هویت (app/utils/import_identity.py)
# ═════════════════════════════════════════════
_DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S")


def _iso_utc(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = None
            for fmt in _DATETIME_FORMATS:
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _identity_hash(
    source: Optional[str],
    external_ticket: Optional[str],
    symbol: Optional[str],
    open_time: Any,
    close_time: Any,
    trading_account_id: Optional[int],
    prop_stage_id: Optional[int],
    version_id: Optional[int],
    test_type: Optional[str],
) -> str:
    parts = [
        source or "",
        external_ticket or "",
        "" if trading_account_id is None else str(trading_account_id),
        "" if prop_stage_id is None else str(prop_stage_id),
        "" if version_id is None else str(version_id),
        (test_type or "").upper(),
        symbol or "",
        _iso_utc(open_time),
        _iso_utc(close_time),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _json_load(raw_data: Any) -> Any:
    if isinstance(raw_data, (dict, list)):
        return raw_data
    if isinstance(raw_data, str) and raw_data.strip():
        try:
            return json.loads(raw_data)
        except ValueError:
            return None
    return None


def _extract_ticket(raw_data: Any) -> Optional[str]:
    """برداشت شماره‌ی سفارش از raw_data (کلیدهای رایج MT4/Soft4X)."""
    data = _json_load(raw_data)
    if not isinstance(data, dict):
        return None
    for key, value in data.items():
        normalized = str(key).strip().lower()
        if normalized in ("position", "ticket", "order", "deal", "id") and value not in (None, ""):
            return str(value).strip()
    return None


# ═════════════════════════════════════════════
# Upgrade / Downgrade
# ═════════════════════════════════════════════
def upgrade() -> None:
    # ── ۱) ImportProfile ──
    op.create_table(
        "import_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("broker_id", sa.Integer(), nullable=True),
        sa.Column("source_format", sa.Enum("SOFT4X_XLSX", "MT4_HTML", name="importsourceformat"), nullable=False),
        sa.Column("symbol_mapping", sa.JSON(), nullable=True),
        sa.Column("column_mapping", sa.JSON(), nullable=True),
        sa.Column("default_context", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["broker_id"], ["brokers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_import_profiles_name"),
    )
    op.create_index(op.f("ix_import_profiles_id"), "import_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_import_profiles_broker_id"), "import_profiles", ["broker_id"], unique=False)

    # ── ۲) ImportBatch ──
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True),
                  server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("imported", sa.Integer(), nullable=True),
        sa.Column("duplicate", sa.Integer(), nullable=True),
        sa.Column("failed", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "COMMITTED", "FAILED", "CANCELLED", name="importstatus"),
                  nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["import_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_batches_status"), "import_batches", ["status"], unique=False)

    # ── ۳) ImportBatchRow (staging) ──
    op.create_table(
        "import_batch_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("NEW", "DUPLICATE", "POSSIBLE_DUPLICATE", "INVALID",
                                    name="importrowstatus"), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("external_ticket", sa.String(), nullable=True),
        sa.Column("identity_hash", sa.String(), nullable=False),
        sa.Column("matched_trade_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_batch_rows_batch_id"), "import_batch_rows", ["batch_id"], unique=False)
    op.create_index(op.f("ix_import_batch_rows_status"), "import_batch_rows", ["status"], unique=False)
    op.create_index(op.f("ix_import_batch_rows_identity_hash"), "import_batch_rows", ["identity_hash"], unique=False)

    # ── ۴) ImportIdentity ──
    op.create_table(
        "import_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trade_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("external_ticket", sa.String(), nullable=True),
        sa.Column("trading_account_id", sa.Integer(), nullable=True),
        sa.Column("prop_stage_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identity_hash", sa.String(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("version_id", sa.Integer(), nullable=True),
        sa.Column("test_type", sa.Enum("BACKTEST", "FORWARD", "REAL_PERSONAL", "REAL_PROP",
                                       name="testtype"), nullable=True),
        sa.Column("trade_hash", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.ForeignKeyConstraint(["trading_account_id"], ["personal_trading_accounts.id"]),
        sa.ForeignKeyConstraint(["prop_stage_id"], ["prop_stages.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["strategy_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_identities_trade_id"), "import_identities", ["trade_id"], unique=False)
    op.create_index(op.f("ix_import_identities_trading_account_id"), "import_identities",
                    ["trading_account_id"], unique=False)
    op.create_index(op.f("ix_import_identities_prop_stage_id"), "import_identities",
                    ["prop_stage_id"], unique=False)
    op.create_index(op.f("ix_import_identities_batch_id"), "import_identities", ["batch_id"], unique=False)
    op.create_index(op.f("ix_import_identities_version_id"), "import_identities", ["version_id"], unique=False)
    op.create_index(op.f("ix_import_identities_trade_hash"), "import_identities", ["trade_hash"], unique=False)
    op.create_index(op.f("ix_import_identities_identity_hash"), "import_identities",
                    ["identity_hash"], unique=True)

    # ── ۵) Backfill هویت برای معاملات موجود (شامل Soft-Deleted) ──
    _backfill_identities()


def _backfill_identities() -> None:
    """برای هر معامله‌ی موجود یک ImportIdentity می‌سازد.

    هویت‌های تکراری (ناسازگاری داده‌ی قدیمی) نادیده گرفته می‌شوند تا
    ایندکس یکتا شکسته نشود.
    """
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, source, symbol, open_time, close_time, personal_trading_account_id, "
        "       prop_stage_id, version_id, test_type, trade_hash, raw_data "
        "FROM trades"
    )).fetchall()

    seen = set()
    inserted = 0
    for (trade_id, source, symbol, open_time, close_time, pta_id, stage_id,
         version_id, test_type, trade_hash, raw_data) in rows:
        if not source or not symbol or open_time is None:
            continue
        ticket = _extract_ticket(raw_data)
        identity_hash = _identity_hash(
            source, ticket, symbol, open_time, close_time, pta_id, stage_id, version_id, test_type
        )
        if identity_hash in seen:
            continue
        seen.add(identity_hash)
        bind.execute(
            sa.text(
                "INSERT INTO import_identities "
                "(trade_id, source, external_ticket, trading_account_id, prop_stage_id, "
                " symbol, open_time, close_time, identity_hash, batch_id, version_id, "
                " test_type, trade_hash) "
                "VALUES (:trade_id, :source, :ticket, :pta, :stage, :symbol, :open_time, "
                "        :close_time, :hash, NULL, :version_id, :test_type, :trade_hash)"
            ),
            {
                "trade_id": trade_id,
                "source": source,
                "ticket": ticket,
                "pta": pta_id,
                "stage": stage_id,
                "symbol": symbol,
                "open_time": open_time,
                "close_time": close_time,
                "hash": identity_hash,
                "version_id": version_id,
                "test_type": test_type,
                "trade_hash": trade_hash,
            },
        )
        inserted += 1

    print(f"[phase30] backfilled import_identities: {inserted} rows")


def downgrade() -> None:
    op.drop_index(op.f("ix_import_identities_identity_hash"), table_name="import_identities")
    op.drop_index(op.f("ix_import_identities_trade_hash"), table_name="import_identities")
    op.drop_index(op.f("ix_import_identities_version_id"), table_name="import_identities")
    op.drop_index(op.f("ix_import_identities_batch_id"), table_name="import_identities")
    op.drop_index(op.f("ix_import_identities_prop_stage_id"), table_name="import_identities")
    op.drop_index(op.f("ix_import_identities_trading_account_id"), table_name="import_identities")
    op.drop_index(op.f("ix_import_identities_trade_id"), table_name="import_identities")
    op.drop_table("import_identities")

    op.drop_index(op.f("ix_import_batch_rows_identity_hash"), table_name="import_batch_rows")
    op.drop_index(op.f("ix_import_batch_rows_status"), table_name="import_batch_rows")
    op.drop_index(op.f("ix_import_batch_rows_batch_id"), table_name="import_batch_rows")
    op.drop_table("import_batch_rows")

    op.drop_index(op.f("ix_import_batches_status"), table_name="import_batches")
    op.drop_table("import_batches")

    op.drop_index(op.f("ix_import_profiles_broker_id"), table_name="import_profiles")
    op.drop_index(op.f("ix_import_profiles_id"), table_name="import_profiles")
    op.drop_table("import_profiles")



