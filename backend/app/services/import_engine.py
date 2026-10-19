"""
Import Engine (فاز ۳۰) + Duplicate Detection (فاز ۳۱)

Pipeline:
    File ← Parse ← Normalize ← Validate ← Duplicate Detection ← Preview
         ← User Confirm ← Atomic Commit

قوانین پیاده‌شده:
1. اعتبارسنجی بر اساس Trade Contract (فاز ۲۷) — `TradeValidator`.
   REAL_PERSONAL ⇒ PersonalTradingAccount، REAL_PROP ⇒ PropStage،
   BACKTEST/FORWARD ⇒ StrategyVersion و `version_id` برای همه اجباری.
2. Commit اتمیک: خطای یک رکورد ⇒ هیچ رکوردی ذخیره نمی‌شود (rollback + status=FAILED).
3. Preview قبل از Commit (ردیف‌ها در `import_batch_rows` staging می‌شوند).
4. ایمپورت هیچ‌گاه `FinancialAccount` نمی‌سازد (این ماژول به FINANCE وابسته نیست).
5. `ImportProfile` = Broker + SourceFormat + Symbol Mapping + Column Mapping + Default Context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..models.imports import (
    ImportBatch,
    ImportBatchRow,
    ImportIdentity,
    ImportProfile,
    ImportRowStatus,
    ImportSourceFormat,
    ImportStatus,
)
from ..models.prop import PropStage, StageStatus, StageType
from ..models.strategy import SymbolMapping, StrategyVersion, TestType, Trade, TradeSource
from ..models.trading import PersonalTradingAccount
from ..utils.import_identity import build_identity_hash, compute_trade_hash, normalize_utc
from ..utils.trade_metrics import calculate_r_multiple
from ..utils.trade_validator import TradeValidator


# ═════════════════════════════════════════════
# ثابت‌ها و نگاشت قالب‌ها
# ═════════════════════════════════════════════
SOURCE_BY_FORMAT: Dict[ImportSourceFormat, TradeSource] = {
    ImportSourceFormat.SOFT4X_XLSX: TradeSource.SOFT4X_IMPORT,
    ImportSourceFormat.MT4_HTML: TradeSource.MT4_IMPORT,
}

FORMAT_ALIASES: Dict[str, ImportSourceFormat] = {
    "soft4x": ImportSourceFormat.SOFT4X_XLSX,
    "soft4x_xlsx": ImportSourceFormat.SOFT4X_XLSX,
    "xlsx": ImportSourceFormat.SOFT4X_XLSX,
    "mt4": ImportSourceFormat.MT4_HTML,
    "mt4_html": ImportSourceFormat.MT4_HTML,
    "html": ImportSourceFormat.MT4_HTML,
}

# فیلدهای کانونیکال قابل نگاشت در Column Mapping (Soft4X)
MAPPABLE_COLUMNS = (
    "open_time", "close_time", "type", "open_price", "close_price",
    "size", "sl", "tp", "pnl", "commission", "external_ticket",
)

# کلیدهای رایج شماره‌ی سفارش در raw_data
TICKET_KEYS = ("position", "ticket", "order", "deal", "id")


# ═════════════════════════════════════════════
# خطای دامنه
# ═════════════════════════════════════════════
class ImportEngineError(Exception):
    """خطای Import Engine با کد HTTP پیشنهادی و ردیف‌های مانع.

    - `detail`          : پیام فارسی برای کاربر
    - `status_code`     : کد HTTP (400 / 404 / 409 / 500)
    - `blocking_rows`   : ردیف‌هایی که مانع Commit شدند (برای نمایش در UI)
    """

    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        blocking_rows: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.blocking_rows = blocking_rows or []


# ═════════════════════════════════════════════
# ImportContext — قرارداد معامله‌ی یک اجرای ایمپورت
# ═════════════════════════════════════════════
@dataclass
class ImportContext:
    test_type: TestType
    version_id: Optional[int] = None
    prop_stage_id: Optional[int] = None
    personal_trading_account_id: Optional[int] = None
    symbol: Optional[str] = None
    source_format: Optional[ImportSourceFormat] = None
    profile_id: Optional[int] = None
    # فاز ۴۶.۲: اختلاف ساعت سرور مقصد با UTC (دقیقه) برای تفسیر زمان‌های بدون tz
    server_utc_offset_minutes: int = 0
    column_mapping: Dict[str, Any] = field(default_factory=dict)
    symbol_mapping: Dict[str, str] = field(default_factory=dict)

    @property
    def expected_source(self) -> TradeSource:
        return SOURCE_BY_FORMAT[self.source_format]

    def to_json(self) -> Dict[str, Any]:
        return {
            "test_type": self.test_type.name,
            "version_id": self.version_id,
            "prop_stage_id": self.prop_stage_id,
            "personal_trading_account_id": self.personal_trading_account_id,
            "symbol": self.symbol,
            "source_format": self.source_format.value if self.source_format else None,
            "profile_id": self.profile_id,
            "server_utc_offset_minutes": self.server_utc_offset_minutes,
            "column_mapping": self.column_mapping or {},
            "symbol_mapping": self.symbol_mapping or {},
        }

    @classmethod
    def from_json(cls, data: Optional[Dict[str, Any]]) -> "ImportContext":
        data = data or {}
        test_type = _test_type_from_json(data.get("test_type"))
        fmt = data.get("source_format")
        return cls(
            test_type=test_type,
            version_id=data.get("version_id"),
            prop_stage_id=data.get("prop_stage_id"),
            personal_trading_account_id=data.get("personal_trading_account_id"),
            symbol=data.get("symbol"),
            source_format=ImportSourceFormat(fmt) if fmt else None,
            profile_id=data.get("profile_id"),
            server_utc_offset_minutes=int(data.get("server_utc_offset_minutes") or 0),
            column_mapping=data.get("column_mapping") or {},
            symbol_mapping=data.get("symbol_mapping") or {},
        )


# ═════════════════════════════════════════════
# Normalization — قالب/نوع تست/اعداد/زمان
# ═════════════════════════════════════════════
def normalize_source_format(value: Any) -> ImportSourceFormat:
    """رشته/Enum قالب فایل → ImportSourceFormat (با پذیرش نام‌های قدیمی)."""
    if isinstance(value, ImportSourceFormat):
        return value
    key = str(value or "").strip().lower()
    if key in FORMAT_ALIASES:
        return FORMAT_ALIASES[key]
    raise ImportEngineError(f"قالب فایل پشتیبانی نمی‌شود: {value}")


def normalize_test_type(
    value: Any,
    *,
    prop_stage_id: Optional[int] = None,
    personal_trading_account_id: Optional[int] = None,
) -> TestType:
    """رشته/Enum نوع تست → TestType (طبق Trade Contract فاز ۲۷).

    مقدار قدیمی `real` (که UI فاز قبل می‌فرستد) نگاشت می‌شود:
    با prop_stage_id ⇒ REAL_PROP، وگرنه با حساب معاملاتی ⇒ REAL_PERSONAL.
    """
    if isinstance(value, TestType):
        return value
    key = str(value or "").strip().lower()
    mapping = {
        "backtest": TestType.BACKTEST,
        "forward": TestType.FORWARD,
        "real_personal": TestType.REAL_PERSONAL,
        "real_prop": TestType.REAL_PROP,
    }
    if key in mapping:
        return mapping[key]
    if key == "real":
        if prop_stage_id:
            return TestType.REAL_PROP
        if personal_trading_account_id:
            return TestType.REAL_PERSONAL
        return TestType.REAL_PROP
    raise ImportEngineError(f"نوع تست نامعتبر: {value}")


def _test_type_from_json(value: Any) -> TestType:
    """نام enum ذخیره‌شده در context (مثل BACKTEST) → TestType."""
    if value is None:
        return TestType.BACKTEST
    if isinstance(value, TestType):
        return value
    try:
        return TestType[str(value).strip().upper()]
    except KeyError:
        return normalize_test_type(value)


def _to_float(value: Any) -> Optional[float]:
    """تبدیل امن به float (با پذیرش رشته‌های دارای کاما/فاصله)."""
    if value is None or value == "" or value == "-":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace(" ", "")
    if text in ("", "-", "N/A", "NA", "None"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    return int(number) if number is not None else None


def _normalize_direction(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("buy", "long"):
        return "buy"
    if text in ("sell", "short"):
        return "sell"
    return text or None


def json_safe(value: Any) -> Any:
    """تبدیل مقادیر غیرقابل‌ذخیره در JSON (datetime/jdatetime/Enum) به متن."""
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return json_safe(value.value)
    return str(value)


def extract_external_ticket(
    raw_data: Optional[Dict[str, Any]],
    column_mapping: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """شماره‌ی سفارش از raw_data (MT4: position / Soft4X: نگاشت‌شده یا هدر رایج)."""
    if not isinstance(raw_data, dict):
        return None

    mapped = (column_mapping or {}).get("external_ticket")
    if mapped is not None and not isinstance(mapped, int):
        target = str(mapped).strip().lower()
        for key, value in raw_data.items():
            if str(key).strip().lower() == target and value not in (None, ""):
                return str(value).strip()

    for key, value in raw_data.items():
        if str(key).strip().lower() in TICKET_KEYS and value not in (None, ""):
            return str(value).strip()
    return None


def _normalize_symbol(symbol: Any, symbol_mapping: Optional[Dict[str, str]]) -> Optional[str]:
    """اعمال Symbol Mapping (اول نگاشت پروفایل/درخواست، سپس SymbolMapping دیتابیس)."""
    if symbol is None:
        return None
    text = str(symbol).strip()
    if not text:
        return None
    mapping = symbol_mapping or {}
    if text in mapping:
        return str(mapping[text]).strip()
    upper_map = {str(k).strip().upper(): v for k, v in mapping.items()}
    return str(upper_map.get(text.upper(), text)).strip()


def _source_name(value: Any) -> str:
    """نام enum منبع (مثل SOFT4X_IMPORT) — مبنای هویت و ImportBatch.source."""
    return getattr(value, "name", None) or str(value or "")


def _enum_by_name(enum_cls, name: Any):
    """بازگرداندن عضو Enum از نام ذخیره‌شده در JSON."""
    if name is None:
        return None
    if isinstance(name, enum_cls):
        return name
    try:
        return enum_cls[str(name).strip().upper()]
    except KeyError:
        pass
    try:
        return enum_cls(str(name).strip().lower())
    except ValueError:
        return None


# ═════════════════════════════════════════════
# Normalize + Validate + Identity
# ═════════════════════════════════════════════
@dataclass
class StagedTrade:
    """ردیف نرمال‌شده + هویت آن (ورودی ذخیره‌سازی)."""
    trade: Dict[str, Any]
    source_name: str
    external_ticket: Optional[str]
    trade_hash: str
    identity_hash: str


def normalize_trade(raw: Dict[str, Any], ctx: ImportContext) -> Dict[str, Any]:
    """مرحله Normalize — ردیف خام پارسر → kwargs آماده‌ی `Trade`."""
    if not isinstance(raw, dict):
        raise ImportEngineError("ساختار ردیف ورودی نامعتبر است")

    raw_data = json_safe(raw.get("raw_data") or {})
    source = raw.get("source") or ctx.expected_source
    direction = _normalize_direction(raw.get("direction"))
    # فاز ۴۶.۲: زمان‌های بدون tz به‌عنوان ساعت سرور مقصد تفسیر می‌شوند
    offset = ctx.server_utc_offset_minutes or 0
    open_time = normalize_utc(raw.get("open_time"), offset)
    close_time = normalize_utc(raw.get("close_time"), offset)
    open_price = _to_float(raw.get("open_price"))
    close_price = _to_float(raw.get("close_price"))
    size = _to_float(raw.get("size"))
    sl = _to_float(raw.get("sl"))
    tp = _to_float(raw.get("tp"))
    pnl = _to_float(raw.get("pnl"))
    commission = _to_float(raw.get("commission"))
    swap = _to_float(raw.get("swap"))
    r_multiple = _to_float(raw.get("r_multiple"))

    # فاز ۴: استاپ اولیه — اولویت: raw.initial_sl > raw_data.initial_sl > sl
    initial_sl = _to_float(raw.get("initial_sl"))
    if initial_sl is None and isinstance(raw_data, dict):
        initial_sl = _to_float(raw_data.get("initial_sl"))
    if initial_sl is None:
        initial_sl = sl

    if r_multiple is None:
        r_multiple = calculate_r_multiple(direction or "", open_price, close_price, sl, initial_sl)

    return {
        "version_id": ctx.version_id,
        "prop_stage_id": ctx.prop_stage_id,
        "personal_trading_account_id": ctx.personal_trading_account_id,
        "symbol": _normalize_symbol(raw.get("symbol") or ctx.symbol, ctx.symbol_mapping),
        "direction": direction,
        "open_time": open_time,
        "close_time": close_time,
        "open_price": open_price,
        "close_price": close_price,
        "size": size,
        "sl": sl,
        "initial_sl": initial_sl,
        "tp": tp,
        "pnl": pnl,
        "r_multiple": r_multiple,
        "commission": commission if commission is not None else 0.0,
        "swap": swap if swap is not None else 0.0,
        "entry_sequence": _to_int(raw.get("entry_sequence")) or 1,
        "source": source,
        "test_type": ctx.test_type,
        "raw_data": raw_data,
    }


def validate_trade(trade: Dict[str, Any]) -> Optional[str]:
    """مرحله Validate در سطح یک رکورد — پیام خطا یا None."""
    if not trade.get("symbol"):
        return "نماد معامله الزامی است"
    if trade.get("direction") not in ("buy", "sell"):
        return "جهت معامله باید buy یا sell باشد"
    open_time = trade.get("open_time")
    if open_time is None:
        return "زمان باز شدن معامله الزامی است"
    close_time = trade.get("close_time")
    if close_time is None:
        return "زمان بسته شدن معامله الزامی است"
    if close_time < open_time:
        return "زمان بسته شدن نمی‌تواند قبل از باز شدن باشد"
    if trade.get("open_price") is None:
        return "قیمت ورود الزامی است"
    if trade.get("size") is None:
        return "حجم معامله الزامی است"

    ok, error = TradeValidator.validate_numbers(
        size=trade.get("size"),
        open_price=trade.get("open_price"),
        close_price=trade.get("close_price"),
        sl=trade.get("sl"),
        tp=trade.get("tp"),
        r_multiple=trade.get("r_multiple"),
        commission=trade.get("commission"),
        swap=trade.get("swap"),
    )
    if not ok:
        return error
    return None


def build_staged_trade(raw: Dict[str, Any], ctx: ImportContext) -> StagedTrade:
    """Normalize + محاسبه‌ی هویت (فاز ۳۱)."""
    trade = normalize_trade(raw, ctx)
    source_name = _source_name(trade.get("source"))
    ticket = extract_external_ticket(trade.get("raw_data"), ctx.column_mapping)
    # `trade_hash` طبق فرمول قدیمی و از مقادیر خام پارسر محاسبه می‌شود تا با
    # hash رکوردهای قبلی دیتابیس یکسان بماند (سازگاری با داده‌های legacy).
    trade_hash = compute_trade_hash({**raw, "source": trade.get("source")})
    identity_hash = build_identity_hash(
        source=source_name,
        external_ticket=ticket,
        symbol=trade.get("symbol"),
        open_time=trade.get("open_time"),
        close_time=trade.get("close_time"),
        trading_account_id=trade.get("personal_trading_account_id"),
        prop_stage_id=trade.get("prop_stage_id"),
        version_id=trade.get("version_id"),
        test_type=trade.get("test_type"),
    )
    return StagedTrade(
        trade=trade,
        source_name=source_name,
        external_ticket=ticket,
        trade_hash=trade_hash,
        identity_hash=identity_hash,
    )


def stage_payload(staged: StagedTrade) -> Dict[str, Any]:
    """StagedTrade → payload JSON برای ذخیره در `import_batch_rows`."""
    return {
        "trade": {key: json_safe(value) for key, value in staged.trade.items()},
        "source": staged.source_name,
        "external_ticket": staged.external_ticket,
        "trade_hash": staged.trade_hash,
        "identity_hash": staged.identity_hash,
    }


def destage_payload(payload: Dict[str, Any]) -> StagedTrade:
    """payload JSON → StagedTrade (زمان‌ها UTC-aware و Enumها بازگردانی می‌شوند)."""
    data = dict(payload.get("trade") or {})
    data["open_time"] = normalize_utc(data.get("open_time"))
    data["close_time"] = normalize_utc(data.get("close_time"))
    data["source"] = _enum_by_name(TradeSource, data.get("source"))
    data["test_type"] = _enum_by_name(TestType, data.get("test_type"))
    return StagedTrade(
        trade=data,
        source_name=payload.get("source") or _source_name(data.get("source")),
        external_ticket=payload.get("external_ticket"),
        trade_hash=payload.get("trade_hash"),
        identity_hash=payload.get("identity_hash"),
    )


# ═════════════════════════════════════════════
# Parse — استفاده از پارسرهای موجود (Soft4X/MT4)
# ═════════════════════════════════════════════
def parse_source(
    db: Optional[Session],
    source_format: ImportSourceFormat,
    *,
    file_path: Optional[str] = None,
    html_content: Optional[str] = None,
    symbol: Optional[str] = None,
    test_type: TestType = TestType.BACKTEST,
    column_mapping: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """مرحله Parse — پارسرهای فاز قبل (Soft4X xlsx / MT4 html) بازاستفاده می‌شوند."""
    from .import_service import MT4Importer, Soft4XImporter

    if source_format == ImportSourceFormat.SOFT4X_XLSX:
        if not file_path:
            raise ImportEngineError("مسیر فایل اکسل مشخص نشده است")
        importer = Soft4XImporter(db, symbol=symbol or "XAUUSD", test_type=test_type.value)
        return importer.parse_file(file_path, column_mapping=column_mapping)

    if source_format == ImportSourceFormat.MT4_HTML:
        if html_content is None:
            raise ImportEngineError("محتوای فایل HTML مشخص نشده است")
        importer = MT4Importer(db, test_type=test_type.value)
        return importer.parse_html(html_content)

    raise ImportEngineError("قالب فایل پشتیبانی نمی‌شود")


# ═════════════════════════════════════════════
# Context — ساخت و اعتبارسنجی
# ═════════════════════════════════════════════
def _resolve_server_offset(
    db: Session, prop_stage_id, personal_trading_account_id
) -> int:
    """فاز ۴۶.۲ — اختلاف ساعت سرور مقصد با UTC (دقیقه).

    - مرحله پراپ ⇒ `PropAccount.server_utc_offset_minutes`
    - حساب معاملاتی شخصی ⇒ `Broker.server_utc_offset_minutes`
    """
    if prop_stage_id:
        stage = db.query(PropStage).filter(PropStage.id == prop_stage_id).first()
        account = stage.account if stage else None
        if account is not None:
            return int(account.server_utc_offset_minutes or 0)
    if personal_trading_account_id:
        acc = (
            db.query(PersonalTradingAccount)
            .filter(PersonalTradingAccount.id == personal_trading_account_id)
            .first()
        )
        broker = acc.broker if acc else None
        if broker is not None:
            return int(broker.server_utc_offset_minutes or 0)
    return 0


def build_context(
    db: Session,
    *,
    source_format: Any = None,
    test_type: Any = None,
    version_id: Optional[int] = None,
    prop_stage_id: Optional[int] = None,
    personal_trading_account_id: Optional[int] = None,
    symbol: Optional[str] = None,
    profile_id: Optional[int] = None,
    column_mapping: Optional[Dict[str, Any]] = None,
    symbol_mapping: Optional[Dict[str, str]] = None,
    source_utc_offset_minutes: Optional[int] = None,
) -> ImportContext:
    """ساخت ImportContext با اعمال مقادیر پیش‌فرض ImportProfile."""
    profile: Optional[ImportProfile] = None
    if profile_id:
        profile = db.query(ImportProfile).filter(ImportProfile.id == profile_id).first()
        if not profile:
            raise ImportEngineError("پروفایل ایمپورت پیدا نشد", 404)

    defaults: Dict[str, Any] = (profile.default_context or {}) if profile else {}

    fmt_value = source_format or (profile.source_format.value if profile else None)
    if not fmt_value:
        raise ImportEngineError("قالب فایل (source_format) مشخص نشده است")
    fmt = normalize_source_format(fmt_value)

    resolved_version = version_id if version_id is not None else defaults.get("version_id")
    resolved_stage = prop_stage_id if prop_stage_id is not None else defaults.get("prop_stage_id")
    resolved_account = (
        personal_trading_account_id
        if personal_trading_account_id is not None
        else defaults.get("personal_trading_account_id")
    )
    resolved_symbol = symbol or defaults.get("symbol")
    if not resolved_symbol and fmt == ImportSourceFormat.SOFT4X_XLSX:
        resolved_symbol = "XAUUSD"

    resolved_test_type = normalize_test_type(
        test_type if test_type is not None else defaults.get("test_type", "backtest"),
        prop_stage_id=_to_int(resolved_stage),
        personal_trading_account_id=_to_int(resolved_account),
    )

    merged_columns = {
        **((profile.column_mapping or {}) if profile else {}),
        **(column_mapping or {}),
    }
    # ── فاز ۶۰.۲: Symbol Mapping از دیتابیس (پایه) + پروفایل + درخواست ──
    # لایه‌ها به ترتیب اولویت: ۱) درخواست کاربر  ۲) پروفایل  ۳) دیتابیس
    db_mappings: Dict[str, str] = {}
    for m in db.query(SymbolMapping).all():
        db_mappings[m.original_symbol] = m.canonical_symbol
    merged_symbols = {
        **db_mappings,
        **((profile.symbol_mapping or {}) if profile else {}),
        **(symbol_mapping or {}),
    }

    return ImportContext(
        test_type=resolved_test_type,
        version_id=_to_int(resolved_version),
        prop_stage_id=_to_int(resolved_stage),
        personal_trading_account_id=_to_int(resolved_account),
        symbol=resolved_symbol,
        source_format=fmt,
        profile_id=profile.id if profile else None,
        server_utc_offset_minutes=(
            source_utc_offset_minutes
            if source_utc_offset_minutes is not None
            else _resolve_server_offset(
                db, _to_int(resolved_stage), _to_int(resolved_account)
            )
        ),
        column_mapping=merged_columns,
        symbol_mapping=merged_symbols,
    )


def validate_contract(ctx: ImportContext) -> None:
    """مرحله Validate قرارداد معامله (بدون بررسی وجود مقصدها).

    جدا نگه داشته شده تا مسیرهای قدیمی بتوانند قبل از Parse همین بررسی را
    انجام دهند و پیام خطای دقیق قرارداد را برگردانند.
    """
    ok, error = TradeValidator.validate_classification(
        test_type=ctx.test_type.value,
        version_id=ctx.version_id,
        personal_trading_account_id=ctx.personal_trading_account_id,
        prop_stage_id=ctx.prop_stage_id,
    )
    if not ok:
        raise ImportEngineError(error or "قرارداد معامله نقض شده است", 400)


def validate_context(db: Session, ctx: ImportContext) -> None:
    """مرحله Validate در سطح دسته — Trade Contract + وجود مقصدها."""
    validate_contract(ctx)

    version = db.query(StrategyVersion).filter(StrategyVersion.id == ctx.version_id).first()
    if not version:
        raise ImportEngineError("نسخه استراتژی پیدا نشد", 404)

    if ctx.prop_stage_id:
        stage = db.query(PropStage).filter(PropStage.id == ctx.prop_stage_id).first()
        if not stage:
            raise ImportEngineError("مرحله پراپ پیدا نشد", 404)

    if ctx.personal_trading_account_id:
        account = (
            db.query(PersonalTradingAccount)
            .filter(PersonalTradingAccount.id == ctx.personal_trading_account_id)
            .first()
        )
        if not account:
            raise ImportEngineError("حساب معاملاتی شخصی پیدا نشد", 404)


# ═════════════════════════════════════════════
# Duplicate Detection (فاز ۳۱)
# ═════════════════════════════════════════════
def _nullable_eq(column, value):
    """مقایسه‌ی NULL-safe (برای ستون‌های دامنه که ممکن است NULL باشند)."""
    if value is None:
        return column.is_(None)
    return column == value


def _scope_filter(model, ctx: ImportContext):
    """شرط «همان دامنه‌ی معاملاتی» (نسخه / مرحله / حساب / نوع تست).

    توجه: نام ستون حساب معاملاتی در `Trade` و `ImportIdentity` متفاوت است
    (`personal_trading_account_id` در برابر `trading_account_id`).
    """
    account_column = (
        model.personal_trading_account_id
        if hasattr(model, "personal_trading_account_id")
        else model.trading_account_id
    )
    return and_(
        _nullable_eq(model.version_id, ctx.version_id),
        _nullable_eq(model.prop_stage_id, ctx.prop_stage_id),
        _nullable_eq(account_column, ctx.personal_trading_account_id),
        _nullable_eq(model.test_type, ctx.test_type),
    )


def classify_duplicate(
    db: Session,
    staged: StagedTrade,
    ctx: ImportContext,
    seen: Optional[Dict[str, int]] = None,
) -> Tuple[ImportRowStatus, Optional[str], Optional[int]]:
    """تشخیص تکرار با identity hash، legacy hash و بررسی شباهت احتمالی.

    هویت‌های معاملات موجود و رکوردهای فعال بررسی می‌شوند. پس از Hard Delete
    هویت هم حذف می‌شود تا re-import همان منبع یک معامله‌ی تازه بسازد.
    """
    if seen and staged.identity_hash in seen:
        return (
            ImportRowStatus.DUPLICATE,
            f"تکراری در همان فایل (ردیف {seen[staged.identity_hash]})",
            None,
        )

    identity = (
        db.query(ImportIdentity)
        .filter(ImportIdentity.identity_hash == staged.identity_hash)
        .first()
    )
    if identity:
        trade = db.query(Trade).filter(Trade.id == identity.trade_id).first()
        if trade is not None:
            return (
                ImportRowStatus.DUPLICATE,
                f"این معامله قبلاً وارد شده است (شناسه {identity.trade_id})",
                identity.trade_id,
            )

    if staged.trade_hash:
        legacy = db.query(Trade).filter(Trade.trade_hash == staged.trade_hash).first()
        if legacy:
            return (
                ImportRowStatus.DUPLICATE,
                f"معامله‌ی هم‌ارز قبلاً ثبت شده است (شناسه {legacy.id})",
                legacy.id,
            )

    if staged.external_ticket:
        match = (
            db.query(ImportIdentity)
            .filter(
                ImportIdentity.source == staged.source_name,
                ImportIdentity.external_ticket == staged.external_ticket,
                _scope_filter(ImportIdentity, ctx),
            )
            .first()
        )
        if match:
            return (
                ImportRowStatus.POSSIBLE_DUPLICATE,
                f"شماره‌ی سفارش {staged.external_ticket} قبلاً با مشخصات دیگری وارد شده است "
                f"(شناسه {match.trade_id})",
                match.trade_id,
            )

    symbol = staged.trade.get("symbol")
    open_time = staged.trade.get("open_time")
    if symbol and open_time is not None:
        match = (
            db.query(Trade)
            .filter(Trade.symbol == symbol, Trade.open_time == open_time, _scope_filter(Trade, ctx))
            .first()
        )
        if match:
            return (
                ImportRowStatus.POSSIBLE_DUPLICATE,
                f"معامله‌ای با همین نماد و زمان ورود از قبل ثبت شده است (شناسه {match.id})",
                match.id,
            )

    return ImportRowStatus.NEW, None, None


# ═════════════════════════════════════════════
# Serializers
# ═════════════════════════════════════════════
def serialize_row(row: ImportBatchRow) -> Dict[str, Any]:
    trade = (row.payload or {}).get("trade") or {}
    return {
        "id": row.id,
        "row_number": row.row_number,
        "status": row.status.value if row.status else None,
        "message": row.message,
        "external_ticket": row.external_ticket,
        "identity_hash": row.identity_hash,
        "matched_trade_id": row.matched_trade_id,
        "symbol": trade.get("symbol"),
        "direction": trade.get("direction"),
        "open_time": trade.get("open_time"),
        "close_time": trade.get("close_time"),
        "size": trade.get("size"),
        "pnl": trade.get("pnl"),
    }


def serialize_batch(
    batch: ImportBatch,
    *,
    include_rows: bool = False,
    rows_limit: int = 50,
) -> Dict[str, Any]:
    """خروجی JSON یک ImportBatch (+ شمارنده‌های تفکیکی وضعیت ردیف‌ها)."""
    rows = sorted(batch.rows or [], key=lambda row: row.row_number)
    counts = {status.value: 0 for status in ImportRowStatus}
    for row in rows:
        if row.status is not None:
            counts[row.status.value] = counts.get(row.status.value, 0) + 1

    data: Dict[str, Any] = {
        "batch_id": batch.id,
        "source": batch.source,
        "file_name": batch.file_name,
        "status": batch.status.value if batch.status else None,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "total": batch.total or 0,
        "imported": batch.imported or 0,
        "duplicate": batch.duplicate or 0,
        "failed": batch.failed or 0,
        "profile_id": batch.profile_id,
        "user_id": batch.user_id,
        "context": batch.context,
        "message": batch.message,
        "counts": counts,
        "blocking": counts.get(ImportRowStatus.INVALID.value, 0) > 0
        or counts.get(ImportRowStatus.POSSIBLE_DUPLICATE.value, 0) > 0,
    }
    if include_rows:
        data["rows"] = [serialize_row(row) for row in rows[:rows_limit]]
        data["rows_total"] = len(rows)
    return data


def sync_prop_stage_profit(db: Session, prop_stage_id: int) -> None:
    """بازمحاسبه سود مرحله پراپ از معاملات بسته؛ مراحل غیرفعال فریز می‌مانند."""
    stage = db.get(PropStage, prop_stage_id)
    if stage is None:
        return

    # فاز ۵: فقط مراحل فعال به‌روزرسانی می‌شوند (تاریخچهٔ مراحل پاس‌شده فریز می‌ماند)
    if stage.status != StageStatus.ACTIVE:
        return

    total_pnl = float(
        db.query(
            func.coalesce(
                func.sum(
                    func.coalesce(Trade.pnl, 0)
                    + func.coalesce(Trade.commission, 0)
                    + func.coalesce(Trade.swap, 0)
                ),
                0.0,
            )
        )
        .filter(
            Trade.prop_stage_id == prop_stage_id,
            Trade.close_time.isnot(None),
        )
        .scalar()
        or 0.0
    )

    if stage.stage_type == StageType.FUNDED_REAL:
        percentage = stage.profit_share_percentage
        if percentage is None:
            percentage = 80.0
        share = float(percentage) / 100.0
        stage.current_profit = total_pnl * share
    else:
        stage.current_profit = total_pnl

    db.commit()


# ═════════════════════════════════════════════
# ImportEngine
# ═════════════════════════════════════════════
class ImportEngine:
    """موتور ایمپورت: Preview (staging) → تأیید کاربر → Commit اتمیک."""

    def __init__(self, db: Session):
        self.db = db

    # ── خواندن ──
    def get_batch(self, batch_id: int) -> ImportBatch:
        batch = self.db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            raise ImportEngineError("Import پیدا نشد", 404)
        return batch

    def list_batches(
        self,
        *,
        limit: int = 20,
        status: Optional[ImportStatus] = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(ImportBatch)
        if status is not None:
            query = query.filter(ImportBatch.status == status)
        batches = query.order_by(ImportBatch.id.desc()).limit(limit).all()
        return [serialize_batch(batch) for batch in batches]

    # ── مرحله‌ی Preview ──
    def create_preview(
        self,
        *,
        ctx: ImportContext,
        raw_rows: List[Dict[str, Any]],
        file_name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[ImportBatch, Dict[str, Any]]:
        """Parse قبلاً انجام شده؛ این‌جا Normalize + Validate + Duplicate + staging."""
        validate_context(self.db, ctx)
        if not raw_rows:
            raise ImportEngineError("هیچ معامله‌ای در فایل یافت نشد", 400)

        # Open positions / rows without a close timestamp are not trades for
        # this import flow. Reject before creating either the batch or staged rows.
        missing_close_rows = [
            index
            for index, raw in enumerate(raw_rows, start=1)
            if not isinstance(raw, dict)
            or normalize_utc(
                raw.get("close_time"), ctx.server_utc_offset_minutes or 0
            ) is None
        ]
        if missing_close_rows:
            first = missing_close_rows[0]
            raise ImportEngineError(
                f"ردیف {first}: زمان بسته شدن معامله الزامی است؛ هیچ ردیفی staging نشد",
                400,
            )

        batch = ImportBatch(
            source=ctx.expected_source.name,
            file_name=file_name,
            status=ImportStatus.PENDING,
            total=len(raw_rows),
            imported=0,
            duplicate=0,
            failed=0,
            user_id=user_id,
            profile_id=ctx.profile_id,
            context=ctx.to_json(),
            message="در انتظار تأیید کاربر",
        )
        self.db.add(batch)
        self.db.flush()

        seen: Dict[str, int] = {}
        counts = {status: 0 for status in ImportRowStatus}

        for index, raw in enumerate(raw_rows, start=1):
            staged = build_staged_trade(raw, ctx)
            error = validate_trade(staged.trade)
            if error:
                status, message, matched = ImportRowStatus.INVALID, error, None
            else:
                status, message, matched = classify_duplicate(self.db, staged, ctx, seen)

            self.db.add(
                ImportBatchRow(
                    batch_id=batch.id,
                    row_number=index,
                    status=status,
                    message=message,
                    external_ticket=staged.external_ticket,
                    identity_hash=staged.identity_hash,
                    matched_trade_id=matched,
                    payload=stage_payload(staged),
                )
            )
            if status != ImportRowStatus.INVALID:
                seen[staged.identity_hash] = index
            counts[status] += 1

        batch.duplicate = counts[ImportRowStatus.DUPLICATE] + counts[ImportRowStatus.POSSIBLE_DUPLICATE]
        batch.failed = counts[ImportRowStatus.INVALID]
        self.db.commit()
        self.db.refresh(batch)
        return batch, serialize_batch(batch, include_rows=True)

    # ── مرحله‌ی Commit (اتمیک) ──
    def commit(
        self,
        batch_id: int,
        *,
        allow_possible_duplicates: bool = False,
    ) -> Dict[str, Any]:
        """ذخیره‌ی ردیف‌های staging‌شده در یک تراکنش.

        خطای یک رکورد ⇒ rollback کامل (هیچ رکوردی ذخیره نمی‌شود) و
        `status=FAILED` روی همان batch.
        """
        batch = self.get_batch(batch_id)
        if batch.status == ImportStatus.COMMITTED:
            raise ImportEngineError("این Import قبلاً تأیید و ذخیره شده است", 409)
        if batch.status == ImportStatus.CANCELLED:
            raise ImportEngineError("این Import لغو شده است؛ Preview جدید بگیرید", 409)

        ctx = ImportContext.from_json(batch.context)
        validate_context(self.db, ctx)

        rows = sorted(batch.rows or [], key=lambda row: row.row_number)
        if not rows:
            raise ImportEngineError("این Import هیچ ردیفی برای ذخیره ندارد", 409)

        # ── مرحله ۱: تعیین سرنوشت هر ردیف (Re-validate + Re-classify) ──
        plan, skipped, blocking = self._plan_commit(rows, ctx, allow_possible_duplicates)
        if blocking:
            self.db.commit()
            raise self._blocking_error(blocking)

        # ── مرحله ۲: درج اتمیک (همه یا هیچ) ──
        created_ids: List[int] = []
        try:
            for row, staged in plan:
                trade = self._create_trade(staged.trade)
                self.db.add(trade)
                self.db.flush()

                self.db.add(
                    ImportIdentity(
                        trade_id=trade.id,
                        source=staged.source_name,
                        external_ticket=staged.external_ticket,
                        trading_account_id=trade.personal_trading_account_id,
                        prop_stage_id=trade.prop_stage_id,
                        symbol=trade.symbol,
                        open_time=trade.open_time,
                        close_time=trade.close_time,
                        identity_hash=staged.identity_hash,
                        batch_id=batch.id,
                        version_id=trade.version_id,
                        test_type=trade.test_type,
                        trade_hash=staged.trade_hash,
                    )
                )
                self.db.flush()

                row.matched_trade_id = trade.id
                created_ids.append(trade.id)

            batch.imported = len(created_ids)
            batch.duplicate = len(skipped)
            batch.failed = 0
            batch.status = ImportStatus.COMMITTED
            batch.completed_at = datetime.now(timezone.utc)
            batch.message = self._success_message(len(created_ids), len(skipped))
            self.db.commit()
        except Exception as exc:  # noqa: BLE001 — هر خطایی ⇒ Import ناقص ممنوع
            self.db.rollback()
            self._mark_failed(batch_id, str(exc))
            raise ImportEngineError(
                f"Commit با خطا برگشت خورد؛ هیچ رکوردی ذخیره نشد: {exc}",
                500,
            )

        if ctx.prop_stage_id:
            sync_prop_stage_profit(self.db, ctx.prop_stage_id)

        result = serialize_batch(self.get_batch(batch_id))
        result["trade_ids"] = created_ids
        result["skipped_rows"] = skipped
        result["allow_possible_duplicates"] = allow_possible_duplicates
        return result

    # ── لغو Preview ──
    def cancel(self, batch_id: int) -> Dict[str, Any]:
        batch = self.get_batch(batch_id)
        if batch.status != ImportStatus.PENDING:
            raise ImportEngineError("فقط Import در انتظار تأیید قابل لغو است", 409)
        batch.status = ImportStatus.CANCELLED
        batch.completed_at = datetime.now(timezone.utc)
        batch.message = "توسط کاربر لغو شد"
        self.db.commit()
        return serialize_batch(batch)

    # ── مسیر یک‌مرحله‌ای (سازگاری با endpointهای قدیمی) ──
    def import_rows(
        self,
        *,
        ctx: ImportContext,
        raw_rows: List[Dict[str, Any]],
        file_name: Optional[str] = None,
        user_id: Optional[int] = None,
        allow_possible_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """Preview + Commit در یک فراخوانی (بدون تأیید انسانی)."""
        batch, _ = self.create_preview(
            ctx=ctx, raw_rows=raw_rows, file_name=file_name, user_id=user_id
        )
        return self.commit(batch.id, allow_possible_duplicates=allow_possible_duplicates)

    # ── داخلی ──
    def _create_trade(self, trade_data: Dict[str, Any]) -> Trade:
        """ساخت `Trade` (نقطه‌ی قابل جای‌گزینی در تست اتمیک‌بودن)."""
        return Trade(**trade_data)

    def _plan_commit(
        self,
        rows: List[ImportBatchRow],
        ctx: ImportContext,
        allow_possible_duplicates: bool,
    ) -> Tuple[List[Tuple[ImportBatchRow, StagedTrade]], List[int], List[Dict[str, Any]]]:
        """تعیین سرنوشت هر ردیف پیش از شروع تراکنش.

        خروجی: (ردیف‌های آماده‌ی درج، شماره‌ی ردیف‌های تکراری، ردیف‌های مانع Commit)

        چرا پیش‌از تراکنش؟ چون رد شدن به‌خاطر ردیف مشکوک/نامعتبر نباید کل
        ImportBatch را FAILED کند؛ فقط Commit انجام نمی‌شود و Batch در
        وضعیت PENDING می‌ماند.
        """
        plan: List[Tuple[ImportBatchRow, StagedTrade]] = []
        skipped: List[int] = []
        blocking: List[Dict[str, Any]] = []
        seen: Dict[str, int] = {}

        for row in rows:
            staged = destage_payload(row.payload or {})

            error = validate_trade(staged.trade)
            if error:
                row.status = ImportRowStatus.INVALID
                row.message = error
                row.matched_trade_id = None
                blocking.append(
                    {"row_number": row.row_number, "status": "invalid", "message": error}
                )
                continue

            status, message, matched = classify_duplicate(self.db, staged, ctx, seen)
            row.status = status
            row.message = message
            row.matched_trade_id = matched

            if status == ImportRowStatus.DUPLICATE:
                skipped.append(row.row_number)
                continue

            if status == ImportRowStatus.POSSIBLE_DUPLICATE and not allow_possible_duplicates:
                blocking.append(
                    {
                        "row_number": row.row_number,
                        "status": status.value,
                        "message": message,
                    }
                )
                continue

            # ردیف‌های بعدی همین batch هم باید این هویت را «مصرف‌شده» ببینند
            seen[staged.identity_hash] = row.row_number
            plan.append((row, staged))

        return plan, skipped, blocking

    def _blocking_error(self, blocking: List[Dict[str, Any]]) -> ImportEngineError:
        invalid = [item for item in blocking if item["status"] == "invalid"]
        if invalid:
            first = invalid[0]
            return ImportEngineError(
                f"ذخیره انجام نشد: {len(invalid)} ردیف نامعتبر است و Import اتمیک است "
                f"(هیچ رکوردی ذخیره نشد) — ردیف {first['row_number']}: {first['message']}",
                400,
                blocking,
            )
        first = blocking[0]
        return ImportEngineError(
            f"ذخیره انجام نشد: {len(blocking)} ردیف مشکوک به تکرار است "
            f"(اولین مورد ردیف {first['row_number']}) — برای ادامه تأیید صریح لازم است",
            409,
            blocking,
        )

    def _success_message(self, imported: int, skipped: int) -> str:
        if skipped:
            return f"{imported} معامله ذخیره شد — {skipped} ردیف تکراری نادیده گرفته شد"
        return f"{imported} معامله با موفقیت ذخیره شد"

    def _mark_failed(self, batch_id: int, message: str) -> None:
        batch = self.db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            return
        batch.status = ImportStatus.FAILED
        batch.message = message
        batch.completed_at = datetime.now(timezone.utc)
        self.db.commit()









