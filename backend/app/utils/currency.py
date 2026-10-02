"""فاز ۴۵.۶ — ابزار مشترک تبدیل ارز.

پیش از این، سه نسخهٔ `_to_currency` در `wallet_service.py`، `payout_service.py` و
`api/prop.py` وجود داشت که رفتارهای متفاوتی داشتند (یکی None-aware، دوتای دیگر
fallback به USDT). اکنون همه از همین تابع استفاده می‌کنند.
"""
from typing import Optional

from ..models.finance import Currency


def to_currency(value, default: Optional[Currency] = None) -> Optional[Currency]:
    """تبدیل String/Enum به `Currency`.

    - `None`       ⇒ `default` (پیش‌فرض `None` تا default مدل اعمال شود).
    - `Currency`   ⇒ همان مقدار.
    - رشتهٔ معتبر   ⇒ مقدار Enum (case-insensitive).
    - مقدار نامعتبر ⇒ اگر `default` داده شده باشد همان، وگرنه `ValueError`.
    """
    if value is None:
        return default
    if isinstance(value, Currency):
        return value
    if isinstance(value, str):
        try:
            return Currency(value.strip().upper())
        except ValueError:
            if default is not None:
                return default
            raise ValueError(f"ارز نامعتبر: {value}")
    if default is not None:
        return default
    raise ValueError(f"نوع ارز نامعتبر: {type(value)}")
