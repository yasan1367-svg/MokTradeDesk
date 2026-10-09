"""فاز ۳۹.۱ — سرویس کیف‌پول: **تنها نویسندهٔ** `FinancialAccount.balance`.

چرا این فایل وجود دارد؟
-----------------------
پیش از فاز ۳۹، موجودی کیف‌پول‌ها از **۵ نقطهٔ پراکنده** تغییر می‌کرد
(`payout_service.py` ×۴ و `prop.py` ×۱) در حالی که `POST/PATCH/DELETE /finance/transactions`
هیچ اثری روی موجودی نداشت ⇒ **دو منبع حقیقت** و drift اجتناب‌ناپذیر (شکاف G1/G11 در
`PLAN_PHASE39.md`).

قرارداد طلایی این فاز:
    هر تغییری در `FinancialAccount.balance` **فقط** از مسیر `WalletService` انجام می‌شود.

قرارداد جهت‌دار (direction contract)
-----------------------------------
    DEPOSIT / PROFIT                   ⇒ `account_id`  +
    WITHDRAWAL / LOSS / FEE / PURCHASE ⇒ `account_id`  −
    TRANSFER                           ⇒ `from_account_id` −  ,  `to_account_id` +
    ADJUSTMENT                         ⇒ `account_id`  ±  (علامت از خودِ مبلغ)

نکات:
- برای `TRANSFER` همیشه `account_id == to_account_id` تنظیم می‌شود (مثل قرارداد فاز ۳۳) و
  اثر روی `account_id` **دوباره** اعمال نمی‌شود (وگرنه مقصد دوبار بستانکار می‌شد).
- `ADJUSTMENT` از محافظ موجودی مستثناست (اصلاح دستی آگاهانه است).
- `post()` همیشه `db.flush()` می‌زند تا `tx.id` بلافاصله در دسترس باشد
  (نیاز `PayoutService._post_income` در فاز ۳۳).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..models.finance import (
    Currency,
    FinancialAccount,
    FinancialTransaction,
    TransactionType,
    CashFlow,
    AccountType,
)
from ..utils.currency import to_currency

logger = logging.getLogger("moktrade")


# ═════════════════════════════════════════════
# خطای دامنه
# ═════════════════════════════════════════════
class WalletError(ValueError):
    """خطای دامنهٔ کیف‌پول با پیام فارسی.

    زیرکلاس `ValueError` است تا لایه‌های موجودی که `except ValueError` دارند
    (`api/prop.py`) بدون تغییر، آن را به `HTTPException(400)` تبدیل کنند.
    """


# ═════════════════════════════════════════════
# قرارداد جهت‌دار
# ═════════════════════════════════════════════
BALANCE_DIRECTION: Dict[TransactionType, str] = {
    TransactionType.CONVERT: "convert",
    TransactionType.DEPOSIT: "+",
    TransactionType.PROFIT: "+",
    TransactionType.WITHDRAWAL: "-",
    TransactionType.LOSS: "-",
    TransactionType.FEE: "-",
    TransactionType.PURCHASE: "-",
    TransactionType.TRANSFER: "move",      # دو طرفه (مبدأ − / مقصد +)
    TransactionType.ADJUSTMENT: "signed",  # علامت از مبلغ
    TransactionType.EXTERNAL_INCOME: "+",
    TransactionType.EXTERNAL_EXPENSE: "-",
}

#: انواعی که موجودی را زیاد می‌کنند (برای گزارش‌ها/تست‌ها).
INFLOW_TYPES = frozenset({TransactionType.DEPOSIT, TransactionType.PROFIT})

#: انواعی که موجودی را کم می‌کنند.
OUTFLOW_TYPES = frozenset({
    TransactionType.WITHDRAWAL,
    TransactionType.LOSS,
    TransactionType.FEE,
    TransactionType.PURCHASE,
})

#: دقت مقایسه برای آشتی‌دهی (نصف سنت).
_EPSILON = 0.005


# ═════════════════════════════════════════════
# helpers
# ═════════════════════════════════════════════
def _to_currency(value) -> Optional[Currency]:
    """تبدیل امن مقدار ورودی به `Currency` (فاز ۴۵.۶: ابزار مشترک).

    `None` ⇒ `None` تا default مدل اعمال شود.
    """
    return to_currency(value)


def _direction_of(tx_type) -> str:
    """جهت اثر یک نوع تراکنش؛ مقدار ناشناخته/None ⇒ `"0"` (بدون اثر، مثل رفتار قدیم)."""
    if tx_type is None:
        return "0"
    try:
        value = tx_type if isinstance(tx_type, TransactionType) else TransactionType(tx_type)
    except ValueError:
        logger.warning("Unknown transaction type %r — no balance effect", tx_type)
        return "0"
    return BALANCE_DIRECTION.get(value, "0")


def _load_accounts(db: Session, ids: Iterable[Optional[int]]) -> Dict[int, FinancialAccount]:
    """بارگذاری کیف‌پول‌های خواسته‌شده به‌صورت یک کوئری (`account_id → object`)."""
    clean = {i for i in ids if i is not None}
    if not clean:
        return {}
    rows = db.query(FinancialAccount).filter(FinancialAccount.id.in_(clean)).all()
    return {a.id: a for a in rows}


def _as_type(tx_type) -> TransactionType:
    """تبدیل امن ورودی به `TransactionType`."""
    return tx_type if isinstance(tx_type, TransactionType) else TransactionType(tx_type)


def _normalize_amount(
    tx_type: TransactionType, amount, signed_amount=None
) -> float:
    """اعتبارسنجی/نرمال‌سازی مبلغ یک تراکنش.

    - `ADJUSTMENT` ⇒ صفر ممنوع، منفی مجاز (از `amount` یا `signed_amount`).
    - بقیهٔ انواع ⇒ باید بزرگ‌تر از صفر باشد.

    اولین منبع موجود از `signed_amount` و سپس `amount` استفاده می‌شود.
    """
    raw = signed_amount if signed_amount is not None else amount
    if raw is None:
        raise WalletError("مبلغ تراکنش الزامی است")
    value = float(raw)
    if not math.isfinite(value):
        raise WalletError("مبلغ تراکنش باید عددی محدود باشد")
    if tx_type == TransactionType.ADJUSTMENT:
        if value == 0:
            raise WalletError("مبلغ اصلاح نمی‌تواند صفر باشد")
    elif value <= 0:
        raise WalletError("مبلغ تراکنش باید بزرگ‌تر از صفر باشد")
    return value


def detect_cash_flow(
    tx_type: TransactionType,
    *,
    from_account: Optional[FinancialAccount] = None,
    to_account: Optional[FinancialAccount] = None,
) -> CashFlow:
    """تشخیص خودکار جریان نقدی بر اساس نوع تراکنش و حساب‌های مبدأ/مقصد.

    قوانین:
    - EXTERNAL_INCOME → INCOME فقط برای مقصد بانکی
    - EXTERNAL_EXPENSE → EXPENSE فقط برای مبدأ بانکی
    - TRANSFER (بانک ← غیربانک) → EXPENSE
    - TRANSFER (غیربانک ← بانک) → INCOME
    - FEE/PURCHASE/LOSS/WITHDRAWAL → EXPENSE فقط برای مبدأ بانکی
    - PROFIT → INCOME فقط برای مقصد بانکی
    - بقیه (DEPOSIT، CONVERT، TRANSFER داخلی، ADJUSTMENT) → NONE
    """
    if tx_type == TransactionType.EXTERNAL_INCOME:
        return CashFlow.INCOME if to_account and to_account.type == AccountType.BANK else CashFlow.NONE
    if tx_type == TransactionType.EXTERNAL_EXPENSE:
        return CashFlow.EXPENSE if from_account and from_account.type == AccountType.BANK else CashFlow.NONE
    if tx_type == TransactionType.TRANSFER:
        if from_account and to_account:
            if from_account.type == AccountType.BANK and to_account.type != AccountType.BANK:
                return CashFlow.EXPENSE
            if to_account.type == AccountType.BANK and from_account.type != AccountType.BANK:
                return CashFlow.INCOME
        return CashFlow.NONE
    if tx_type in (TransactionType.FEE, TransactionType.PURCHASE, TransactionType.LOSS, TransactionType.WITHDRAWAL):
        return CashFlow.EXPENSE if from_account and from_account.type == AccountType.BANK else CashFlow.NONE
    if tx_type == TransactionType.PROFIT:
        return CashFlow.INCOME if to_account and to_account.type == AccountType.BANK else CashFlow.NONE
    return CashFlow.NONE


# ═════════════════════════════════════════════
# سرویس
# ═════════════════════════════════════════════
class WalletService:
    """تنها نقطهٔ مجاز برای تغییر `FinancialAccount.balance`."""

    # ── محاسبهٔ اثر ──
    @staticmethod
    def deltas(tx: FinancialTransaction) -> Dict[int, float]:
        """نگاشت «شناسهٔ کیف‌پول → تغییر موجودی» برای یک تراکنش (بدون اعمال).

        - `TRANSFER`  : `from` منفی و `to` مثبت (account_id نادیده گرفته می‌شود).
        - `ADJUSTMENT`: علامت از خودِ `amount` می‌آید (منفی مجاز است).
        - بقیه        : `account_id` با علامت جهت.
        """
        amount = float(tx.amount or 0.0)
        direction = _direction_of(tx.type)

        out: Dict[int, float] = {}

        def _bump(account_id: Optional[int], delta: float) -> None:
            if account_id is None or delta == 0.0:
                return
            out[account_id] = out.get(account_id, 0.0) + delta

        if direction == "convert":
            _bump(tx.from_account_id, -amount)
            _bump(tx.to_account_id, float(tx.to_amount or 0.0))
        elif direction == "move":
            # انتقال یک‌طرفه (مبدأ یا مقصد نامشخص) = تبدیل/جابجایی که **بیرون از نرم‌افزار**
            # رخ داده (قرارداد قدیمی `/finance/transactions` و سناریوی کاربر:
            # «تبدیل در صرافی انجام می‌شود») ⇒ فقط ثبت می‌شود، بدون اثر روی موجودی.
            if tx.from_account_id is None or tx.to_account_id is None:
                return {}
            _bump(tx.from_account_id, -amount)
            _bump(tx.to_account_id, +amount)
        elif direction == "signed":
            _bump(tx.account_id, amount)
        elif direction == "+":
            _bump(tx.account_id, +amount)
        elif direction == "-":
            _bump(tx.account_id, -amount)

        return out

    @staticmethod
    def apply_effects(
        db: Session, tx: FinancialTransaction, *, sign: int = 1
    ) -> Dict[int, float]:
        """اثر تراکنش را روی موجودی کیف‌پول‌ها اعمال می‌کند (`sign=-1` ⇒ برگشت).

        خروجی: نگاشت «شناسهٔ کیف‌پول → تغییر اعمال‌شده».
        """
        if sign not in (1, -1):
            raise WalletError("علامت اعمال اثر باید ۱ یا -۱ باشد")

        effect = WalletService.deltas(tx)
        if not effect:
            return {}

        accounts = _load_accounts(db, effect.keys())
        missing = [aid for aid in effect if aid not in accounts]
        if missing:
            raise WalletError(
                "حساب مالی پیدا نشد: " + ", ".join(str(m) for m in sorted(missing))
            )

        applied: Dict[int, float] = {}
        for account_id, delta in effect.items():
            account = accounts[account_id]
            applied[account_id] = sign * delta
            account.balance = float(account.balance or 0.0) + (sign * delta)
        return applied

    # ── محافظ موجودی ──
    @staticmethod
    def _assert_sufficient(
        db: Session, tx: FinancialTransaction, *, allow_overdraft: bool
    ) -> None:
        """جلوگیری از منفی‌شدن موجودی برای انواع برداشتی (به‌جز ADJUSTMENT)."""
        if allow_overdraft or _direction_of(tx.type) == "signed":
            return

        debits = {aid: d for aid, d in WalletService.deltas(tx).items() if d < 0}
        if not debits:
            return

        accounts = _load_accounts(db, debits.keys())
        for account_id, delta in debits.items():
            account = accounts.get(account_id)
            if account is None:
                raise WalletError(f"حساب مالی {account_id} پیدا نشد")
            available = float(account.balance or 0.0)
            if available + delta < -_EPSILON:
                raise WalletError(
                    f"موجودی کیف‌پول «{account.name}» کافی نیست "
                    f"(موجودی: {available:g}، مورد نیاز: {-delta:g})"
                )


    # ── اعتبارسنجی مبلغ (برای مسیرهای ویرایش) ──
    @staticmethod
    def validate_amount(tx_type, amount, signed_amount=None) -> float:
        """اعتبارسنجی مبلغ یک تراکنش **بدون ثبت** آن.

        برای `PATCH`ها لازم است: بدون این چک، ویرایش مبلغ به صفر اثر قبلی را
        بی‌صدا حذف می‌کرد (`deltas` برای مبلغ صفر خالی برمی‌گردد).
        """
        return _normalize_amount(_as_type(tx_type), amount, signed_amount)

    @staticmethod
    def validate_accounts(db: Session, tx: FinancialTransaction) -> None:
        if tx.type == TransactionType.CONVERT:
            if tx.from_account_id is None or tx.to_account_id is None:
                raise WalletError("Conversion requires source and destination accounts")
            if tx.from_account_id == tx.to_account_id:
                raise WalletError("Conversion accounts must differ")
            accounts = _load_accounts(db, [tx.from_account_id, tx.to_account_id])
            source = accounts.get(tx.from_account_id)
            destination = accounts.get(tx.to_account_id)
            if source is None or destination is None:
                raise WalletError("Account not found")
            if source.currency == destination.currency:
                raise WalletError("Currencies must differ; use transfer")
            WalletService.validate_amount(tx.type, tx.amount)
            WalletService.validate_amount(tx.type, tx.to_amount)
            if tx.account_id != tx.to_account_id:
                raise WalletError("Conversion account must be destination")
            if tx.currency != source.currency or tx.to_currency != destination.currency:
                raise WalletError("Conversion currencies must match their accounts")
            return
        if tx.to_amount is not None or tx.to_currency is not None:
            raise WalletError("Destination amount/currency are only allowed for convert")
        if tx.type is None or tx.currency is None:
            raise WalletError("نوع تراکنش و ارز الزامی هستند")
        # EXTERNAL_INCOME: فقط مقصد لازمه (بدون مبدأ)
        if tx.type == TransactionType.EXTERNAL_INCOME:
            if tx.account_id is None:
                raise WalletError("حساب مقصد الزامی است")
            account = _load_accounts(db, [tx.account_id]).get(tx.account_id)
            if account is None:
                raise WalletError("حساب مالی پیدا نشد")
            if tx.currency is not None and account.currency != tx.currency:
                raise WalletError("ارز تراکنش باید با ارز حساب مقصد یکسان باشد")
            return
        # EXTERNAL_EXPENSE: فقط مبدأ لازمه (بدون مقصد)
        if tx.type == TransactionType.EXTERNAL_EXPENSE:
            if tx.account_id is None:
                raise WalletError("حساب مبدأ الزامی است")
            account = _load_accounts(db, [tx.account_id]).get(tx.account_id)
            if account is None:
                raise WalletError("حساب مالی پیدا نشد")
            if tx.currency is not None and account.currency != tx.currency:
                raise WalletError("ارز تراکنش باید با ارز حساب مبدأ یکسان باشد")
            return
        account_ids = [tx.account_id]
        if tx.type == TransactionType.TRANSFER:
            if tx.from_account_id is not None and tx.to_account_id is not None:
                if tx.from_account_id == tx.to_account_id:
                    raise WalletError("حساب مبدأ و مقصد باید متفاوت باشند")
                if tx.account_id != tx.to_account_id:
                    raise WalletError("حساب انتقال باید همان حساب مقصد باشد")
                account_ids.extend([tx.from_account_id, tx.to_account_id])
            elif tx.from_account_id is not None or tx.to_account_id is not None:
                raise WalletError("برای انتقال، حساب مبدأ و مقصد را با هم مشخص کن")
        accounts = _load_accounts(db, account_ids)
        for account_id in account_ids:
            account = accounts.get(account_id)
            if account is None:
                raise WalletError("حساب مالی پیدا نشد")
            if account.currency != tx.currency:
                raise WalletError("ارز تراکنش و تمام حساب‌های مرتبط باید یکسان باشد")

    @staticmethod
    def convert(
        db: Session, *, from_account_id: int, to_account_id: int,
        amount: float, to_amount: float, date=None,
        description: Optional[str] = None, category_id: Optional[int] = None,
        commit: bool = True,
    ) -> FinancialTransaction:
        accounts = _load_accounts(db, [from_account_id, to_account_id])
        source = accounts.get(from_account_id)
        destination = accounts.get(to_account_id)
        if source is None or destination is None:
            raise WalletError("Account not found")
        tx = FinancialTransaction(
            type=TransactionType.CONVERT, account_id=to_account_id,
            from_account_id=from_account_id, to_account_id=to_account_id,
            amount=amount, currency=source.currency,
            to_amount=to_amount, to_currency=destination.currency,
            date=date or datetime.now(timezone.utc), description=description,
            category_id=category_id,
        )
        WalletService.validate_accounts(db, tx)
        WalletService._assert_sufficient(db, tx, allow_overdraft=True)
        db.add(tx)
        db.flush()
        WalletService.apply_effects(db, tx)
        if commit:
            db.commit()
            db.refresh(tx)
        else:
            db.flush()
        return tx

    # ── ثبت تراکنش ──
    @staticmethod
    def post(
        db: Session,
        *,
        account_id: int,
        type: TransactionType,
        amount: Optional[float] = None,
        currency=None,
        date=None,
        category_id: Optional[int] = None,
        from_account_id: Optional[int] = None,
        to_account_id: Optional[int] = None,
        description: Optional[str] = None,
        related_trade_id: Optional[int] = None,
        related_prop_account_id: Optional[int] = None,
        signed_amount: Optional[float] = None,
        allow_overdraft: bool = False,
        allow_cross_currency: bool = False,
        commit: bool = True,
    ) -> FinancialTransaction:
        """ثبت یک تراکنش مالی + اعمال اثر آن روی موجودی کیف‌پول(ها).

        قوانین:
        - `amount > 0` برای همهٔ انواع، **به‌جز** `ADJUSTMENT`؛ برای اصلاح دستی
          می‌توان `amount` منفی داد یا به‌جایش `signed_amount` فرستاد.
        - `TRANSFER` دو حالت دارد:
          ۱) **دوطرفه** (`from_account_id` و `to_account_id` هر دو داده شوند) ⇒
             `from_account_id != to_account_id`، `account_id` روی مقصد تنظیم و
             اثر دوطرفه اعمال می‌شود.
          ۲) **یک‌طرفه** (یکی/هر دو نامشخص) ⇒ تبدیل یا جابجایی که **بیرون از نرم‌افزار**
             رخ داده؛ فقط ثبت می‌شود و **موجودی را تغییر نمی‌دهد** (قرارداد قدیمی
             `/finance/transactions` — برای ثبت موجودی حاصل از تبدیل بیرونی از
             `ADJUSTMENT` استفاده کنید).
        - `allow_overdraft=False` ⇒ برداشت بیش از موجودی با `WalletError` رد می‌شود.

        Raises:
            WalletError: مبلغ نامعتبر، حساب نامعتبر یا موجودی ناکافی.
        """
        tx_type = _as_type(type)
        if tx_type == TransactionType.CONVERT:
            raise WalletError("Use WalletService.convert for conversions")
        direction = _direction_of(tx_type)

        # ── اعتبارسنجی مبلغ ──
        value = _normalize_amount(tx_type, amount, signed_amount)

        # ── اعتبارسنجی حساب‌ها ──
        if direction == "move":
            if from_account_id is not None and to_account_id is not None:
                if from_account_id == to_account_id:
                    raise WalletError("حساب مبدأ و مقصد باید متفاوت باشند")
                account_id = to_account_id
            else:
                # انتقال یک‌طرفه: تبدیل/جابجایی بیرون از نرم‌افزار (قرارداد قدیمی)
                # ⇒ روی `account_id` ثبت می‌شود و موجودی را تغییر نمی‌دهد.
                from_account_id = None
                to_account_id = None
                if account_id is None:
                    raise WalletError("حساب تراکنش الزامی است")
        elif account_id is None:
            raise WalletError("حساب تراکنش الزامی است")

        present = _load_accounts(db, (account_id, from_account_id, to_account_id))
        if direction == "move" and from_account_id is not None:
            if from_account_id not in present or to_account_id not in present:
                raise WalletError("حساب مبدأ یا مقصد معتبر نیست")
        elif account_id not in present:
            raise WalletError("حساب مالی پیدا نشد")

        # ── فاز ۴۵.۵: اعتبارسنجی ارز ──
        target_currency = _to_currency(currency)
        if direction == "move":
            # انتقال دوطرفه: طرفین باید هم‌ارز باشند (مگر cross-currency مجاز شود)
            if from_account_id is not None and to_account_id is not None:
                src_acc = present[from_account_id]
                dst_acc = present[to_account_id]
                if src_acc.currency != dst_acc.currency and not allow_cross_currency:
                    raise WalletError(
                        "ارز حساب‌های مبدأ و مقصد باید یکسان باشد؛ انتقال هر ارز را جداگانه ثبت کن"
                    )
                if (
                    target_currency is not None
                    and src_acc.currency is not None
                    and target_currency != src_acc.currency
                ):
                    raise WalletError("ارز تراکنش باید با ارز حساب‌های مبدأ و مقصد یکسان باشد")
            elif account_id in present:
                account_obj = present[account_id]
                if (
                    target_currency is not None
                    and account_obj.currency is not None
                    and target_currency != account_obj.currency
                ):
                    raise WalletError("ارز تراکنش باید با ارز حساب یکسان باشد")
        else:
            account_obj = present[account_id]
            if (
                target_currency is not None
                and account_obj.currency is not None
                and target_currency != account_obj.currency
            ):
                raise WalletError(
                    f"ارز تراکنش ({target_currency.value}) با ارز حساب "
                    f"({account_obj.currency.value}) هم‌خوان نیست"
                )

        tx = FinancialTransaction(
            account_id=account_id,
            category_id=category_id,
            amount=value,
            currency=target_currency or present[account_id].currency,
            date=date or datetime.now(timezone.utc),
            description=description,
            type=tx_type,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            related_trade_id=related_trade_id,
            related_prop_account_id=related_prop_account_id,
        )

        WalletService._assert_sufficient(db, tx, allow_overdraft=allow_overdraft)

        db.add(tx)
        db.flush()                       # ⇒ tx.id بلافاصله در دسترس است
        # فاز ۴۷.۱: تشخیص خودکار cash_flow
        from_acc = present.get(from_account_id) if from_account_id else None
        to_acc = present.get(to_account_id) if to_account_id else None
        if direction in ("+", "-", "signed") and account_id in present:
            if direction == "+" or (direction == "signed" and tx_type != TransactionType.EXTERNAL_EXPENSE):
                to_acc = present[account_id]
            else:
                from_acc = present[account_id]
        tx.cash_flow = detect_cash_flow(tx_type, from_account=from_acc, to_account=to_acc)
        WalletService.apply_effects(db, tx)

        if commit:
            db.commit()
            db.refresh(tx)
        else:
            db.flush()
        return tx

    # ── برگشت ──
    @staticmethod
    def reverse(
        db: Session,
        tx: FinancialTransaction,
        *,
        commit: bool = True,
        allow_overdraft: bool = False,
    ) -> bool:
        """اثر تراکنش را برمی‌گرداند و آن را نرم‌حذف می‌کند.

        idempotent است: اگر تراکنش از قبل حذف‌شده باشد، هیچ کاری نمی‌کند و `False`
        برمی‌گرداند.

        فاز ۴۵.۷: اگر برگشت باعث منفی‌شدن موجودی یک حساب شود (مثلاً حذف یک واریز
        که پولش قبلاً خرج شده)، با `WalletError` رد می‌شود.
        """
        if tx is None or tx.is_deleted:
            return False

        if not allow_overdraft:
            # برگشت، منفیِ دلتای اصلی است ⇒ حساب‌هایی که دلتای مثبت داشته‌اند
            # در برگشت بدهکار می‌شوند و باید موجودی کافی داشته باشند.
            reversal_debits = {
                aid: -delta
                for aid, delta in WalletService.deltas(tx).items()
                if delta > 0
            }
            accounts = _load_accounts(db, reversal_debits.keys())
            for account_id, delta in reversal_debits.items():
                account = accounts.get(account_id)
                if account is None:
                    continue
                if float(account.balance or 0.0) + delta < -_EPSILON:
                    raise WalletError("حذف این تراکنش موجودی را منفی می‌کند")

        WalletService.apply_effects(db, tx, sign=-1)
        tx.is_deleted = True
        if commit:
            db.commit()
        else:
            db.flush()
        return True


    # ── گزارش‌ها ──
    @staticmethod
    def reconcile(db: Session, account_id: int) -> dict:
        """آشتی‌دهی: موجودی ذخیره‌شده در برابر مجموع اثرهای دفتر.

        خروجی: `{account_id, account_name, type, currency, stored, ledger, delta,
        is_balanced, entry_count}`

        `delta = stored − ledger`:
        - `delta == 0` ⇒ کل موجودی با تراکنش‌ها توضیح داده می‌شود (`is_balanced=True`).
        - `delta != 0` ⇒ بخشی از موجودی «موجودی اولیهٔ ضمنی» است و تراکنش متناظر ندارد
          (همان شکاف G1 — مثلاً کیف‌پولی که با `balance=1000` مستقیم ساخته شده).
        """
        account = db.query(FinancialAccount).filter(FinancialAccount.id == account_id).first()
        if not account:
            raise WalletError("حساب مالی پیدا نشد")

        ledger_total = 0.0
        entry_count = 0
        for tx in WalletService._account_transactions(db, account_id):
            delta = WalletService.deltas(tx).get(account_id, 0.0)
            if delta == 0.0:
                continue
            ledger_total += delta
            entry_count += 1

        stored = round(float(account.balance or 0.0), 2)
        ledger_total = round(ledger_total, 2)
        difference = round(stored - ledger_total, 2)

        return {
            "account_id": account.id,
            "account_name": account.name,
            "type": account.type.value if account.type else None,
            "currency": account.currency.value if account.currency else None,
            "stored": stored,
            "ledger": ledger_total,
            "delta": difference,
            "is_balanced": abs(difference) < _EPSILON,
            "entry_count": entry_count,
        }

    @staticmethod
    def ledger(
        db: Session,
        account_id: int,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        date_from=None,
        date_to=None,
    ) -> List[dict]:
        """صورت‌حساب کیف‌پول: اثر هر تراکنش + موجودی تجمعی (running balance)."""
        account = db.query(FinancialAccount).filter(FinancialAccount.id == account_id).first()
        if not account:
            raise WalletError("حساب مالی پیدا نشد")

        # فاز ۴۵.۸: موجودی آغازین = مجموع اثر تراکنش‌های مؤثر **قبل از** بازه
        opening = WalletService._opening_balance(db, account_id, before=date_from)

        rows = WalletService._account_transactions(
            db, account_id, date_from=date_from, date_to=date_to
        )

        running = opening
        all_entries: List[dict] = []
        for tx in rows:
            delta = WalletService.deltas(tx).get(account_id, 0.0)
            running += delta
            peer_from = tx.from_account_id
            peer_to = tx.to_account_id
            peer_id = next(
                (c for c in (peer_from, peer_to) if c is not None and c != account_id),
                None,
            )
            peer = tx.from_account if peer_id == peer_from else tx.to_account
            all_entries.append({
                "id": tx.id,
                "date": tx.date.isoformat() if tx.date else None,
                "type": tx.type.value if tx.type else None,
                "direction": "in" if delta > 0 else ("out" if delta < 0 else "none"),
                "amount": abs(delta) if tx.type == TransactionType.CONVERT else tx.amount,
                "signed_amount": round(delta, 2),
                "currency": (tx.to_currency.value if tx.type == TransactionType.CONVERT and account_id == tx.to_account_id else tx.currency.value) if tx.currency else None,
                "description": tx.description,
                "category_name": tx.category.name if tx.category else None,
                "peer_account_id": peer_id,
                "peer_account_name": peer.name if (peer_id and peer) else None,
                "running_balance": round(running, 2),
            })

        # فاز ۴۵.۸: offset/limit فقط پنجرهٔ نمایش را می‌بُرد؛ running از ابتدا محاسبه شده
        start = max(int(offset or 0), 0)
        end = start + int(limit) if limit else None
        return all_entries[start:end]

    # ── موجودی آغازین (برای running_balance) ──
    @staticmethod
    def _opening_balance(db: Session, account_id: int, *, before=None) -> float:
        """مجموع اثر تراکنش‌های مؤثر روی حساب، **قبل از** تاریخ داده‌شده."""
        if before is None:
            return 0.0
        q = (
            db.query(FinancialTransaction)
            .filter(
                FinancialTransaction.is_deleted == False,  # noqa: E712
                or_(
                    FinancialTransaction.account_id == account_id,
                    FinancialTransaction.from_account_id == account_id,
                    FinancialTransaction.to_account_id == account_id,
                ),
                FinancialTransaction.date < before,
            )
        )
        total = 0.0
        for tx in q.all():
            total += WalletService.deltas(tx).get(account_id, 0.0)
        return total

    # ── کوئری مشترک ──
    @staticmethod
    def _account_transactions(
        db: Session,
        account_id: int,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        date_from=None,
        date_to=None,
    ) -> List[FinancialTransaction]:
        """همهٔ تراکنش‌های غیرحذف‌شده‌ای که بر این کیف‌پول اثر دارند (یک کوئری، سه رابطه)."""
        q = (
            db.query(FinancialTransaction)
            .options(
                joinedload(FinancialTransaction.category),
                joinedload(FinancialTransaction.from_account),
                joinedload(FinancialTransaction.to_account),
            )
            .filter(
                FinancialTransaction.is_deleted == False,  # noqa: E712
                or_(
                    FinancialTransaction.account_id == account_id,
                    FinancialTransaction.from_account_id == account_id,
                    FinancialTransaction.to_account_id == account_id,
                ),
            )
            .order_by(FinancialTransaction.date.asc(), FinancialTransaction.id.asc())
        )
        if date_from:
            q = q.filter(FinancialTransaction.date >= date_from)
        if date_to:
            q = q.filter(FinancialTransaction.date <= date_to)
        if offset:
            q = q.offset(offset)
        if limit:
            q = q.limit(limit)
        return q.all()

