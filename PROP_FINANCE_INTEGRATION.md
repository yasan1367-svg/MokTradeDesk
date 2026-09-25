# 🔗 PROP ↔ FINANCE Integration — طراحی فاز ۵

> **وضعیت:** 📝 پیش‌نویس طراحی — **در انتظار تأیید** (هیچ کدی هنوز نوشته نشده)
> **رویکرد انتخاب‌شده:** گزینه ۲ — «spec کامل + جایگزینی منطق شخصی با مالی»
> **تاریخ:** 2026-09-24

---

## ۱. خلاصه طراحی

یکپارچه‌سازی دو ماژول **پراپ** (`prop_accounts`, `prop_stages`, `prop_withdrawals`, `prop_costs`) و **مالی** (`accounts`, `categories`, `transactions`) به‌صورت **یک‌طرفه‌ی خودکار (Auto-Sync)**:

| رویداد در پراپ | نتیجه در مالی |
|----------------|---------------|
| ساخت `PropAccount` | ساخت خودکار `Account(type=prop)` + برگشت FK |
| ثبت `PropWithdrawal` | ساخت خودکار `Transaction(type=withdrawal)` + به‌روزرسانی موجودی مبدأ/مقصد |
| ثبت `PropCost` با `cost_type=purchase` | ساخت خودکار `Transaction(type=purchase)` با دسته «خرید پراپ» |

**حذف منطق شخصی از مسیر پراپ:**
- `WithdrawalCreate.target_personal_account_id` → **حذف** می‌شود.
- `LedgerTransaction` (دفتر کل شخصی) که در endpoint برداشت ساخته می‌شد → **حذف** می‌شود.
- جایگزین: `destination_account_id` (FK → `accounts.id`, **اجباری**) + `Transaction` مالی.
- منطق شخصی (`PersonalPage` / `/api/personal/ledger`) برای تراکنش‌های غیرپراپ **دست‌نخورده** می‌ماند.

**جهت ارتباط (دوطرفه):**
```
PropAccount.finance_account_id  ──►  accounts.id
PropWithdrawal.destination_account_id  ──►  accounts.id
Account.prop_firm_id            ──►  prop_firms.id        (از قبل موجود)
Transaction.related_prop_account_id ──► prop_accounts.id  (از قبل موجود)
```

---

## ۲. وضعیت فعلی (Before)

### ۲.۱ مدل‌ها

| مدل | فایل | فیلدهای مرتبط |
|-----|------|----------------|
| `PropAccount` | `models/prop.py:57` | `prop_firm_id`, `account_label`, `account_number`, `currency(String)` |
| `PropStage` | `models/prop.py:72` | `prop_account_id`, `initial_balance`, `total_withdrawn`, `current_profit` |
| `PropWithdrawal` | `models/prop.py:100` | `prop_stage_id`, `amount`, `withdrawal_date`, `note` |
| `PropCost` | `models/prop.py:111` | `prop_account_id`, `cost_type(String)`, `amount`, `currency` |
| `Account` | `models/finance.py:47` | `name`, `type(Enum)`, `currency(Enum IRR/USD)`, `balance`, `prop_firm_id` |
| `Transaction` | `models/finance.py:99` | `account_id(NOT NULL)`, `category_id`, `amount`, `currency(Enum)`, `type(Enum)`, `from_account_id`, `to_account_id`, `related_prop_account_id` |

### ۲.۲ ارتباط موجود (قبل از فاز ۵)

- ✅ `Account.prop_firm_id` → `prop_firms.id`
- ✅ `Transaction.related_prop_account_id` → `prop_accounts.id`
- ❌ `PropAccount.finance_account_id` (نبود)
- ❌ `PropWithdrawal.destination_account_id` (نبود)

### ۲.۳ Auto-Sync موجود — ناقص

`POST /api/prop/stages/{stage_id}/withdraw` (`prop.py:424`) فقط یک `LedgerTransaction` از نوع `PROP_PAYOUT` می‌سازد (دفتر شخصی). **هیچ `Transaction` مالی ساخته نمی‌شود** → برداشت‌های پراپ در گزارش‌های ماژول مالی (فاز ۳) دیده نمی‌شوند.

### ۲.۴ باگ‌های از قبل موجود (در مسیر این فاز)

| # | محل | مشکل | اقدام در فاز ۵ |
|---|-----|------|----------------|
| ۱ | `backend/app/api/prop.py:119` | `PropFirmDefaultRules` import نشده → `NameError` در `GET /firms/{id}/default-rules` | ✅ رفع (افزودن به import) |
| ۲ | `frontend/src/api/client.ts:184` | `getStageWithdrawals` → endpoint ناموجود. **تأیید شد: هیچ‌جا استفاده نمی‌شود (کد مرده)** | ✅ رفع یا حذف |

---

## ۳. مدل‌های تغییر یافته

### ۳.۱ `PropAccount` — افزودن ۲ خط (`models/prop.py:57-70`)

```python
class PropAccount(Base):
    __tablename__ = "prop_accounts"

    id = Column(Integer, primary_key=True, index=True)
    prop_firm_id = Column(Integer, ForeignKey("prop_firms.id"), nullable=False)
    account_label = Column(String, nullable=False)
    account_number = Column(String, nullable=True)
    currency = Column(String, default="USD")
    is_active = Column(Integer, default=1)

    # 🆕 فاز ۵ — ارتباط با حساب مالی
    finance_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    firm = relationship("PropFirm", back_populates="accounts")
    stages = relationship("PropStage", back_populates="account", cascade="all, delete-orphan")
    costs = relationship("PropCost", back_populates="account", cascade="all, delete-orphan")

    # 🆕 فاز ۵
    finance_account = relationship("Account", foreign_keys=[finance_account_id])
```

### ۳.۲ `PropWithdrawal` — افزودن ۲ خط (`models/prop.py:100-109`)

```python
class PropWithdrawal(Base):
    __tablename__ = "prop_withdrawals"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=False)
    amount = Column(Float, nullable=False)
    withdrawal_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    note = Column(Text, nullable=True)

    # 🆕 فاز ۵ — حساب مقصد پول برداشت‌شده
    destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    stage = relationship("PropStage", back_populates="withdrawals")

    # 🆕 فاز ۵
    destination_account = relationship("Account", foreign_keys=[destination_account_id])
```

> **نکته فنی:** هر دو ستون `nullable=True` هستند تا با رکوردهای موجود سازگار بمانند. `relationship("Account")` با نام رشته‌ای resolve می‌شود (همان الگویی که `Account.prop_firm = relationship("PropFirm")` از قبل استفاده می‌کند).

---

## ۴. Migration

**فایل جدید:** `backend/migrations/versions/<rev>_link_prop_to_finance.py`

```python
revision = '<new_rev>'
down_revision = '51ea09b4aa3d'   # head فعلی (finance_tables)

def upgrade():
    op.add_column('prop_accounts',
        sa.Column('finance_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_prop_accounts_finance_account_id',
        'prop_accounts', 'accounts', ['finance_account_id'], ['id'])

    op.add_column('prop_withdrawals',
        sa.Column('destination_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_prop_withdrawals_destination_account_id',
        'prop_withdrawals', 'accounts', ['destination_account_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_prop_withdrawals_destination_account_id',
        'prop_withdrawals', type_='foreignkey')
    op.drop_column('prop_withdrawals', 'destination_account_id')
    op.drop_constraint('fk_prop_accounts_finance_account_id',
        'prop_accounts', type_='foreignkey')
    op.drop_column('prop_accounts', 'finance_account_id')
```

**⚠️ هشدار SQLite:** `op.create_foreign_key` روی SQLite پشتیبانی نمی‌شود مگر با `batch_alter_table`. دو راه:

| راه | توضیح |
|-----|-------|
| **الف (توصیه‌شده)** | استفاده از `with op.batch_alter_table('prop_accounts') as batch: batch.add_column(...)` |
| **ب** | فقط `op.add_column` بدون `create_foreign_key` (SQLite در `add_column` محدودیت FK را اعمال نمی‌کند ولی ستون کار می‌کند) |

**قبل از اجرا:** بکاپ دیتابیس الزامی است:
```powershell
Copy-Item backend\trading_desk.db backend\trading_desk.db.bak_phase5
```

**اجرا:**
```powershell
cd backend; .\.venv\Scripts\alembic.exe upgrade head
```

---

## ۵. APIها

### ۵.۱ `POST /api/prop/accounts` — ساخت حساب مالی خودکار

**Schema (`PropAccountCreate`) — فیلد جدید:**
```python
class PropAccountCreate(BaseModel):
    prop_firm_id: int
    account_label: str
    account_number: Optional[str] = None
    currency: str = "USD"
    initial_balance: Optional[float] = 10000.0
    profit_target: Optional[float] = 800.0
    max_daily_dd: Optional[float] = 500.0
    max_total_dd: Optional[float] = 1000.0
    min_trading_days: Optional[int] = 5
    create_finance_account: bool = True          # 🆕 فاز ۵ (پیش‌فرض فعال)
```

**منطق جدید (بعد از ساخت `PropAccount`، قبل از ساخت Stage1):**
```python
if account.create_finance_account:
    fin = Account(
        name=account.account_label,                    # «FTMO 100K»
        type=AccountType.PROP,
        currency=_to_currency(account.currency),       # String → Enum(IRR|USD)
        balance=account.initial_balance or 0.0,
        prop_firm_name=firm.name,
        prop_firm_id=account.prop_firm_id,
    )
    db.add(fin); db.flush()                            # flush برای گرفتن id
    db_account.finance_account_id = fin.id
```

**Response (تغییر یافته):**
```json
{
  "id": 12,
  "finance_account_id": 7,
  "message": "اکانت و مرحله ۱ ایجاد شد"
}
```

**Helper مشترک (جدید در `prop.py`):**
```python
def _to_currency(value: str) -> Currency:
    """تبدیل String پراپ به Enum مالی (IRR|USD) با fallback امن"""
    try:
        return Currency((value or "USD").upper())
    except ValueError:
        return Currency.USD
```

### ۵.۲ `POST /api/prop/stages/{stage_id}/withdraw` — برداشت + تراکنش مالی

**Schema (`WithdrawalCreate`) — جایگزینی فیلد:**
```python
class WithdrawalCreate(BaseModel):
    amount: float
    note: Optional[str] = None
    destination_account_id: int                 # 🆕 اجباری (FK → accounts.id)
    # ❌ target_personal_account_id حذف شد
```

**منطق جدید:**
```python
# ۱. اعتبارسنجی‌ها (بدون تغییر): stage وجود، FUNDED_REAL، validate_withdrawal
# ۲. اعتبارسنجی جدید: مقصد باید وجود داشته باشد و از نوع prop نباشد
dest = db.query(Account).filter(
    Account.id == request.destination_account_id,
    Account.type != AccountType.PROP,
).first()
if not dest:
    raise HTTPException(400, "حساب مقصد معتبر نیست (باید بانک/صرافی/کیف‌پول/بروکر باشد)")

# ۳. مبدأ = حساب مالی پراپ
prop_acc = db.query(PropAccount).filter(PropAccount.id == stage.prop_account_id).first()
src_id = prop_acc.finance_account_id if prop_acc else None

# ۴. ثبت PropWithdrawal
withdrawal = PropWithdrawal(
    prop_stage_id=stage_id, amount=request.amount, note=request.note,
    destination_account_id=request.destination_account_id,   # 🆕
)
db.add(withdrawal)

# ۵. ثبت Transaction مالی
tx = Transaction(
    account_id=request.destination_account_id,     # ← ⚠️ تصمیم باز (بخش ۹)
    category_id=<id دسته «برداشت پراپ»>,             # اختیاری
    amount=request.amount,
    currency=_to_currency(prop_acc.currency if prop_acc else "USD"),
    date=datetime.now(timezone.utc),
    description=f"برداشت از {prop_acc.account_label if prop_acc else 'پراپ'}" + (f" - {request.note}" if request.note else ""),
    type=TransactionType.WITHDRAWAL,
    from_account_id=src_id,                         # 🆕 مبدأ
    to_account_id=request.destination_account_id,   # 🆕 مقصد
    related_prop_account_id=stage.prop_account_id,  # 🆕 لینک به پراپ
)
db.add(tx)

# ۶. به‌روزرسانی موجودی‌ها
if src_id:  # مبدأ کم شود
    src_acct = db.query(Account).filter(Account.id == src_id).first()
    if src_acct: src_acct.balance = (src_acct.balance or 0) - request.amount
dest.balance = (dest.balance or 0) + request.amount   # مقصد زیاد شود

# ۷. total_withdrawn مرحله (بدون تغییر)
stage.total_withdrawn = (stage.total_withdrawn or 0) + request.amount

db.commit()
```

**❌ حذف‌شده:** بلوک `LedgerTransaction` (خطوط ۴۵۱-۴۷۰) — دیگر دفتر شخصی ساخته نمی‌شود.

### ۵.۳ `POST /api/prop/costs` — ثبت هزینه + تراکنش خرید

**Schema (`PropCostCreate`) — ۲ فیلد جدید:**
```python
class PropCostCreate(BaseModel):
    prop_account_id: int
    cost_type: str                              # "purchase" برای خرید پراپ
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    pay_from_account_id: Optional[int] = None   # 🆕 حساب پرداخت‌کننده (مالی)
    create_transaction: bool = True             # 🆕 ثبت خودکار Transaction
```

**منطق جدید:**
```python
db_cost = PropCost(**cost.model_dump(exclude={"pay_from_account_id", "create_transaction"}))
db.add(db_cost); db.flush()

if cost.create_transaction and cost.cost_type == "purchase":
    prop_acc = db.query(PropAccount).filter(PropAccount.id == cost.prop_account_id).first()
    cat = _get_or_create_category(db, "خرید پراپ", CategoryType.EXPENSE, "#E74C3C", "🛒")
    payer_id = cost.pay_from_account_id or (prop_acc.finance_account_id if prop_acc else None)

    tx = Transaction(
        account_id=payer_id,                        # ⚠️ نیازمند account_id معتبر (بخش ۹.۱)
        category_id=cat.id,
        amount=cost.amount,
        currency=_to_currency(cost.currency),
        date=datetime.now(timezone.utc),
        description=cost.description or f"خرید پراپ {prop_acc.account_label if prop_acc else ''}",
        type=TransactionType.PURCHASE,
        from_account_id=payer_id,
        related_prop_account_id=cost.prop_account_id,
    )
    db.add(tx)
    if payer_id:
        payer = db.query(Account).filter(Account.id == payer_id).first()
        if payer: payer.balance = (payer.balance or 0) - cost.amount

db.commit()
```

### ۵.۴ `GET /api/prop/accounts/{account_id}/finance-account` — **جدید**

```python
@router.get("/accounts/{account_id}/finance-account")
def get_prop_finance_account(account_id: int, db: Session = Depends(get_db)):
    """دریافت حساب مالی متناظر با یک اکانت پراپ"""
    prop_acc = db.query(PropAccount).filter(PropAccount.id == account_id).first()
    if not prop_acc:
        raise HTTPException(404, "اکانت پراپ پیدا نشد")
    if not prop_acc.finance_account_id:
        return {"linked": False, "account": None}

    fin = db.query(Account).filter(Account.id == prop_acc.finance_account_id).first()
    if not fin:
        return {"linked": False, "account": None}

    return {
        "linked": True,
        "account": {
            "id": fin.id, "name": fin.name,
            "type": fin.type.value if fin.type else None,
            "currency": fin.currency.value if fin.currency else None,
            "balance": fin.balance,
        },
    }
```

---

## ۶. تغییرات Frontend

### ۶.۱ `frontend/src/api/client.ts`

```typescript
// 🆕 فاز ۵
export const getPropAccountFinanceAccount = (propAccountId: number) =>
  api.get(`/api/prop/accounts/${propAccountId}/finance-account`);

export const getFinanceAccountsForDestination = () =>
  api.get('/api/finance/accounts');   // فیلتر type!=prop در سمت کلاینت
```

**تغییر امضاها:**
```typescript
// createPropAccount → افزودن create_finance_account
export const createPropAccount = (data: {
  prop_firm_id: number;
  account_label: string;
  account_number?: string;
  initial_balance?: number;
  profit_target?: number;
  max_daily_dd?: number;
  max_total_dd?: number;
  min_trading_days?: number;
  create_finance_account?: boolean;          // 🆕
}) => api.post('/api/prop/accounts', data);

// withdrawFromStage → جایگزینی destination_account_id
// (امضای فعلی: withdrawFromStage(stageId, amount, _, targetPersonalAccountId))
export const withdrawFromStage = (
  stageId: number,
  amount: number,
  destinationAccountId: number,              // 🆕 اجباری
  note?: string,
) => api.post(`/api/prop/stages/${stageId}/withdraw`, {
  amount,
  destination_account_id: destinationAccountId,
  note,
});

// 🐛 رفع باگ: getStageWithdrawals (خط ۱۸۴) — کد مرده؛ حذف شود
```

### ۶.۲ `frontend/src/pages/PropPage.tsx`

| # | تغییر | جزئیات |
|---|--------|--------|
| ۱ | **فرم ساخت اکانت** (`handleCreateAccount` خط ۲۴۲) | checkbox «ساخت خودکار حساب مالی» با state `createFinanceAccount` پیش‌فرض `true` + ارسال `create_finance_account` |
| ۲ | **فرم برداشت** (`handleWithdraw` خط ۴۰۸) | جایگزینی `prompt()` اکانت شخصی با select حساب مقصد از `getFinanceAccounts()` (فیلتر `type != prop`) + ارسال `destination_account_id` |
| ۳ | **جزئیات اکانت** | لینک «💰 مشاهده حساب مالی» با `getPropAccountFinanceAccount(account.id)`؛ در صورت `linked: false` پیام «حساب مالی متصل نیست» |
| ۴ | **state جدید** | `financeAccounts`، `createFinanceAccount`، `selectedDestinationId` |

### ۶.۳ نکته UI

`handleWithdraw` فعلی از `prompt()` مرورگر استفاده می‌کند (خطوط ۴۰۹-۴۲۴). برای انتخاب حساب مقصد، `prompt()` کافی نیست چون باید نام حساب‌ها را نشان دهد. **پیشنهاد:** یک Modal کوچک با `<select>` که از `financeAccounts` پر می‌شود؛ حداقلِ کار: `prompt()` با لیست شماره‌دار اما از **حساب‌های مالی** (نه شخصی).

---

## ۷. Seed — دسته‌بندی «خرید پراپ»

در `backend/app/api/finance.py` → `DEFAULT_CATEGORIES` (خط ۵۴۷)، دو ورودی اضافه شود:

```python
{"name": "خرید پراپ", "type": CategoryType.EXPENSE, "color": "#E74C3C", "icon": "🛒"},
{"name": "برداشت پراپ", "type": CategoryType.INCOME, "color": "#22c55e", "icon": "🏢"},
```

> **نکته:** تابع `seed_categories` فقط دسته‌های ناموجود را می‌سازد (`skipped` برای موجودها)، پس اجرای مجدد ایمن است.
> علاوه بر seed، تابع `_get_or_create_category()` در `prop.py` هم هنگام ثبت تراکنش، دسته‌بندی را در صورت نبود **on-demand** می‌سازد (تا نیازی به اجرای دستی seed نباشد).

---

## ۸. رفع باگ‌های از قبل موجود

| # | فایل:خط | اقدام |
|---|---------|-------|
| ۱ | `backend/app/api/prop.py:8-11` | افزودن `PropFirmDefaultRules` به import → رفع `NameError` در `GET /firms/{id}/default-rules` |
| ۲ | `frontend/src/api/client.ts:184` | `getStageWithdrawals` کد مرده است (تأیید شد هیچ‌جا استفاده نمی‌شود) → **حذف** |

---

## ۹. ⚠️ نکات، تصمیمات باز و ابهامات

> این بخش مهم‌ترین قسمت طراحی است — **قبل از تأیید، لطفاً این ۶ مورد را ببینید.**

### ۹.۱ `Transaction.account_id` اجباری است (`NOT NULL`) — چه مقداری بگیرد؟

`Transaction` هم `account_id` (NOT NULL) دارد و هم `from_account_id`/`to_account_id`. spec شما فقط `from`/`to` را گفته بود.

| گزینه | `account_id` | مزیت | عیب |
|-------|--------------|------|-----|
| **الف (پیشنهاد من)** | `= destination_account_id` | پول در حساب مقصد «دیده» می‌شود؛ در `GET /accounts/{id}/stats` ظاهر می‌شود | در `total_expense` حساب مقصد به‌عنوان «هزینه» شمرده می‌شود (چون ماژول مالی هر `withdrawal` را expense می‌داند) |
| **ب** | `= PropAccount.finance_account_id` (مبدأ) | خروج پول در حساب پراپ درست است | ورود پول به حساب مقصد در stats دیده نمی‌شود |
| **ج** | دو تراکنش جدا (out مبدأ + in مقصد) | دقیق‌ترین حسابداری | پیچیده؛ نیازمند مفهوم `transfer` جدید در گزارش‌ها |

**توصیه:** گزینه **الف** + مستندسازی این caveat. رفع ریشه‌ای نیازمند افزودن مفهوم «transfer» به گزارش‌های فاز ۳ است — **خارج از دامنه فاز ۵**.

### ۹.۲ اگر `PropAccount.finance_account_id` قبلاً `NULL` باشد

اگر اکانت پراپی بدون حساب مالی ساخته شده باشد (یا با `create_finance_account=false`)، هنگام برداشت `src_id = None` می‌شود.

**پیشنهاد:** در `withdraw` اگر `finance_account_id` خالی بود، **خودکار ساخته شود** (همان منطق ۵.۱) و به پراپ وصل شود — تا کاربر خطا نگیرد. جایگزین: برگرداندن `400`.

### ۹.۳ بکاپ دیتابیس الزامی است

طبق دستور خودتان، **قبل از migration** یک نسخه پشتیبان گرفته می‌شود:
```
Copy-Item backend\trading_desk.db backend\trading_desk.db.bak_phase5
```

### ۹.۴ فرمت `cost_type`

هیچ قرارداد ثابتی وجود ندارد (فرانت UI برای هزینه ندارد). پیشنهاد: مقدار **`"purchase"`** برای خرید پراپ. سایر مقادیر (`"challenge_fee"`، `"reset"`، `"addon"`) بدون ساخت تراکنش ثبت می‌شوند.

### ۹.۵ اثر جانبی حذف منطق شخصی

- برداشت‌های **جدید** پراپ در «دفتر کل شخصی» (`PersonalPage`) **دیده نمی‌شوند**.
- برداشت‌های **قدیمی** (`LedgerTransaction`) در جدول `ledger_transactions` باقی می‌مانند (حذف فیزیکی **نمی‌شود**).
- صفحه «جریان نقدی» شخصی (`/api/personal/cashflow`) دیگر `PROP_PAYOUT` جدید نمی‌بیند.

**این مطابق تصمیم گزینه ۲ شماست** — فقط برای شفافیت ثبت می‌شود.

### ۹.۶ نکته حسابداری: موجودی حساب پراپ

کاستن از `Account.balance` حساب پراپ (`type=prop`) هنگام برداشت، از نظر **حسابداری واقعی** محل بحث است: موجودی پراپ پول کاربر نیست بلکه سرمایه‌ی در اختیار او نزد شرکت پراپ است. spec شما صریحاً کم‌شدن مبدأ را خواسته، لذا همان پیاده می‌شود — ولی پیشنهاد می‌کنم در فاز بعدی بازنگری شود.

---

## ۱۰. چک‌لیست اجرا و اعتبارسنجی

- [ ] بکاپ `trading_desk.db`
- [ ] افزودن ۲ فیلد به `models/prop.py`
- [ ] ساخت فایل migration + `alembic upgrade head`
- [ ] تأیید ستون‌ها با `PRAGMA table_info(prop_accounts)` و `PRAGMA table_info(prop_withdrawals)`
- [ ] اصلاح import `PropFirmDefaultRules` در `prop.py`
- [ ] افزودن helperهای `_to_currency()` و `_get_or_create_category()`
- [ ] ایمپورت `Account`, `AccountType`, `Transaction`, `TransactionType`, `Category`, `CategoryType`, `Currency` در `prop.py`
- [ ] تغییر `PropAccountCreate` + منطق `create_account`
- [ ] تغییر `WithdrawalCreate` + بازنویسی `withdraw`
- [ ] تغییر `PropCostCreate` + منطق `create_cost`
- [ ] افزودن `GET /accounts/{id}/finance-account`
- [ ] افزودن ۲ دسته به `DEFAULT_CATEGORIES`
- [ ] به‌روزرسانی `client.ts` (۲ تابع جدید + ۲ امضا + حذف باگ ۱۸۴)
- [ ] به‌روزرسانی `PropPage.tsx` (checkbox + select مقصد + لینک حساب مالی)
- [ ] ✅ `python -c "from app.main import app"` (import سالم)
- [ ] ✅ تست TestClient: ساخت اکانت پراپ → بررسی ساخت `Account`
- [ ] ✅ تست TestClient: برداشت → بررسی `Transaction` + موجودی‌ها + `total_withdrawn`
- [ ] ✅ تست TestClient: هزینه purchase → بررسی `Transaction(type=purchase)` + دسته
- [ ] ✅ تست `GET /accounts/{id}/finance-account` (حالت linked true/false)
- [ ] ✅ `npx tsc -b --force` و `npm run build` (exit 0)

---

## ۱۱. ریسک‌ها و Rollback

| ریسک | احتمال | کاهش |
|------|--------|------|
| migration روی SQLite با FK شکست بخورد | متوسط | `batch_alter_table` یا صرفِ `add_column` |
| شکستن `PersonalPage` (چون prop دیگر Ledger نمی‌سازد) | بالا (عمدی) | مطابق تصمیم گزینه ۲ — صفحات شخصی برای غیرپراپ کار می‌کنند |
| دوبار شمارش در `/summary` (caveat ۹.۱) | متوسط | مستندسازی |
| `NameError`/import ناقص در `prop.py` | متوسط | چک‌لیست + تست import |
| `account_id = NULL` در `Transaction` → خطای NOT NULL | متوسط | همیشه `account_id` را از مقصد/پرداخت‌کننده پر کن |

**Rollback:**
```powershell
cd backend; .\.venv\Scripts\alembic.exe downgrade -1
# در صورت نیاز به بازگردانی کامل دیتابیس:
Copy-Item backend\trading_desk.db.bak_phase5 backend\trading_desk.db
```

---

## ۱۲. جمع‌بندی فایل‌های تغییریافته

| فایل | نوع تغییر |
|------|-----------|
| `backend/app/models/prop.py` | ✏️ ۲ فیلد + ۲ relationship |
| `backend/migrations/versions/<rev>_link_prop_to_finance.py` | 🆕 فایل جدید |
| `backend/app/api/prop.py` | ✏️ import + ۲ helper + ۳ schema + ۳ endpoint + ۱ endpoint جدید |
| `backend/app/api/finance.py` | ✏️ ۲ دسته در `DEFAULT_CATEGORIES` |
| `frontend/src/api/client.ts` | ✏️ ۲ تابع جدید + ۲ امضا + حذف کد مرده |
| `frontend/src/pages/PropPage.tsx` | ✏️ checkbox + select مقصد + لینک حساب مالی |
| `PROP_FINANCE_INTEGRATION.md` | 🆕 همین فایل |

---

## ۱۳. ترتیب پیشنهادی اجرا

1. **بکاپ دیتابیس** (۹.۳)
2. **مدل‌ها** (`models/prop.py`) — ۲ فیلد + ۲ relationship
3. **Migration** + `alembic upgrade head` + تأیید ستون‌ها
4. **بک‌اند API** (`prop.py` + seed در `finance.py`) + تست import
5. **تست بک‌اند** با TestClient (۴ سناریو)
6. **فرانت‌اند** (`client.ts` + `PropPage.tsx`) + `tsc -b --force`
7. **build نهایی** `npm run build`

---

> ✅ **پایان طراحی — منتظر تأیید شما برای شروع کدنویسی.**
> اگر با موارد بخش ۹ (خصوصاً **۹.۱** گزینه الف، **۹.۲** خودکارسازی، و **۹.۴** قرارداد `"purchase"`) موافقید، بفرمایید تا از مرحله ۱ (بکاپ) شروع کنم.