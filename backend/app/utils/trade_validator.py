from typing import Optional, Tuple
from ..models.strategy import TestType


class TradeValidator:
    """اعتبارسنجی Trade Contract"""

    @staticmethod
    def validate_classification(
        test_type: str,
        version_id: Optional[int],
        personal_trading_account_id: Optional[int],
        prop_stage_id: Optional[int],
    ) -> Tuple[bool, Optional[str]]:
        """
        اعتبارسنجی طبقه‌بندی معامله طبق قرارداد فاز ۲۷.

        | نوع            | version_id | personal_trading_account_id | prop_stage_id |
        | BACKTEST       | اجباری     | ممنوع                       | ممنوع         |
        | FORWARD        | اجباری     | ممنوع                       | ممنوع         |
        | REAL_PERSONAL  | اجباری     | اجباری                      | ممنوع         |
        | REAL_PROP      | اجباری     | ممنوع                       | اجباری        |

        Returns: (is_valid, error_message)
        """
        # تبدیل test_type به Enum
        try:
            tt = TestType(test_type)
        except ValueError:
            return False, f"نوع تست نامعتبر: {test_type}"

        # version_id برای همهٔ انواع اجباری است
        if not version_id:
            return False, f"{tt.name} نیاز به version_id دارد"

        # ═════════════════════════════════════════════
        # BACKTEST / FORWARD — نه حساب شخصی، نه پراپ
        # ═════════════════════════════════════════════
        if tt in (TestType.BACKTEST, TestType.FORWARD):
            if personal_trading_account_id:
                return False, f"{tt.name} نباید personal_trading_account_id داشته باشد"
            if prop_stage_id:
                return False, f"{tt.name} نباید prop_stage_id داشته باشد"

        # ═════════════════════════════════════════════
        # REAL_PERSONAL — فقط حساب معاملاتی شخصی
        # ═════════════════════════════════════════════
        elif tt == TestType.REAL_PERSONAL:
            if prop_stage_id:
                return False, "REAL_PERSONAL نباید prop_stage_id داشته باشد"
            if not personal_trading_account_id:
                return False, "REAL_PERSONAL نیاز به personal_trading_account_id دارد"

        # ═════════════════════════════════════════════
        # REAL_PROP — فقط مرحله پراپ (XOR)
        # ═════════════════════════════════════════════
        elif tt == TestType.REAL_PROP:
            if personal_trading_account_id:
                return False, "REAL_PROP نباید personal_trading_account_id داشته باشد"
            if not prop_stage_id:
                return False, "REAL_PROP نیاز به prop_stage_id دارد"

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