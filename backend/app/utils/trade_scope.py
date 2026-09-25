"""
فیلترهای مشترک دامنه‌ی معاملات (Trade Scope)

معاملات REAL (حساب شخصی یا پراپ) بخشی از **تحلیل Backtest/Forward** یک نسخه‌ی استراتژی
نیستند؛ آن‌ها از مسیر PropStage / FinanceAccount تحلیل می‌شوند.

این ماژول یک شرط SQL مشترک برمی‌گرداند تا این معاملات در همه‌ی نقاط تحلیلی
(analyze_version، compare_versions، strategy stats، گزارش PDF) یکسان کنار گذاشته شوند.
"""
from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from ..models.strategy import Trade, TestType


def analysis_trades_filter() -> ColumnElement:
    """شرط SQL: فقط معاملات غیر-REAL (یعنی BACKTEST و FORWARD).

    نکته: ستون `test_type` در مدل `nullable` است. ردیف‌های قدیمی که مقدار NULL دارند
    به‌عنوان «غیر-REAL» در نظر گرفته می‌شوند تا ناخواسته از تحلیل حذف نشوند
    (حفظ رفتار قبلی برای داده‌های legacy).

    مقدار enum در دیتابیس به‌صورت NAME ذخیره می‌شود ('REAL') نه value ('real').
    """
    return or_(Trade.test_type.is_(None), Trade.test_type != TestType.REAL)
