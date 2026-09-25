"""
کمک‌تابع مشترک استخراج مقدار Enum (فاز ۱۵.۹)

پیش‌تر الگوی تکراری `x.value if hasattr(x, 'value') else str(x)` در چند endpoint
تکرار می‌شد و بعضی جاها مستقیماً `.value` استفاده می‌کردند (ناسازگاری خروجی).
این helper یک رفتار واحد و امن تضمین می‌کند.
"""
from typing import Any


def enum_value(value: Any) -> Any:
    """مقدار رشته‌ای یک Enum را برمی‌گرداند.

    - اگر مقدار Enum باشد → `.value` آن (رشته)
    - در غیر این صورت → `str(value)` (رفتار fallback قبلی، بدون تغییر)

    مثال:
        enum_value(StageType.STAGE_1)  ->  "stage_1"
        enum_value("stage_1")          ->  "stage_1"
    """
    return value.value if hasattr(value, "value") else str(value)
