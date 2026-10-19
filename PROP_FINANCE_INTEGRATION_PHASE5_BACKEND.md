# 🔗 PROP ↔ FINANCE Integration — گزارش فاز ۵ (Backend)

> **وضعیت:** ✅ کامل و تست‌شده
> **دامنه:** فقط Backend (فرانت‌اند در فاز بعد)
> **تاریخ:** 2026-09-24
> **تصمیمات:** ۹.۱ = گزینه الف (`account_id` = حساب مقصد) | ۹.۲ = ساخت خودکار فعال | ۹.۴ = `cost_type="purchase"`

---

## ۱. خلاصه تغییرات

یکپارچه‌سازی **پراپ → مالی** به‌صورت خودکار (Auto-Sync) با حذف منطق دفتر کل شخصی از مسیر پراپ:

| رویداد در پراپ | نتیجه خودکار در مالی |
|----------------|----------------------|
| `POST /api/prop/accounts` | ساخت `Account(type=prop)` + `PropAccount.finance_account_id` |
| `POST /api/prop/stages/{id}/withdraw` | ساخت `Transaction(type=withdrawal)` + به‌روزرسانی موجودی مبدأ/مقصد + دسته «برداشت پراپ» |
| `POST /api/prop/costs` با `cost_type=purchase` | ساخت `Transaction(type=purchase)` + دسته «خرید پراپ» + کاهش موجودی پرداخت‌کننده |

**حذف‌شده:** `target_personal_account_id` و بلوک `LedgerTransaction` (دفتر شخصی) از endpoint برداشت پراپ.

**افزوده‌شده:** `GET /api/prop/accounts/{id}/finance-account` و `GET /api/prop/stages/{id}/withdrawals`.

---

## ۲. فایل‌های تغییریافته

| # | فایل | نوع | جزئیات |
|---|------|-----|--------|
| ۱ | `backend/app/models/prop.py` | ✏️ | `PropAccount.finance_account_id` + relationship، `PropWithdrawal.destination_account_id` + relationship |
| ۲ | `backend/migrations/versions/b7d4e19c2f83_link_prop_to_finance.py` | 🆕 | migration با `batch_alter_table` |
| ۳ | `backend/app/api/prop.py` | ✏️ | ۳ helper + ۳ schema + ۳ endpoint تغییر/جدید + رفع ۲ باگ |
| ۴ | `backend/app/api/finance.py` | ✏️ | ۲ دسته جدید در `DEFAULT_CATEGORIES` |
| ۵ | `PROP_FINANCE_INTEGRATION_PHASE5_BACKEND.md` | 🆕 | همین فایل |

### ۲.۱ مدل‌ها (`models/prop.py`)

```python
# PropAccount — ۲ خط اضافه شد
finance_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
finance_account = relationship("Account", foreign_keys=[finance_account_id])

# PropWithdrawal — ۲ خط اضافه شد
destination_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
destination_account = relationship("Account", foreign_keys=[destination_account_id])
```

### ۲.۲ Migration

- `revision = 'b7d4e19c2f83'` | `down_revision = '51ea09b4aa3d'`
- `op.batch_alter_table(...).add_column(...)` + `create_foreign_key(...)`
- ✅ اجرا شد: `alembic upgrade head`

### ۲.۳ API (`api/prop.py`)

| Endpoint | تغییر |
|----------|-------|
| `POST /accounts` | + `create_finance_account: bool = True` + ساخت `Account` + برگشت `finance_account_id` در response |
| `POST /stages/{id}/withdraw` | حذف `target_personal_account_id` → + `destination_account_id` (اجباری) + `Transaction` + به‌روزرسانی موجودی‌ها |
| `POST /costs` | + `pay_from_account_id` + `create_transaction` + `Transaction(type=purchase)` |
| `GET /accounts/{id}/finance-account` | 🆕 برگشت `{linked, account}` |
| `GET /stages/{id}/withdrawals` | 🆕 (رفع باگ ۲) |

**Helperهای جدید:**
- `_to_currency(value)` — تبدیل `String` پراپ به `Enum(IRR|USD)` با fallback امن
- `_get_or_create_category(db, name, type, color, icon)` — ساخت on-demand دسته‌بندی
- `_ensure_finance_account(db, prop_acc)` — ساخت خودکار حساب مالی در صورت نبود (تصمیم ۹.۲)

### ۲.۴ Seed (`api/finance.py`)

```python
{"name": "خرید پراپ", "type": CategoryType.EXPENSE, "color": "#E74C3C", "icon": "🛒"},
{"name": "برداشت پراپ", "type": CategoryType.INCOME, "color": "#27AE60", "icon": "💰"},
```
✅ اجرا شد: `created=2 skipped=11 total=13` (id=12 و id=13)

---

## ۳. رفع باگ‌های از قبل موجود

| # | محل | مشکل | اقدام | تست |
|---|-----|------|-------|-----|
| ۱ | `api/prop.py:8-11` | `PropFirmDefaultRules` import نشده بود → `NameError` در `GET /firms/{id}/default-rules` | افزودن به import | ✅ تست ۵ |
| ۲ | `api/client.ts:184` | `getStageWithdrawals` به endpoint ناموجود اشاره می‌کرد | ساخت endpoint `GET /stages/{id}/withdrawals` در بک‌اند (راه‌حل Backend-only) | ✅ تست ۶ |

---

## ۴. نتایج تست

**روش:** FastAPI `TestClient` + DB درون‌حافظه‌ای (`sqlite://` + `StaticPool`) — **DB واقعی دست‌نخورده ماند**.
**نتیجه:** 🎉 **۵۱ PASS / ۰ FAIL** (EXIT=0)

### تست ۱ — ساخت حساب مالی خودکار (۱۰/۱۰ ✅)
```
POST /api/prop/accounts → 200
{'id': 1, 'finance_account_id': 2, 'message': 'اکانت و مرحله ۱ ایجاد شد'}
```
- ✅ `Account` خودکار ساخته شد
- ✅ `Account.name == "FTMO 100K"` (از `account_label`)
- ✅ `Account.type == PROP` | ✅ `currency == USD`
- ✅ `Account.balance == 100000.0` (از `initial_balance`)
- ✅ `Account.prop_firm_id` وصل است
- ✅ `PropAccount.finance_account_id` وصل است
- ✅ Stage1 ساخته شد

### تست ۲ — برداشت + تراکنش مالی (۱۳/۱۳ ✅)
```
POST /api/prop/stages/{id}/withdraw → 200
{'transaction_id': 1, 'source_account_id': 2, 'destination_account_id': 1}
```
- ✅ `Transaction` مالی ساخته شد | ✅ `type == withdrawal`
- ✅ `account_id == destination` (**تصمیم ۹.۱ — گزینه الف**)
- ✅ `from_account_id == حساب مالی پراپ` | ✅ `to_account_id == destination`
- ✅ `related_prop_account_id` وصل است
- ✅ `currency == USD` (تبدیل درست String→Enum)
- ✅ دسته «برداشت پراپ» ساخته و وصل شد
- ✅ موجودی مبدأ: `100000 − 500 = 99500`
- ✅ موجودی مقصد: `1000 + 500 = 1500`
- ✅ `stage.total_withdrawn == 500`
- ✅ `PropWithdrawal.destination_account_id` ذخیره شد
- ✅ **`LedgerTransaction` شخصی ساخته نشد** (حذف موفق منطق شخصی)

### تست ۳ — هزینه خرید پراپ (۷/۷ ✅)
```
POST /api/prop/costs (cost_type=purchase, amount=540) → 200
{'transaction_id': 2, ...}
```
- ✅ `type == purchase` | ✅ دسته «خرید پراپ»
- ✅ `related_prop_account_id` وصل است
- ✅ `account_id == حساب مالی پراپ` (پرداخت‌کننده پیش‌فرض)
- ✅ موجودی پرداخت‌کننده: `99500 − 540 = 98960`
- ✅ `PropCost` ثبت شد

### تست ۴ — `GET /accounts/{id}/finance-account` (۴/۴ ✅)
- ✅ `linked: true` + `id` درست + `balance` درست
- ✅ اکانت ناموجود → `404`

### تست ۵ — رفع باگ ۱ (۱/۱ ✅)
- ✅ `GET /firms/{id}/default-rules` → `200` (بدون `NameError`)

### تست ۶ — رفع باگ ۲ (۲/۲ ✅)
- ✅ `GET /stages/{id}/withdrawals` → `200` + لیست ۱ موردی
- ✅ `destination_account_name == "بانک ملی"`

### تست ۷ — اعتبارسنجی مقصد (۱/۱ ✅)
- ✅ مقصد از نوع `prop` → `400`

### تست ۸ — `create_finance_account=False` (۱/۱ ✅)
- ✅ `finance_account_id == None`

### تست ۹ — برداشت بیش از سود (۱/۱ ✅)
- ✅ `99999` دلار (بیش از ۱۲۰۰ دلار قابل برداشت) → `400`

### تست ۱۰ — `_ensure_finance_account` (۵/۵ ✅)
- ✅ قبل: `finance_account_id == None`
- ✅ برداشت موفق با ساخت خودکار حساب مالی
- ✅ `source_account_id` در response
- ✅ `finance_account_id` بعد از برداشت وصل شد
- ✅ نام حساب جدید `"NoFin 50K"` و موجودی `50000 − 100 = 49900`

---

## ۵. تأیید یکپارچگی داده و Schema

### Migration
```
alembic_version: b7d4e19c2f83   (قبل: 51ea09b4aa3d)
prop_accounts cols:    [... , 'created_at', 'finance_account_id']
prop_withdrawals cols: [... , 'note', 'destination_account_id']
```

### Foreign Keys
```
prop_accounts:    prop_firm_id → prop_firms.id
                  finance_account_id → accounts.id          ✅
prop_withdrawals: prop_stage_id → prop_stages.id
                  destination_account_id → accounts.id      ✅
```

### یکپارچگی داده (DB واقعی، قبل/بعد migration)
| جدول | قبل | بعد |
|------|-----|-----|
| prop_accounts | 2 | 2 |
| prop_stages | 2 | 2 |
| trades | 18 | 18 |
| accounts | 1 | 1 |
| transactions | 0 | 0 |

✅ **صفر از دست رفتن داده** — بدون جدول `_alembic_tmp_*` باقی‌مانده.
✅ **Seed:** `created=2 skipped=11 total=13` (دسته‌ها id=12 «خرید پراپ»، id=13 «برداشت پراپ»)

---

## ۶. نکات و هشدارها

### ۶.۱ ⚠️ Caveat شمارش در گزارش‌های مالی (تصمیم ۹.۱)
با `account_id = destination_account_id`، تابع `GET /api/finance/accounts/{id}/stats` این تراکنش را در `total_expense` حساب **مقصد** می‌شمارد (چون ماژول مالی هر `withdrawal` را expense می‌داند) — در حالی که پول به آن حساب **وارد** شده است.
**رفع ریشه‌ای** نیازمند افزودن مفهوم `transfer` به گزارش‌های فاز ۳ است → **خارج از دامنه فاز ۵**.

### ۶.۲ ⚠️ اثر جانبی حذف منطق شخصی
- برداشت‌های **جدید** پراپ در «دفتر کل شخصی» (`PersonalPage`) دیده **نمی‌شوند**.
- رکوردهای **قدیمی** `ledger_transactions` باقی مانده‌اند (حذف فیزیکی نشد).
- این **مطابق تصمیم گزینه ۲** است.

### ۶.۳ ⚠️ نکته حسابداری موجودی پراپ
`Account.balance` حساب پراپ هنگام برداشت **کاهش** می‌یابد. از نظر حسابداری واقعی، موجودی پراپ پول کاربر نیست بلکه سرمایه در اختیار او نزد شرکت پراپ است. طبق spec پیاده شد؛ پیشنهاد بازنگری در فاز بعد.

### ۶.۴ ⚠️ تغییرات backward-incompatible (نیازمند اصلاح در فرانت‌اند)
- `createPropAccount` → بهتر است `create_finance_account` بفرستد (اختیاری، پیش‌فرض `True`)
- **`withdrawFromStage` امضایش تغییر کرد** → باید `destination_account_id` بفرستد
- `PropPage.tsx:427` هنوز `targetAccountId` (اکانت شخصی) می‌فرستد → **تا اصلاح نشود، برداشت از UI خطای `422` می‌دهد**

### ۶.۵ 🐛 باگ محیطی از قبل موجود (خارج از دامنه فاز ۵)
`backend/app/api/export.py:22` → `import arabic_reshaper` **نصب نیست** → `from app.main import app` شکست می‌خورد.
- **تأثیر روی فاز ۵:** صفر — تست‌ها با روترهای مجزا انجام شد.
- **ولی:** Swagger (`/docs`) تا رفع این مشکل بالا نمی‌آید.
- راه‌حل: `pip install arabic_reshaper` یا اختیاری‌کردن آن import.

### ۶.۶ `getStageWithdrawals` در فرانت
تابع فرانت (`client.ts:184`) **کد مرده** است (هیچ‌جا استفاده نمی‌شود). endpoint بک‌اند ساخته شد تا در آینده قابل استفاده باشد؛ حذف تابع فرانت در فاز فرانت پیشنهاد می‌شود.

---

## ۷. چک‌لیست تکمیل‌شده

- [x] بکاپ `trading_desk.db.backup`
- [x] ۲ فیلد به `models/prop.py`
- [x] فایل migration + `alembic upgrade head`
- [x] تأیید ستون‌ها و FKها
- [x] رفع باگ ۱ (`PropFirmDefaultRules` import)
- [x] helperهای `_to_currency` / `_get_or_create_category` / `_ensure_finance_account`
- [x] `PropAccountCreate` + `create_account`
- [x] `WithdrawalCreate` + بازنویسی `withdraw`
- [x] `PropCostCreate` + `create_cost`
- [x] `GET /accounts/{id}/finance-account`
- [x] `GET /stages/{id}/withdrawals` (رفع باگ ۲)
- [x] ۲ دسته در `DEFAULT_CATEGORIES` + اجرای seed
- [x] تست import + AST
- [x] ۱۰ سناریو تست (۵۱ assertion) — همه PASS
- [x] پاکسازی فایل‌های موقت

---

## ۸. گام بعدی (فاز فرانت‌اند)

| # | فایل | تغییر |
|---|------|-------|
| ۱ | `frontend/src/api/client.ts` | `createPropAccount` + `create_finance_account`؛ `withdrawFromStage` → `destination_account_id`؛ + `getPropAccountFinanceAccount`؛ حذف `getStageWithdrawals` |
| ۲ | `frontend/src/pages/PropPage.tsx` | checkbox «ساخت خودکار حساب مالی» + select «حساب مقصد» + لینک «💰 حساب مالی» |

**پیش‌نیاز:** رفع `arabic_reshaper` برای بالا آمدن کامل اپ/Swagger.

---

## ۹. Rollback

```powershell
cd backend
.\.venv\Scripts\alembic.exe downgrade -1
# در صورت نیاز به بازگردانی کامل دیتابیس:
Copy-Item trading_desk.db.backup trading_desk.db
```

---

> ✅ **فاز ۵ (Backend) کامل شد — ۵۱ تست PASS، صفر خطا، صفر از دست رفتن داده.**

