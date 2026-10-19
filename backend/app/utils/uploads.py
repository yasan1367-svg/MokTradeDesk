"""
کمک‌تابع مشترک آپلود فایل (فاز ۱۵.۱۱)

قبل از این فاز، همهٔ endpointهای آپلود (`trades`, `personal`, `imports`) فایل را
بدون هیچ سقف حجمی می‌خواندند ⇒ خطر پر شدن حافظه/دیسک با فایل حجیم.
این helper یک سقف واحد (۱۰ مگابایت) اعمال می‌کند و در صورت عبور، خطای ۴۱۳ می‌دهد.
"""
from fastapi import HTTPException, UploadFile

# سقف حجم آپلود: ۱۰ مگابایت
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_SIZE_MB = MAX_UPLOAD_SIZE // (1024 * 1024)


def _too_large_detail() -> str:
    return f"حجم فایل بیش از حد مجاز است (حداکثر {MAX_UPLOAD_SIZE_MB} مگابایت)"


async def read_upload_limited(file: UploadFile, max_size: int = MAX_UPLOAD_SIZE) -> bytes:
    """خواندن محتوای فایل آپلودی با بررسی سقف حجم.

    - ابتدا از `file.size` (اگر Starlette آن را پر کرده باشد) استفاده می‌شود.
    - در غیر این صورت با `seek(0, 2)` + `tell()` حجم محاسبه و مکان به ابتدا برمی‌گردد.
    - در صورت عبور از سقف → `HTTPException(413)`.
    - در پایان، حجم واقعی خوانده‌شده هم دوباره بررسی می‌شود (محافظت مضاعف).

    Raises:
        HTTPException: با کد 413 اگر حجم فایل از سقف بیشتر باشد.
    """
    size = getattr(file, "size", None)
    if size is None:
        try:
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(0)
        except Exception:
            size = None

    if size is not None and size > max_size:
        raise HTTPException(status_code=413, detail=_too_large_detail())

    content = await file.read()

    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=_too_large_detail())

    return content
