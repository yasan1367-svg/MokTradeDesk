"""Rate Limiting مشترک پروژه (فاز ۱۵.۲) — مبتنی بر slowapi.

استفاده:
    from ..core.rate_limit import limiter, IMPORT_RATE_LIMIT

    @router.post("/x")
    @limiter.limit(IMPORT_RATE_LIMIT)
    async def handler(request: Request, ...):
        ...
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# کلید محدودسازی: آدرس IP درخواست‌کننده
limiter = Limiter(key_func=get_remote_address)

# سقف‌های پیش‌فرض برای endpointهای سنگین
IMPORT_RATE_LIMIT = "10/minute"   # آپلود و پردازش فایل (Soft4X / MT4)
EXPORT_RATE_LIMIT = "20/minute"   # ساخت CSV/PDF (بار سنگین CPU/حافظه)
