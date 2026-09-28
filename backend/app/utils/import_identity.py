"""
هویت معامله و hashهای ایمپورت (فاز ۳۰/۳۱)

این ماژول تنها مرجع محاسبه‌ی:
- `compute_trade_hash`   : همان hash قدیمی (MD5 از source|symbol|direction|times|prices|size)
                           که در `Trade.trade_hash` ذخیره می‌شود (سازگاری با داده‌های legacy).
- `build_identity_hash`  : هویت کامل معامله برای Duplicate Detection (فاز ۳۱).

هویت (طبق قرارداد فاز ۳۱):
    source + external_ticket + trading_account_id + symbol + open_time + close_time
به‌علاوهٔ «دامنه»:
    version_id + prop_stage_id + test_type
دلیل افزودن دامنه: `trading_account_id` برای BACKTEST/FORWARD/REAL_PROP خالی است،
پس بدون دامنه یک فایل مشترک بین دو نسخه‌ی استراتژی اشتباهاً «تکراری» می‌شد.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ═════════════════════════════════════════════
# Helpers — نرمال‌سازی زمان
# ═════════════════════════════════════════════
_DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S")


def normalize_utc(value: Any) -> Optional[datetime]:
    """تبدیل هر ورودی زمانی به datetime آگاه از timezone (UTC).

    - `None` → `None`
    - رشته‌ی ISO یا «YYYY-MM-DD HH:MM:SS[.ffffff]» → datetime
    - datetime بدون tz → UTC فرض می‌شود (هم‌قرارداد `api/trades.py`)
    """
    if value is None or value == "":
        return None
    dt: Optional[datetime]
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
                return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_utc(value: Any) -> str:
    """نمایش متنی UTC (برای hash و برای JSON staging)."""
    dt = normalize_utc(value)
    return dt.isoformat() if dt else ""


# ═════════════════════════════════════════════
# Trade Hash (legacy — سازگاری)
# ═════════════════════════════════════════════
TRADE_HASH_FIELDS = (
    "source", "symbol", "direction", "open_time", "close_time",
    "open_price", "close_price", "size",
)


def compute_trade_hash(trade_data: Dict[str, Any]) -> str:
    """MD5 همان فرمول قدیمی — برای پرشدن‌کردن `Trade.trade_hash`."""
    key = "|".join(str(trade_data.get(field, "")) for field in TRADE_HASH_FIELDS)
    return hashlib.md5(key.encode()).hexdigest()


# ═════════════════════════════════════════════
# Identity Hash (فاز ۳۱)
# ═════════════════════════════════════════════
IDENTITY_FIELDS = (
    "source", "external_ticket", "trading_account_id", "prop_stage_id",
    "version_id", "test_type", "symbol", "open_time", "close_time",
)


def test_type_name(value: Any) -> str:
    """نام enum تست (BACKTEST / FORWARD / REAL_PERSONAL / REAL_PROP)."""
    if value is None:
        return ""
    name = getattr(value, "name", None)
    return str(name) if name else str(value).strip().upper()


def _optional_id(value: Any) -> str:
    return "" if value is None else str(value)


def build_identity_hash(
    source: Optional[str],
    external_ticket: Optional[str],
    symbol: Optional[str],
    open_time: Any,
    close_time: Any = None,
    *,
    trading_account_id: Optional[int] = None,
    prop_stage_id: Optional[int] = None,
    version_id: Optional[int] = None,
    test_type: Any = None,
) -> str:
    """SHA-256 هویت معامله (۹ فیلد — ترتیب ثابت)."""
    parts = [
        source or "",
        external_ticket or "",
        _optional_id(trading_account_id),
        _optional_id(prop_stage_id),
        _optional_id(version_id),
        test_type_name(test_type),
        symbol or "",
        iso_utc(open_time),
        iso_utc(close_time),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def identity_components_are_complete(
    source: Optional[str], symbol: Optional[str], open_time: Any
) -> bool:
    """آیا حداقل‌های شناسه (source/symbol/open_time) موجودند؟"""
    return bool(source) and bool(symbol) and normalize_utc(open_time) is not None
