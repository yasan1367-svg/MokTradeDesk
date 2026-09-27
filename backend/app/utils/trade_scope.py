"""
فیلترهای مشترک دامنه‌ی معاملات (Trade Scope)

معاملات REAL (حساب شخصی یا پراپ) بخشی از **تحلیل Backtest/Forward** یک نسخه‌ی استراتژی
نیستند؛ آن‌ها از مسیر PropStage / FinanceAccount تحلیل می‌شوند.

این ماژول یک شرط SQL مشترک برمی‌گرداند تا این معاملات در همه‌ی نقاط تحلیلی
(analyze_version، compare_versions، strategy stats، گزارش PDF) یکسان کنار گذاشته شوند.
"""
from sqlalchemy import or_, and_
from sqlalchemy.sql.elements import ColumnElement

from ..models.strategy import Trade, TestType


def analysis_trades_filter() -> ColumnElement:
    """شرط SQL: فقط معاملات غیر-REAL (یعنی BACKTEST و FORWARD) و حذف‌نشده.

    نکته: ستون `test_type` در مدل `nullable` است. ردیف‌های قدیمی که مقدار NULL دارند
    به‌عنوان «غیر-REAL» در نظر گرفته می‌شوند تا ناخواسته از تحلیل حذف نشوند
    (حفظ رفتار قبلی برای داده‌های legacy).

    مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود ('REAL') نه value ('real').

    فاز ۲۵: معاملات حذف‌شده (Soft Delete) از تحلیل کنار گذاشته می‌شوند.
    """
    return and_(
        or_(Trade.test_type.is_(None), Trade.test_type != TestType.REAL),
        Trade.is_deleted == False,
    )


def version_scope_key(version_id: int, test_type=None) -> str:
    """کلید دامنهٔ نسخه در `AnalysisResult` / `AnalysisRun`.

    یک نسخه می‌تواند هم‌زمان معاملات Backtest و Forward داشته باشد؛ بنابراین
    این دو باید مستقل ذخیره شوند و کلید شامل نام `test_type` است
    (مثلاً «12:BACKTEST» و «12:FORWARD»).

    حالت legacy (`test_type=None`) همان `str(version_id)` می‌ماند تا رکوردهای
    موجود قبلی و endpointهای قدیمی سازگار بمانند.
    """
    if test_type is None:
        return str(version_id)
    name = getattr(test_type, "name", None) or str(test_type)
    return f"{version_id}:{name}"

