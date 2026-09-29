# 🔧 PHASE 38.5 — Fix Debt (از 38.3/38.4) · REPORT

> **وضعیت:** ✅ کامل (بدون commit — منتظر تأیید)
> **تاریخ:** ۱۴۰۵/۰۷/۰۷
> **پایه:** `HEAD = 4efd37c` (Phase 38.3-38.4 — push شده)
> **خروجی تست‌ها:** `pytest` → **192 passed (EXIT 0)** · `tsc -b --force` → **EXIT 0** · `vitest run` → **9 passed (EXIT 0)**

---

## ۱. خلاصهٔ اجرایی

هر ۵ بدهیِ گزارش‌شده در فازهای ۳۸.۳/۳۸.۴ بسته شد — و در جریان کار **۳ باگ خاموش جدید** هم کشف و رفع شد:

| # | بدهی | وضعیت | نتیجهٔ کلیدی |
|:--|:---|:---|:---|
| 🔴 ۱ | Migration روی DB خالی crash می‌کرد | ✅ رفع شد | `alembic upgrade head` روی DB خالی → **EXIT 0**، schema **بدون drift** |
| 🔴 ۲ | «حساب مالی» در معاملهٔ دستی بی‌اثر بود | ✅ رفع شد (گزینه A) | **+۳ باگ خاموش کشف شد** (پایین‌تر) + ۴ تست رگرسیون |
| 🟡 ۳ | `classify()` هنوز `"broker"` برمی‌گرداند | ✅ رفع شد | کلیدها → `prop` / `personal` / `simulation` (فرانت هم به‌روز شد) |
| 🟡 ۴ | `PropPage:300` فیلد ناموجود می‌خواند | ✅ رفع شد | کل پل مردهٔ پراپ↔مالی در UI حذف شد |
| 🟢 ۵ | برچسب‌های `broker`/`prop` در FinancePage | ✅ رفع شد | + تایپ `Account` از فیلدهای منسوخه پاک شد |

**🐛 سه باگ خاموش (silent) که در مسیر بدهی ۲ کشف شد:**
1. **`test_type = 'real'` نامعتبر بود** — بک‌اند فقط `backtest/forward/real_personal/real_prop` را می‌پذیرد ⇒ هر تلاش برای ثبت معاملهٔ REAL دستی **همیشه ۴۰۰** می‌گرفت (کل مسیر REAL خراب بود، نه فقط حساب).
2. **گزینهٔ فیلتر `real`** در لیست معاملات ⇒ همیشه صفر نتیجه (قرارداد فاز ۲۷ آن را حذف کرده بود).
3. **پل پراپ↔مالی در `PropPage`** (checkbox + پنل + دکمه) روی endpointهایی کار می‌کرد که **فاز ۲۸ حذفشان کرده بود** ⇒ همیشه ۴۰۴ / «حساب مالی متصل نیست».

✅ **هیچ commit ای زده نشد.**

---

## ۲. 🔴 بدهی ۱ — Fix Migration Bug

### ۲.۱ تشخیص (گام ۱.۱ و ۱.۲)
فایل `backend/migrations/versions/c9d0e1f2a3b4_phase36_indexes.py` — **۷ ایندکس** می‌ساخت و **هیچ چک وجودی نداشت**:
```python
_TRADES_INDEXES = ["prop_stage_id", "personal_trading_account_id", "is_deleted", "close_time"]
_TRANSACTIONS_INDEXES = ["account_id", "date", "type"]

def upgrade() -> None:
    for col in _TRADES_INDEXES:
        op.create_index(op.f(f"ix_trades_{col}"), "trades", [col], unique=False)   # ← بدون IF NOT EXISTS
    for col in _TRANSACTIONS_INDEXES:
        op.create_index(op.f(f"ix_transactions_{col}"), "transactions", [col], unique=False)
```

**کدام ایندکس قبلاً ساخته شده بود؟** (اسکن همهٔ ۱۶ فایل migration با `create_index`)
| ایندکس | سازندهٔ قبلی | تکراری؟ |
|:---|:---|:---|
| `ix_trades_is_deleted` | **`f1a2b3c4d5e6_add_is_deleted_to_trades.py:41`** (فاز ۲۵) | 🔴 **بله** |
| `ix_trades_prop_stage_id` | — (فقط همین migration) | ✅ خیر |
| `ix_trades_personal_trading_account_id` | — | ✅ خیر |
| `ix_trades_close_time` | — | ✅ خیر |
| `ix_transactions_account_id` / `_date` / `_type` | — (فقط `ix_transactions_id` در `51ea09b4aa3d`) | ✅ خیر |

⇒ **علت دقیق crash**: `index ix_trades_is_deleted already exists` (چون زنجیرهٔ migrationها روی DB خالی، اول فاز ۲۵ را اجرا می‌کند و بعد فاز ۳۶ دوباره همان ایندکس را می‌سازد).

### ۲.۲ Fix (گام ۱.۳)
به‌جای `IF NOT EXISTS` خام (که SQLite-specific است)، از **inspector** استفاده شد تا روی هر دیالکتی (SQLite/PG) و هم روی DB خالی و هم DB موجود درست کار کند:
```python
from sqlalchemy import inspect

def _existing_indexes(table: str) -> set:
    """نام ایندکس‌های موجود روی جدول (برای idempotent بودن migration)."""
    return {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table)}

def _create_index_if_missing(index_name: str, table: str, column: str) -> None:
    if index_name in _existing_indexes(table):
        return
    op.create_index(op.f(index_name), table, [column], unique=False)

def _drop_index_if_exists(index_name: str, table: str) -> None:
    if index_name not in _existing_indexes(table):
        return
    op.drop_index(op.f(index_name), table_name=table)
```
`upgrade()`/`downgrade()` حالا از این helperها استفاده می‌کنند ⇒ **هر ۷ ایندکس idempotent شدند** (نه فقط آن یکی) ⇒ اگر در آینده هم migration دیگری ایندکسی را بسازد، این فایل نمی‌شکند.
همچنین docstring فایل با توضیح فاز ۳۸.۵ به‌روز شد.

### ۲.۳ تست (گام ۱.۴)
```text
cd backend
Copy-Item trading_desk.db trading_desk.db.bak_before_fix
Remove-Item trading_desk.db            → deleted: True
venv\Scripts\python.exe -m alembic upgrade head
   … Running upgrade b8c9d0e1f2a3 -> c9d0e1f2a3b4, phase36_indexes   ← بدون خطا
UPGRADE_EXIT=0                                                       ✅
venv\Scripts\python.exe -m alembic current
   c9d0e1f2a3b4 (head)                                               ✅
```
> 🎯 **قبل از fix** همین دستور با `sqlite3.OperationalError: index ix_trades_is_deleted already exists` کرش می‌کرد.

### ۲.۴ اعتبارسنجی عمیق‌تر (schema drift)
DB ساخته‌شده با **migration** با DB ساخته‌شده با **`create_all`** (فاز ۳۸.۴) مقایسه شد:
```text
TABLES   migration=30   create_all=30    only-in-* = []         ✅
INDEXES  migration=59   create_all=59    only-in-* = []         ✅
COLUMN SETS ........... REAL mismatches = []                    ✅
order-only diffs ..... analysis_results, analysis_runs, prop_withdrawals,
                       strategy_versions, trades  (فقط «ترتیب» ستون‌ها)
```
> 📌 تفاوت ترتیب طبیعی است: migrationها با `ALTER TABLE` ستون جدید را **آخر** اضافه می‌کنند، ولی `create_all` ستون‌ها را به ترتیب مدل می‌سازد. **مجموعهٔ ستون‌ها یکسان است** ⇒ صفر drift.

### ۲.۵ ✅ مزیت جانبی
`app/main.py` در startup هم `alembic upgrade head` می‌زند ⇒ حالا **نصب تازه (fresh install) هم بدون خطا بالا می‌آید**. این با یک smoke واقعی تأیید شد:
```text
🚀 MokTradeDesk API started
✅ Database migrations applied      ← دیگر exception نمی‌دهد
```
---

## ۳. 🔴 بدهی ۲ — Fix TradesPage (ثبت معاملهٔ دستی)

### ۳.۱ تشخیص (گام ۲.۲) — قرارداد واقعی بک‌اند
**`POST /api/trades/manual`** (`backend/app/api/trades.py:597` + `ManualTradeCreate:57`):
```python
class ManualTradeCreate(BaseModel):
    symbol, direction, open_time, close_time, open_price, close_price,
    size, sl, tp, pnl, r_multiple, commission, swap
    # Classification:
    test_type: str = "backtest"
    version_id: Optional[int]
    personal_trading_account_id: Optional[int]     # ← نام واقعی
    prop_stage_id: Optional[int]
```
```python
test_type_map = {"backtest":…, "forward":…, "real_personal":…, "real_prop":…}
test_type = test_type_map.get(data.test_type)
if not test_type:
    raise HTTPException(400, "نوع تست نامعتبر")     # ← 'real' ⇒ همیشه ۴۰۰
```
**فرانت (قبل از fix) چه می‌فرستاد؟**
```ts
test_type: 'real',                                    // ❌ نامعتبر
finance_account_id: manualTrade.finance_account_id,   // ❌ فیلد ناموجود ⇒ Pydantic نادیده می‌گیرد
prop_stage_id: manualTrade.prop_stage_id,             // ✅ ولی بدون انتخابگر مستقل
```
**چرا «حساب مالی» بی‌اثر بود؟** سه لایه:
1. `finance_account_id` در schema بک‌اند **وجود ندارد** ⇒ بی‌صدا دور ریخته می‌شد.
2. Dropdown از `getFinanceAccounts()` (حساب‌های **مالی**) پر می‌شد و حتی `a.broker_name` را نمایش می‌داد که فاز ۲۸ حذفش کرده بود.
3. 🔥 **باگ پنهان‌تر:** چون `test_type='real'` نامعتبر بود، درخواست **قبل از** رسیدن به منطق classification با **۴۰۰** رد می‌شد ⇒ کل مسیر REAL دستی از ابتدا کار نمی‌کرد.

### ۳.۲ انتخاب گزینه (گام ۲.۳)
> ✅ **گزینه A** انتخاب شد — با یک تکمیل ضروری.

**دلیل:** بک‌اند `personal_trading_account_id` را دارد و `TradeValidator` دقیقاً می‌گوید:
| test_type | version_id | personal_trading_account_id | prop_stage_id |
|:---|:---|:---|:---|
| BACKTEST / FORWARD | اجباری | ممنوع | ممنوع |
| REAL_PERSONAL | اجباری | **اجباری** | ممنوع |
| REAL_PROP | اجباری | ممنوع | **اجباری** |

- ❌ گزینه B (افزودن `finance_account_id` به بک‌اند) رد شد: خلاف تصمیم معماری فاز ۲۷/۲۸ است (Trade نباید به حساب **مالی** وصل شود).
- ❌ گزینه C (حذف فیلد از فرانت) رد شد: قابلیت REAL_PERSONAL لازم است و endpoint آن (`/api/trading/accounts`) وجود دارد.
- ⚠️ **تکمیل:** صرفاً تغییر نام کافی نبود؛ `test_type` هم باید به دو مقدار معتبر `real_personal`/`real_prop` تفکیک می‌شد و برای REAL_PROP یک **انتخابگر مرحلهٔ پراپ** اضافه می‌شد (قبلاً در فرم نبود).
### ۳.۳ Fix — `client.ts` (گام ۲.۴)
```diff
-  // ⚠️ فاز ۳۸.۴ — این فیلد در بک‌اند وجود ندارد (نام درست: `personal_trading_account_id`).
-  // عمداً دست‌نخورده ماند تا `TradesPage` نشکند؛ مهاجرت کامل آن به یک فاز جدا نیاز دارد.
-  finance_account_id?: number;
+  // فاز ۳۸.۵: جایگزین منسوخ `finance_account_id` (که در بک‌اند وجود نداشت).
+  // قرارداد Trade (فاز ۲۷): REAL_PERSONAL ⇒ personal_trading_account_id، REAL_PROP ⇒ prop_stage_id
+  personal_trading_account_id?: number;
```
و **دو API جدید** در بخش Trading (که قبلاً در کلاینت نبودند):
```ts
export const getBrokers = () => api.get('/api/trading/brokers');

/** حساب‌های معاملاتی شخصی (هر کدام روی یک بروکر) — برای انتخاب دامنهٔ معاملهٔ REAL_PERSONAL */
export const getPersonalTradingAccounts = (params?: { broker_id?: number }) =>
  api.get('/api/trading/accounts', { params });
```

### ۳.۴ Fix — `TradesPage.tsx`
| # | تغییر |
|:--|:---|
| ۱ | `getFinanceAccounts` → `getPersonalTradingAccounts` در import و `loadFilters` |
| ۲ | state: `financeAccounts` → **`personalAccounts`** (دیگر فیلتر `type !== 'prop'` لازم نیست) |
| ۳ | `manualTrade.finance_account_id` → **`personal_trading_account_id`** (state + reset) |
| ۴ | `test_type` select: `backtest/forward/real` → **`backtest/forward/real_personal/real_prop`** |
| ۵ | فیلتر لیست معاملات: گزینهٔ مردهٔ `real` → **`real_personal` + `real_prop`** |
| ۶ | `getTestTypeLabel`: برچسب‌های ۴ مقدار جدید (+ کلید `real` برای دادهٔ قدیمی) |
| ۷ | اعتبارسنجی فرم: **آینهٔ `TradeValidator`** (XOR حساب شخصی ↔ مرحله پراپ) |
| ۸ | JSX: select «حساب مالی» → **«حساب معاملاتی شخصی»** (فقط برای `real_personal`) با نمایش `account_label — broker_name` |
| ۹ | JSX: دو بلوک پراپ ادغام و فقط برای **`real_prop`** نمایش داده می‌شود |
| ۱۰ | payload: ارسال `personal_trading_account_id` + `prop_stage_id` |

نمونهٔ اعتبارسنجی جدید:
```tsx
const isRealPersonal = manualTrade.test_type === 'real_personal';
const isRealProp = manualTrade.test_type === 'real_prop';

if (isRealPersonal && !manualTrade.personal_trading_account_id) {
  setError('برای معامله‌ی رییل شخصی، انتخاب «حساب معاملاتی شخصی» الزامی است'); return;
}
if (isRealProp && !manualTrade.prop_stage_id) {
  setError('برای معامله‌ی رییل پراپ، انتخاب «مرحله‌ی پراپ» الزامی است'); return;
}
if (!isRealPersonal && !isRealProp && (manualTrade.prop_stage_id || manualTrade.personal_trading_account_id)) {
  setError('برای Backtest و Forward، نباید دامنهٔ معاملاتی انتخاب شود'); return;
}
```

### ۳.۵ 🔬 کشف جانبی: آیا فیلتر `test_type` بک‌اند case-sensitive است؟
چون مقادیر Enum در SQLite به‌صورت **NAME** (`'BACKTEST'`) ذخیره می‌شوند، احتمال داشت فیلتر با lowercase کار نکند. با آزمون تجربی روی DB در حافظه بررسی شد:
```text
RAW stored value: [('BACKTEST',)]
  filter 'backtest'   -> 1        ← value (lowercase) هم کار می‌کند
  filter 'BACKTEST'   -> 1        ← name (uppercase)
  filter 'forward'    -> 0
  filter 'real'       -> 0        ← مقدار حذف‌شدهٔ قرارداد فاز ۲۷
```
⇒ ✅ فیلتر `backtest/forward` سالم بود؛ فقط گزینهٔ `real` مرده بود (رفع شد).

### ۳.۶ تست (گام ۲.۵) + ۴ تست رگرسیون جدید
به `backend/tests/test_trades.py` اضافه شد:
| تست | چه چیزی را قفل می‌کند |
|:---|:---|
| `test_manual_trade_real_personal_accepts_personal_trading_account` | ثبت REAL_PERSONAL با `personal_trading_account_id` → ۲۰۰ + ذخیرهٔ درست (`test_type`, `personal_trading_account_id`, نام حساب، `prop_stage_id=None`) |
| `test_manual_trade_legacy_real_test_type_rejected` | مقدار قدیمی `test_type='real'` → **۴۰۰** (رگرسیون‌گیرِ باگ خاموش) |
| `test_manual_trade_real_prop_requires_prop_stage` | REAL_PROP بدون مرحله → ۴۰۰ |
| `test_manual_trade_backtest_rejects_personal_account` | BACKTEST با حساب شخصی → ۴۰۰ |

```text
pytest tests/test_trades.py -q  →  23 passed (19 قبل + ۴ جدید) · EXIT 0
```
---

## ۴. 🟡 بدهی ۳ — Clean `analytics.py` (classify / by_source)

### ۴.۱ تشخیص (گام ۳.۲)
```python
# قبل
def classify(t):
    if t.prop_stage_id:            return "prop"
    if t.personal_trading_account_id: return "broker"     # ← نام منسوخ
    return "personal"                                     # ← معنایش: BACKTEST/FORWARD!
```
- **آیا کسی از آن استفاده می‌کند؟** ✅ بله — `classify()` در خط ۴۱۲ روی هر معاملهٔ «دیروز» صدا زده می‌شود و `by_source` را پر می‌کند؛ خروجی از `GET /api/analytics/yesterday` به فرانت می‌رود.
- **مصرف‌کنندهٔ نهایی (فقط یک جا):** `DashboardPage.tsx:506-521` (بَج‌های شمارش + `MiniBars`).
- **`"broker"` از کجا می‌آمد؟** از فاز ۱۴.۲ که «بروکر» یک `AccountType` بود. فاز ۲۸ آن را به `PersonalTradingAccount` منتقل کرد ولی کلید JSON به‌روز نشد. بدتر: fallback هم `"personal"` نام داشت، در حالی که آن دسته در واقع معاملات **BACKTEST/FORWARD** (بدون دامنهٔ واقعی) است.

### ۴.۲ Fix (گام ۳.۳)
```diff
-    # تفکیک منبع بر اساس دامنهٔ معامله (فاز ۲۸)
+    # تفکیک منبع بر اساس دامنهٔ معامله (فاز ۲۸) — فاز ۳۸.۵: کلیدها با قرارداد فاز ۲۷ هم‌نام شدند
+    #   prop       → REAL_PROP
+    #   personal   → REAL_PERSONAL   (قبلاً به‌اشتباه «broker» بود؛ حساب معاملاتی شخصی روی بروکر)
+    #   simulation → BACKTEST / FORWARD  (بدون دامنهٔ واقعی؛ قبلاً «personal»)
     def classify(t):
         if t.prop_stage_id:
             return "prop"
         if t.personal_trading_account_id:
-            return "broker"
-        return "personal"
+            return "personal"
+        return "simulation"

     by_source = {
         "prop":       {...},
-        "broker":     {...},
-        "personal":   {...},
+        "personal":   {...},
+        "simulation": {...},
     }
```
**فرانت (`DashboardPage.tsx`) هم در همان تغییر به‌روز شد:**
```diff
-{(['prop', 'broker', 'personal'] as const).map((k) => (
-  ... {k === 'prop' ? '🏢 پراپ' : k === 'broker' ? '📊 بروکر' : '👤 شخصی'} ...
+{(['prop', 'personal', 'simulation'] as const).map((k) => (
+  ... {k === 'prop' ? '🏢 پراپ' : k === 'personal' ? '👤 شخصی' : '🧪 شبیه‌سازی'} ...
-  { label: 'بروکر', value: Math.abs(yesterday.by_source?.broker?.pnl ?? 0) },
-  { label: 'شخصی',  value: Math.abs(yesterday.by_source?.personal?.pnl ?? 0) },
+  { label: 'شخصی',      value: Math.abs(yesterday.by_source?.personal?.pnl ?? 0) },
+  { label: 'شبیه‌سازی', value: Math.abs(yesterday.by_source?.simulation?.pnl ?? 0) },
```
> ⚠️ **این یک تغییر شکننده در کلید JSON است** (`broker`→`personal`, `personal`→`simulation`) که بک‌اند و فرانت **در یک تغییر** هم‌زمان به‌روز شدند تا ناسازگاری نماند.

### ۴.۳ تأیید (smoke واقعی روی اپ)
```text
GET /api/analytics/yesterday → 200
by_source keys = ['personal', 'prop', 'simulation']       ✅ دیگر «broker» وجود ندارد
```
> 💡 این smoke یک **مزیت جانبی بدهی ۱** را هم تأیید کرد: startup اپ حالا `✅ Database migrations applied` می‌دهد (قبلاً exception می‌خورد).

---

## ۵. 🟡 بدهی ۴ — Clean `PropPage.tsx`

### ۵.۱ تشخیص (گام ۴.۱) — بزرگ‌تر از یک خط!
`PropPage.tsx:300` (کد قبل):
```tsx
setSuccessMessage(
  createFinanceAccount && res.data?.finance_account_id      // ← همیشه undefined
    ? 'اکانت پراپ + حساب مالی ساخته شد'
    : 'اکانت پراپ ساخته شد'
);
```
بررسی عمیق‌تر نشان داد **کل «پل پراپ ↔ مالی» در UI مرده است**:
| نقطه | وضعیت واقعی |
|:---|:---|
| `POST /api/prop/accounts` + `create_finance_account` | ❌ `PropAccountCreate` این فیلد را **ندارد** (فاز ۲۸) ⇒ نادیده گرفته می‌شد |
| `res.data.finance_account_id` | ❌ پاسخ بک‌اند فقط `{id, message}` است (`prop.py:284`) ⇒ همیشه falsy |
| `GET /api/prop/accounts/{id}/finance-account` | ❌ **حذف شده** — کامنت خود کد: `prop.py:1182 — endpointهای «حساب مالی متناظر پراپ» حذف شدند` |
| `POST /api/prop/accounts/{id}/finance-account` | ❌ همان ⇒ دکمهٔ «💰 ساخت حساب مالی» همیشه ۴۰۴ |
| پنل «حساب مالی متناظر» | ❌ همیشه «حساب مالی متصل نیست» نشان می‌داد |

### ۵.۲ Fix (گام ۴.۲)
| # | حذف/اصلاح |
|:--|:---|
| ۱ | `setSuccessMessage('اکانت پراپ ساخته شد')` — ساده و درست (منطبق بر پاسخ واقعی بک‌اند) |
| ۲ | حذف checkbox «💰 ساخت خودکار حساب مالی» + ارسال `create_finance_account` |
| ۳ | حذف پنل «حساب مالی متناظر» + دکمهٔ «ساخت حساب مالی» |
| ۴ | حذف `handleCreateFinanceAccount` و `loadFinanceInfo` |
| ۵ | حذف stateهای مرده: `createFinanceAccount` / `financeInfo` / `loadingDetail` |
| ۶ | حذف `Skeleton` (فقط در همان پنل استفاده می‌شد) و `await loadFinanceInfo(accountId)` از `loadAccountDetail` |
| ۷ | `client.ts`: حذف `getPropAccountFinanceAccount` / `createPropFinanceAccount` / فیلد `create_finance_account` |
| ۸ | متغیر بی‌استفادهٔ `const res = await createPropAccount(...)` → `await createPropAccount(...)` |

> ✅ **آنچه حفظ شد:** «برداشت پراپ» (Modal + `withdrawFromStage` + `getFinanceAccountsForDestination`) — این مسیر **سالم** است و طبق فاز ۲۸، تنها راه ورود پول از پراپ به FINANCE است.
> 🔧 **تعمیر جانبی:** در جریان ادیت، یک بلوک کد اشتباهاً بازنویسی شد (`handleConfirmWithdraw` تکراری + گم‌شدن `return (`) که **بلافاصله شناسایی و بازگردانی شد** — قبل از اجرای تست‌ها.
---

## ۶. 🟢 بدهی ۵ — برچسب‌های `broker`/`prop` در FinancePage

### ۶.۱ تشخیص (گام ۵.۱) — همهٔ موارد `broker`/`prop` در `FinancePage.tsx`
| خط | کد (قبل) | حکم |
|:---|:---|:---|
| ۷۶ | `ACCOUNT_TYPE_LABELS = { …, broker: '📊', prop: '🏢', … }` | ❌ **منسوخ** — `AccountType` از فاز ۲۸ این دو را ندارد |
| ۸۲ | `ACCOUNT_TYPE_NAMES = { …, broker: 'بروکر', prop: 'پراپ', … }` | ❌ **منسوخ** |
| ۵۷-۵۸ | تایپ `Account`: `broker_name?` / `prop_firm_name?` / `prop_firm_id?` | ❌ **منسوخ** (فاز ۲۸ از `accounts` حذفشان کرد) |
| ۷۶,۸۱,۱۱۳۴ | `exchange` | ✅ درست — `AccountType.EXCHANGE` (صرافی) معتبر است |
| ۸۹,۹۸,۱۰۳ | `transfer` | ✅ فاز ۳۸.۴ (جانشین exchange) |

### ۶.۲ Fix (گام ۵.۲)
```diff
 const ACCOUNT_TYPE_LABELS: Record<string, string> = {
-  bank: '🏦', exchange: '🔄', crypto_wallet: '₿', broker: '📊', prop: '🏢',
+  bank: '🏦', exchange: '🔄', crypto_wallet: '₿',
   card: '💳', cash: '💵', trust_wallet: '🤝',   // فاز ۳۸.۲
+  // فاز ۳۸.۵: `broker`/`prop` حذف شدند (از فاز ۲۸ در AccountType وجود ندارند)
 };

 const ACCOUNT_TYPE_NAMES: Record<string, string> = {
   bank: 'بانک', exchange: 'صرافی', crypto_wallet: 'کیف‌پول دیجیتال',
-  broker: 'بروکر', prop: 'پراپ',
   card: 'کارت بانکی', cash: 'پول نقد', trust_wallet: 'کیف پول Trust',  // فاز ۳۸.۲
+  // فاز ۳۸.۵: `broker`/`prop` حذف شدند
 };

 type Account = {
   id: number; name: string; type: string; currency: string;
-  balance: number; card_number?: string; broker_name?: string;
-  prop_firm_name?: string; prop_firm_id?: number | null; created_at?: string;
+  balance: number; card_number?: string; created_at?: string;
+  // فاز ۳۸.۵: `broker_name`/`prop_firm_name`/`prop_firm_id` حذف شدند (فیلد منسوخهٔ فاز ۲۸)
 };
```
> 🛡️ **بی‌خطر بودن حذف برچسب‌ها:** مصرف‌کننده‌ها همیشه `X[a.type] || fallback` هستند
> (`ACCOUNT_TYPE_LABELS[a.type] || '❓'`) ⇒ حذف کلیدهای غیرقابل‌وقوع هیچ نمایشی را نمی‌شکند.
---

## ۷. ✅ نتیجهٔ تست‌ها (گام ۲.۵)

### ۷.۱ بک‌اند
```text
cd backend
venv\Scripts\python.exe -m pytest -q -p no:warnings
........................................................................ [ 37%]
........................................................................ [ 75%]
................................................                         [100%]
PYTEST_EXIT=0            →  192 passed
```
| مقایسه | تعداد |
|:---|:---|
| baseline (قبل از ۳۸.۵) | ۱۸۸ |
| **بعد از ۳۸.۵** | **۱۹۲** (= ۱۸۸ + ۴ تست جدید) |
| شکست/رگرسیون | **صفر** ✅ |

### ۷.۲ فرانت‌اند
```text
cd frontend
npx tsc -b --force   →  TSC_EXIT=0        (بدون هیچ خطا)
npx vitest run       →  VITEST_EXIT=0
  ✓ src/__tests__/utils.test.ts (4 tests)
  ✓ src/__tests__/components.test.tsx (5 tests)
  Test Files  2 passed (2)      Tests  9 passed (9)
```

### ۷.۳ تست‌های هدفمند + smoke
| بررسی | نتیجه |
|:---|:---|
| `alembic upgrade head` روی DB خالی | ✅ EXIT 0 · `c9d0e1f2a3b4 (head)` |
| drift اسکیما (migration vs create_all) | ✅ ۳۰ جدول / ۵۹ ایندکس / صفر اختلاف ستونی |
| `pytest tests/test_trades.py` | ✅ 23 passed |
| `GET /api/analytics/yesterday` | ✅ 200 · keys = `prop, personal, simulation` |
| smoke startup اپ | ✅ `✅ Database migrations applied` (بدون exception) |
| اسکن نهایی: مراجع باقی‌ماندهٔ توابع حذف‌شده | ✅ صفر |

---

## ۸. 📁 فایل‌های تغییر یافته (۸ فایل)

```text
 backend/app/api/analytics.py                                |  11 +-
 backend/migrations/versions/c9d0e1f2a3b4_phase36_indexes.py |  34 +++++-
 backend/tests/test_trades.py                                |  81 ++++++++++
 frontend/src/api/client.ts                                  |  26 +++--
 frontend/src/pages/DashboardPage.tsx                        |   6 +-
 frontend/src/pages/FinancePage.tsx                          |   9 +-
 frontend/src/pages/PropPage.tsx                             |  98 +---------
 frontend/src/pages/TradesPage.tsx                           | 122 +++++-----
 8 files changed, 210 insertions(+), 177 deletions(-)
```
| بدهی | فایل‌ها |
|:---|:---|
| ۱ | `migrations/versions/c9d0e1f2a3b4_phase36_indexes.py` |
| ۲ | `frontend/src/api/client.ts`, `frontend/src/pages/TradesPage.tsx`, `backend/tests/test_trades.py` |
| ۳ | `backend/app/api/analytics.py`, `frontend/src/pages/DashboardPage.tsx` |
| ۴ | `frontend/src/pages/PropPage.tsx`, `frontend/src/api/client.ts` |
| ۵ | `frontend/src/pages/FinancePage.tsx` |

**DB (بیرون از git):** `trading_desk.db` (بازسازی‌شده با migration — تمیز) + دو بکاپ:
`trading_desk.db.bak_before_cleanbreak` (فاز ۳۸.۴) و `trading_desk.db.bak_before_fix` (فاز ۳۸.۵)

---

## ۹. 📌 بدهی‌های باقی‌مانده (خارج از دامنهٔ ۳۸.۵)

| # | مورد | شدت | توضیح |
|:--|:---|:--|:---|
| ۱ | **`app/api/broker.py` + router `/api/broker`** | 🟡 متوسط | در `main.py:164` mount شده؛ بازماندهٔ فاز ۲۰ (دوران `AccountType.BROKER`). فرانت مصرفش **نمی‌کند** (`client.ts` هیچ صدازنی به `/api/broker` ندارد) ⇒ کاندیدای حذف در فاز تمیزکاری. |
| ۲ | **کلیدهای `"broker"` در `finance.py:1182,1220`** | 🟢 کم | مربوط به **موجودی بروکر** (از `PersonalTradingAccount.current_balance`) در `spendable-assets`/`real-pnl` — **معتبر و مصرف‌شده** در داشبورد ⇒ عمداً حفظ شد (نباید با بدهی ۳ اشتباه شود). |
| ۳ | **تب «حساب معاملاتی شخصی» در `AnalysisPage`** | 🟢 کم | بک‌اند مسیرهای `/analyze|analysis/personal-account/{id}` را دارد ولی فرانت وصل نشده (جانشین واقعی تب بروکر حذف‌شده در ۳۸.۴). |
| ۴ | **`ImportPage` — کلاسیفیکیشن REAL_PERSONAL** | 🟡 متوسط | `PHASE27_TRADE_CONTRACT.md` گفته بود مقصد REAL_PERSONAL از منبع جدید پر شود؛ باید بررسی شود آیا `ImportPage` هم مثل `TradesPage` به منبع/فیلد منسوخه اشاره می‌کند. |
| ۵ | **`services/finance_sync_service.py`** | 🟢 کم | همچنان no-op از فاز ۲۸ (نیازمند تصمیم طراحی). |
| ۶ | **`GET /api/analytics/yesterday` کل جدول را می‌خواند** | 🟢 کم | بدهی قدیمی `BE-12` در `COMPREHENSIVE_REVIEW.md` (بهینه‌سازی، نه باگ). |

---

## ۱۰. ✅ تأیید نهایی Phase 38.5

| بررسی | نتیجه |
|:---|:---|
| بدهی ۱ — migration idempotent + تست روی DB خالی | ✅ |
| بدهی ۲ — `personal_trading_account_id` + تفکیک `real_personal`/`real_prop` + انتخابگر مرحله | ✅ |
| بدهی ۲ — `client.ts` (حذف `finance_account_id` منسوخ + افزودن APIهای Trading) | ✅ |
| بدهی ۳ — `classify()` + `by_source` + Dashboard هم‌زمان | ✅ |
| بدهی ۴ — حذف کامل پل مردهٔ پراپ↔مالی در `PropPage` + `client.ts` | ✅ |
| بدهی ۵ — برچسب‌های `broker`/`prop` + تایپ `Account` | ✅ |
| `pytest` | ✅ **192 passed · EXIT 0** (baseline ۱۸۸) |
| `tsc -b --force` | ✅ **EXIT 0** |
| `vitest run` | ✅ **9 passed · EXIT 0** |
| commit | ✅ **زده نشد** |

⏸️ **پایان Phase 38.5 — منتظر تأیید کاربر برای commit.**