"""
Domain: IMPORT — موتور ایمپورت (فاز ۳۰) + یکپارچگی تکرار (فاز ۳۱)

Pipeline:
    File ← Parse ← Normalize ← Validate ← Duplicate Detection ← Preview
         ← User Confirm ← Atomic Commit

جداول این دامنه:
- `ImportProfile`   : پروفایل ایمپورت (Broker / SourceFormat / Symbol+Column Mapping / Default Trade Context)
- `ImportBatch`     : سرشماری هر اجرای ایمپورت (total / imported / duplicate / failed / status)
- `ImportBatchRow`  : ردیف‌های staging شده‌ی همان اجرا (خروجی Preview، ورودی Commit)
- `ImportIdentity`  : هویت هر معامله‌ی واردشده برای Duplicate Detection

قوانین:
1. Import هرگز `FinancialAccount` نمی‌سازد (این دامنه هیچ ارتباطی با FINANCE ندارد).
2. Commit اتمیک است: خطای یک رکورد ⇒ هیچ رکوردی ذخیره نمی‌شود.
"""
import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .strategy import TestType


# ═════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════
class ImportSourceFormat(str, enum.Enum):
    """قالب منبع فایل ورودی."""
    SOFT4X_XLSX = "soft4x_xlsx"
    MT4_HTML = "mt4_html"


class ImportStatus(str, enum.Enum):
    """وضعیت یک ImportBatch.

    - PENDING   : Preview انجام شده و منتظر تأیید کاربر است.
    - COMMITTED : Commit اتمیک با موفقیت انجام شد.
    - FAILED    : Commit با خطا برگشت داده شد (هیچ رکوردی ذخیره نشد).
    - CANCELLED : کاربر Preview را کنار گذاشت.
    """
    PENDING = "pending"
    COMMITTED = "committed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportRowStatus(str, enum.Enum):
    """وضعیت یک ردیف در Preview (فاز ۳۱).

    - NEW                : رکورد جدید است.
    - DUPLICATE          : همان هویت قبلاً وارد شده (شامل حذف‌شده‌های نرم).
    - POSSIBLE_DUPLICATE : شباهت قوی ولی نه هویت کامل (نیاز به تصمیم کاربر).
    - INVALID            : نقض قرارداد معامله (مانع Commit اتمیک).
    """
    NEW = "new"
    DUPLICATE = "duplicate"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    INVALID = "invalid"


# ═════════════════════════════════════════════
# Models
# ═════════════════════════════════════════════
class ImportProfile(Base):
    """پروفایل ایمپورت (فاز ۳۰).

    یک پروفایل، همه‌ی «همیشه‌ثابت‌ها»ی یک بروکر/قالب را نگه می‌دارد تا کاربر
    هر بار آن‌ها را دستی وارد نکند:
    - `broker`           : بروکر منبع فایل (Broker)
    - `source_format`    : قالب فایل (Soft4X xlsx / MT4 html)
    - `symbol_mapping`   : {"GOLD": "XAUUSD", ...} — مقدم بر SymbolMapping دیتابیس
    - `column_mapping`   : {"open_time": "Time Open", ...} — هدر/ایندکس ستون‌ها
    - `default_context`  : {"test_type": "BACKTEST", "version_id": 3, ...}
    """
    __tablename__ = "import_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    broker_id = Column(Integer, ForeignKey("brokers.id"), nullable=True, index=True)
    source_format = Column(Enum(ImportSourceFormat), nullable=False)
    symbol_mapping = Column(JSON, nullable=True)
    column_mapping = Column(JSON, nullable=True)
    default_context = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    broker = relationship("Broker")

    __table_args__ = (
        UniqueConstraint("name", name="uq_import_profiles_name"),
    )


class ImportBatch(Base):
    """سرشماری یک اجرای ایمپورت (فاز ۳۰/۳۱).

    `context` (توسعه‌ی فاز ۳۰) اسنپ‌شات قرارداد معامله‌ی همان اجراست
    (test_type / version_id / prop_stage_id / personal_trading_account_id / symbol)
    تا Commit بدون ارسال دوباره‌ی پارامترها ممکن باشد.
    """
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total = Column(Integer, default=0)
    imported = Column(Integer, default=0)
    duplicate = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    status = Column(Enum(ImportStatus), default=ImportStatus.PENDING, index=True)
    user_id = Column(Integer, nullable=True)

    # ── توسعه‌های فاز ۳۰ ──
    profile_id = Column(Integer, ForeignKey("import_profiles.id"), nullable=True)
    context = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)

    rows = relationship(
        "ImportBatchRow",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="ImportBatchRow.row_number",
    )


class ImportBatchRow(Base):
    """ردیف staging شده‌ی یک ImportBatch (فاز ۳۰ — Preview → Confirm).

    خروجی مرحله‌ی Preview اینجاست؛ Commit فقط روی همین ردیف‌ها (پس از
    اعتبارسنجی مجدد) عمل می‌کند ⇒ نیازی به آپلود دوباره‌ی فایل نیست و
    شمارنده‌های batch قابل اتکا هستند.
    """
    __tablename__ = "import_batch_rows"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    status = Column(Enum(ImportRowStatus), default=ImportRowStatus.NEW, index=True)
    message = Column(String, nullable=True)
    external_ticket = Column(String, nullable=True)
    identity_hash = Column(String, nullable=False, index=True)
    # ارجاع نرم (بدون FK) به معامله‌ی متناظر در تشخیص تکرار/شباهت
    matched_trade_id = Column(Integer, nullable=True)
    payload = Column(JSON, nullable=False)

    batch = relationship("ImportBatch", back_populates="rows")


class ImportIdentity(Base):
    """هویت معامله‌ی واردشده (فاز ۳۱) — مبنای Duplicate Detection.

    هویت = `source + external_ticket + trading_account_id + symbol + open_time + close_time`
    به‌علاوهٔ «دامنه» (version_id / prop_stage_id / test_type) که برای انواع
    BACKTEST / FORWARD / REAL_PROP لازم است، چون `trading_account_id` ندارند
    (وگرنه یک فایل مشترک بین دو نسخه‌ی استراتژی اشتباهاً تکراری تشخیص داده می‌شد).

    نکته: رکوردهای معامله‌های Soft-Deleted هم در همین جدول می‌مانند تا
    re-import دوباره‌کاری نکند (قانون فاز ۳۱).
    """
    __tablename__ = "import_identities"

    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False, index=True)
    source = Column(String, nullable=False)
    external_ticket = Column(String, nullable=True)
    trading_account_id = Column(
        Integer, ForeignKey("personal_trading_accounts.id"), nullable=True, index=True
    )
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=True)
    identity_hash = Column(String, unique=True, nullable=False, index=True)

    # ── توسعه‌های فاز ۳۰/۳۱ ──
    batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True, index=True)
    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=True, index=True)
    test_type = Column(Enum(TestType), nullable=True)
    # همان hash قدیمی معامله (سازگاری با Trade.trade_hash و داده‌های legacy)
    trade_hash = Column(String(32), nullable=True, index=True)

    trade = relationship("Trade", back_populates="import_identities")



