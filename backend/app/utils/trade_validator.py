from typing import Optional, Tuple
from ..models.strategy import TestType


class TradeValidator:
    """اعتبارسنجی Trade Contract"""

    @staticmethod
    def validate_classification(
        test_type: str,
        version_id: Optional[int],
        finance_account_id: Optional[int],
        prop_stage_id: Optional[int],
    ) -> Tuple[bool, Optional[str]]:
        """
        اعتبارسنجی طبقه‌بندی معامله.
        Returns: (is_valid, error_message)
        """
        # تبدیل test_type به Enum
        try:
            test_type_enum = TestType(test_type)
        except ValueError:
            return False, f"نوع تست نامعتبر: {test_type}"

        # ═════════════════════════════════════════════
        # BACKTEST
        # ═════════════════════════════════════════════
        if test_type_enum == TestType.BACKTEST:
            if not version_id:
                return False, "BACKTEST نیاز به version_id دارد"
            if finance_account_id:
                return False, "BACKTEST نباید finance_account_id داشته باشد"
            if prop_stage_id:
                return False, "BACKTEST نباید prop_stage_id داشته باشد"

        # ═════════════════════════════════════════════
        # FORWARD
        # ═════════════════════════════════════════════
        elif test_type_enum == TestType.FORWARD:
            if not version_id:
                return False, "FORWARD نیاز به version_id دارد"
            if finance_account_id:
                return False, "FORWARD نباید finance_account_id داشته باشد"
            if prop_stage_id:
                return False, "FORWARD نباید prop_stage_id داشته باشد"

        # ═════════════════════════════════════════════
        # REAL (Personal یا Prop)
        # ═════════════════════════════════════════════
        elif test_type_enum == TestType.REAL:
            if not version_id:
                return False, "REAL نیاز به version_id دارد"

            # XOR: دقیقاً یکی از دو
            if finance_account_id and prop_stage_id:
                return False, "REAL نمی‌تواند همزمان finance_account_id و prop_stage_id داشته باشد"
            if not finance_account_id and not prop_stage_id:
                return False, "REAL باید یکی از finance_account_id یا prop_stage_id را داشته باشد"

        return True, None


    @staticmethod
    def validate_numbers(
        size: Optional[float],
        open_price: Optional[float],
        close_price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        r_multiple: Optional[float] = None,
        commission: Optional[float] = None,
        swap: Optional[float] = None,
    ) -> Tuple[bool, Optional[str]]:
        """اعتبارسنجی اعداد"""
        if size is not None and size <= 0:
            return False, "حجم معامله باید مثبت باشد"
        if open_price is not None and open_price <= 0:
            return False, "قیمت ورود باید مثبت باشد"
        if close_price is not None and close_price <= 0:
            return False, "قیمت خروج باید مثبت باشد"
        if sl is not None and sl <= 0:
            return False, "حد ضرر باید مثبت باشد"
        if tp is not None and tp <= 0:
            return False, "حد سود باید مثبت باشد"
        if commission is not None and commission < 0:
            # کامیشن معمولاً منفی ذخیره می‌شود، اما اینجا چک نمی‌کنیم
            pass
        return True, None


    @staticmethod
    def validate_dates(
        open_time,
        close_time=None,
    ) -> Tuple[bool, Optional[str]]:
        """اعتبارسنجی تاریخ‌ها"""
        if open_time is None:
            return False, "زمان باز شدن معامله الزامی است"
        if close_time is not None and close_time < open_time:
            return False, "زمان بسته شدن نمی‌تواند قبل از باز شدن باشد"
        return True, None