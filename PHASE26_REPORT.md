# 📋 گزارش فاز ۲۶ — بهبود عملکرد + کیفیت

> **تاریخ:** ۱۴۰۵/۰۷/۰۶ (2026-09-28) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۱۰۱ تست بک‌اند پاس · ✅ ۹ تست فرانت پاس · ✅ `tsc -b --force` (exit 0) · ✅ `npm run build` (exit 0) · ✅ `alembic upgrade head` (exit 0)
> **قوانین:** ✅ Auto-approve غیرفعال · ✅ ترتیب ۱→۱۱ رعایت شد

---

## ۰. بررسی وضعیت فعلی (قبل از تغییر)

| # | مورد | وضعیت قبل |
|---|---|---|
| ۱ | `POST /api/trades/{id}/restore` | ❌ وجود نداشت |
| ۲ | `GET /api/trades/?include_deleted` | ❌ وجود نداشت؛ serializer هم `is_deleted` برنمی‌گرداند |
| ۳ | `core/database.py` | `create_engine(...)` بدون PRAGMA — `journal_mode=delete` |
| ۴ | `main.py` | `@app.on_event("startup"/"shutdown")` (منسوخ) |
| ۵ | `core/database.py` | `from sqlalchemy.ext.declarative import declarative_base` + `Base = declarative_base()` |
| ۶ | `models/strategy.py` | `StrategyVersion.test_type = Column(String, nullable=True)` |
| ۷ | `models/strategy.py` | `CustomTimeInterval.is_active = Column(Integer, default=1)`، `TimePoint.is_active` همان |
| ۸ | `requirements.txt` | ۱۸ بسته **بدون نسخه** |
| ۹ | ریشهٔ پروژه | `README.md` ❌ نداشت |

**بررسی ریسک داده:**

| جدول | تعداد رکورد در DB واقعی |
|---|---|
| `strategy_versions` | **۰** |
| `custom_time_intervals` | **۰** |
| `time_points` | **۰** |

➡️ تغییر نوع ستون‌ها **بدون ریسک دادهٔ موجود**؛ با این حال migration شامل تبدیل داده هم هست.

---

## ۱. Restore endpoint

### `backend/app/api/trades.py` (جدید، خط ۵۹۱)

```python
@router.post("/{trade_id}/restore")
def restore_trade(trade_id: int, db: Session = Depends(get_db)):
    """بازگردانی معامله‌ی حذف‌شده (Soft Delete → is_deleted = False)."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="معامله پیدا نشد")

    if not trade.is_deleted:
        return {"message": "این معامله حذف نشده بود", "count": 0}   # idempotent

    trade.is_deleted = False
    db.commit()
    return {"message": "معامله بازگردانی شد", "count": 1}
```

**رفتار:** حذف‌شده → `count=1` · حذف‌نشده → `count=0` (idempotent) · ناموجود → `404`

---

## ۲. نمایش حذف‌شده‌ها

### الف) Backend — `GET /api/trades/?include_deleted=true`

```python
def get_trades(
    ...
    search: Optional[str] = None,
    include_deleted: bool = False,      # ← جدید
    pnl_min: Optional[float] = None,
    ...
):
    query = db.query(Trade)
    # فاز ۲۵: حذف‌شده‌ها پیش‌فرض پنهان — فاز ۲۶: با include_deleted دیده می‌شوند
    if not include_deleted:
        query = query.filter(Trade.is_deleted == False)
```

**افزودن `is_deleted` به serializerها:** `_serialize_trade_summary` (خط ۱۵۷) و `_serialize_trade_detail` (خط ۱۸۹) هر دو فیلد `"is_deleted": bool(t.is_deleted)` گرفتند.

### ب) Frontend API — `client.ts`

```typescript
export const getTrades = (params?: { ..., include_deleted?: boolean; ... })

// فاز ۲۶: بازگردانی معامله‌ی حذف‌نرم‌شده
export const restoreTrade = (tradeId: number) =>
  api.post(`/api/trades/${tradeId}/restore`);
```

### ج) Frontend UI — `TradesPage.tsx`

| # | تغییر |
|---|---|
| ۱ | State جدید: `const [showDeleted, setShowDeleted] = useState(false)` |
| ۲ | Checkbox «🗑️ نمایش حذف‌شده‌ها» در پنل فیلترها |
| ۳ | `include_deleted: showDeleted || undefined` در `loadTrades` + افزودن `showDeleted` به وابستگی `useEffect` |
| ۴ | فیلد `is_deleted?: boolean` در interface `Trade` |
| ۵ | **رنگ متفاوت ردیف:** `bg-[var(--loss)]/10 opacity-70` + آیکون 🗑️ کنار شناسه |
| ۶ | دکمهٔ **♻️ بازگردانی** (به‌جای ✏️ ویرایش) برای ردیف‌های حذف‌شده |
| ۷ | `handleRestoreTrade()` — فراخوانی `restoreTrade` + پیام موفقیت + reload |

---

## ۳. WAL در `database.py`

```python
_IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _IS_SQLITE else {},
)

if _IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()
```

**مزیت:** WAL خواندن و نوشتن هم‌زمان را ممکن می‌کند → کاهش تأخیر قفل در بار سنگین (تحلیل + Import + API).

**تأیید عملی:** `PRAGMA journal_mode` → **`wal`** ✅

---

## ۴. `on_event` → `lifespan`

**قبل:**
```python
app = FastAPI(title="MokTradeDesk API", version="1.0")

@app.on_event("startup")
def startup(): ...

@app.on_event("shutdown")
def shutdown(): ...
```

**بعد:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MokTradeDesk API started")
    # ... auto-migrate (فاز ۱۸) ...
    # ... initial backup + auto-backup thread (فاز ۱۷) ...
    yield
    _backup_stop.set()
    logger.info("👋 MokTradeDesk API stopped")

app = FastAPI(title="MokTradeDesk API", version="1.0", lifespan=lifespan)
```

**مزیت:** رفع `DeprecationWarning: on_event is deprecated` (FastAPI) ✅ — هر دو بلوک `@app.on_event` حذف شدند.

---

## ۵. `declarative_base` → `DeclarativeBase`

**قبل:**
```python
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
```

**بعد:**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """کلاس پایهٔ همهٔ مدل‌ها (سبک SQLAlchemy 2.0)."""
    pass
```

**مزیت:** رفع `MovedIn20Warning: declarative_base() is deprecated` ✅
**سازگاری:** `Base.metadata` و همهٔ مدل‌ها بدون تغییر کار می‌کنند (تأیید با import + ۱۰۱ تست).

---

## ۶. `StrategyVersion.test_type` — String → Enum

**قبل (خط ۸۲):**
```python
# فاز 24: test_type for filtering in UI (BACKTEST / FORWARD / REAL)
test_type = Column(String, nullable=True)
```

**بعد (خط ۸۳):**
```python
# فاز 26: test_type از String به Enum تغییر یافت (BACKTEST / FORWARD / REAL)
# مقدار در دیتابیس به‌صورت NAME ذخیره می‌شود ('BACKTEST' / 'FORWARD' / 'REAL')
test_type = Column(Enum(TestType), nullable=True)
```

### به‌روزرسانی کد مصرف‌کننده (`api/strategies.py`)

| محل | قبل | بعد |
|---|---|---|
| خط ۲۶ (جدید) | — | helper `_parse_test_type(value)` |
| `get_strategy_versions` | `"test_type": v.test_type` | `enum_value(v.test_type)` |
| `create_version` | `version.test_type.lower() if ...` | `_parse_test_type(version.test_type)` |
| `fork_version` | `_raw_test_type.lower() if ...` | `_parse_test_type(_raw_test_type)` |
| خروجی fork | `forked.test_type` | `enum_value(forked.test_type)` |

```python
def _parse_test_type(value) -> Optional[TestType]:
    """تبدیل ورودی test_type (رشته یا Enum) به TestType — فاز ۲۶."""
    if value is None or value == "":
        return None
    if isinstance(value, TestType):
        return value
    try:
        return TestType(str(value).lower())
    except ValueError:
        return None
```

> **حفظ قرارداد Frontend:** ورودی/خروجی API همچنان رشتهٔ **حروف کوچک** (`backtest`/`forward`/`real`) است؛ فقط ذخیره‌سازی در DB به NAME تغییر کرد.

---

## ۷. `is_active` — Integer → Boolean

**قبل:**
```python
class CustomTimeInterval(Base):
    is_active = Column(Integer, default=1)

class TimePoint(Base):
    is_active = Column(Integer, default=1)
```

**بعد:**
```python
is_active = Column(Boolean, default=True)  # فاز ۲۶: Integer → Boolean
```

### به‌روزرسانی مصرف‌کننده‌ها

| فایل | قبل | بعد |
|---|---|---|
| `services/analysis_service.py:629` | `CustomTimeInterval.is_active == 1` | `.is_(True)` |
| `schemas/analytics.py:19,33` | `is_active: int = 1` / `int` | `bool = True` / `bool` |
| `schemas/analytics.py:48,57` | `is_active: int = 1` / `int` | `bool = True` / `bool` |

> `seed-gold` / `seed-dji` مقدار `is_active` نمی‌دهند → از `default=True` استفاده می‌کنند (بدون تغییر).

---

## ۸. Migration

**فایل جدید:** `backend/migrations/versions/a2b3c4d5e6f7_phase26_test_type_enum_is_active_bool.py`

| کلید | مقدار |
|---|---|
| `revision` | `a2b3c4d5e6f7` |
| `down_revision` | `f1a2b3c4d5e6` |

**مراحل upgrade:**
1. `UPDATE strategy_versions SET test_type = UPPER(test_type) WHERE UPPER(...) IN ('BACKTEST','FORWARD','REAL')` — تبدیل حروف کوچک → NAME
2. `UPDATE strategy_versions SET test_type = NULL WHERE ... NOT IN (...)` — مقادیر نامعتبر
3. `batch_alter_table("strategy_versions").alter_column("test_type", String → Enum)`
4. `batch_alter_table("custom_time_intervals").alter_column("is_active", Integer → Boolean)`
5. `batch_alter_table("time_points").alter_column("is_active", Integer → Boolean)`

**اجرا:** `alembic upgrade head` → **EXIT=0** · بکاپ: `trading_desk.db.bak_phase26`

**تأیید اسکیما (SQLite):**

| جدول | ستون | نوع جدید |
|---|---|---|
| `strategy_versions` | `test_type` | `VARCHAR(8)` (Enum) |
| `custom_time_intervals` | `is_active` | `BOOLEAN` |
| `time_points` | `is_active` | `BOOLEAN` |
| `alembic_version` | — | `a2b3c4d5e6f7` (head) ✅ |

---

## ۹. `requirements.txt` — Pin نسخه‌ها

**قبل:** ۱۸ بسته بدون نسخه.
**بعد:** همه با `==` (نسخه‌های واقعی نصب‌شدهٔ venv):

```
fastapi==0.141.1          uvicorn[standard]==0.54.0
sqlalchemy==2.1.1         alembic==1.20.0
pydantic==2.13.5          pydantic-settings==2.15.0
python-multipart==0.0.32  openpyxl==3.1.5
beautifulsoup4==4.15.0    slowapi==0.1.10
reportlab==5.0.1          jdatetime==6.1.0
arabic-reshaper==3.0.1    python-bidi==0.6.11
pytest==9.1.1             pytest-cov==7.1.0
httpx==0.28.1
```

---

## ۱۰. README ریشه

**فایل جدید:** `README.md` (~۱۹۰ خط) شامل:
- معرفی + جدول ۹ بخش اصلی
- ویژگی‌های کلیدی (۲۰ مورد)
- راه‌اندازی سریع (لانچر + دستی) با پیش‌نیازها و آدرس‌ها
- دستورات تست و پرکاربرد
- فناوری‌ها + ساختار پروژه
- جدول لینک مستندات

---

## ۱۱. تست کامل

### تست‌های جدید

**`backend/tests/test_trades.py`** (+۵ تست فاز ۲۶):

| تست | سناریو |
|---|---|
| `test_restore_soft_deleted_trade` | حذف → پنهان → `include_deleted=true` (با فلگ `is_deleted`) → بازگردانی → دیده می‌شود |
| `test_restore_is_idempotent` | بازگردانی معامله‌ی حذف‌نشده → `count=0` |
| `test_restore_not_found` | `404` |
| `test_list_default_hides_deleted_and_flags_it` | لیست پیش‌فرض + `is_deleted=False` |
| `test_include_deleted_returns_both` | `include_deleted=true` → هر دو (فلگ درست) |

**`backend/tests/test_quality_phase26.py`** 🆕 (+۶ تست):

| تست | سناریو |
|---|---|
| `test_version_test_type_roundtrip` | `backtest` → ذخیره `TestType.BACKTEST` → خروجی `backtest` |
| `test_version_test_type_uppercase_accepted` | `FORWARD` → خروجی `forward` |
| `test_version_test_type_invalid_becomes_none` | `xyz` → `None` |
| `test_fork_keeps_test_type` | Fork نسخهٔ `real` → `real` |
| `test_custom_interval_is_active_is_boolean` | default = `True` |
| `test_time_point_is_active_is_boolean` | default = `True` |

### نتایج اجرا

| ابزار | نتیجه |
|---|---|
| `pytest` (کل) | ✅ **۱۰۱ پاس** (`101 passed in 24.16s`, EXIT=0) |
| `vitest run` | ✅ **۹ پاس** (EXIT=0) |
| `npx tsc -b --force` | ✅ `TSC_EXIT=0` |
| `npm run build` | ✅ `BUILD_EXIT=0` |
| `alembic upgrade head` | ✅ EXIT=0 (`a2b3c4d5e6f7`) |
| `import app.main` | ✅ OK |

### تأیید قرارداد مسیرها

```
TOTAL_PATHS: 109                       ← +۱ نسبت به فاز ۲۵ (۱۰۸)
/api/trades/                     ['get']
/api/trades/{trade_id}/restore   ['post']   ← جدید
/api/trades/batch-delete         ['post']
/api/trades/manual               ['post']
/api/trades/{trade_id}           ['delete', 'get', 'patch']
DB journal_mode: wal
alembic: a2b3c4d5e6f7
```

---

## ۱۲. فایل‌های تغییر‌یافته / جدید

| فایل | نوع | تغییر |
|---|---|---|
| `backend/app/api/trades.py` | ✏️ | `restore_trade` + `include_deleted` + `is_deleted` در ۲ serializer |
| `backend/app/core/database.py` | ✏️ | WAL + `DeclarativeBase` |
| `backend/app/main.py` | ✏️ | `lifespan` (حذف `on_event`) + import `asynccontextmanager` |
| `backend/app/models/strategy.py` | ✏️ | `test_type` Enum + ۲× `is_active` Boolean |
| `backend/app/api/strategies.py` | ✏️ | `_parse_test_type` + ۴ محل مصرف |
| `backend/app/services/analysis_service.py` | ✏️ | `is_active.is_(True)` |
| `backend/app/schemas/analytics.py` | ✏️ | ۴× `is_active: bool` |
| `backend/migrations/versions/a2b3c4d5e6f7_phase26_test_type_enum_is_active_bool.py` | 🆕 | Migration |
| `backend/requirements.txt` | ✏️ | Pin نسخه‌ها |
| `backend/tests/test_trades.py` | ✏️ | +۵ تست |
| `backend/tests/test_quality_phase26.py` | 🆕 | +۶ تست |
| `frontend/src/api/client.ts` | ✏️ | `include_deleted` + `restoreTrade` |
| `frontend/src/pages/TradesPage.tsx` | ✏️ | Checkbox + رنگ حذف‌شده + دکمهٔ بازگردانی |
| `README.md` | 🆕 | راهنمای ریشه |
| `PHASE26_REPORT.md` | 🆕 | این گزارش |

**بکاپ:** `backend/trading_desk.db.bak_phase26`

---

## ۱۳. نکات و محدودیت‌ها

1. **`test_type` و قرارداد API:** مقدار در DB به **NAME** (`'BACKTEST'`) ذخیره می‌شود (هم‌راستا با `Trade.test_type` و `AnalysisScope`)، اما ورودی/خروجی API همچنان **حروف کوچک** است → Frontend بدون تغییر کار می‌کند.
2. **مقادیر نامعتبر `test_type`:** به‌جای ذخیرهٔ رشتهٔ نامعتبر، `None` می‌شوند (رفتار تمیزتر). Frontend فقط مقادیر معتبر می‌فرستد.
3. **WAL فقط برای SQLite:** با `_IS_SQLITE` گارد شده؛ روی DB دیگر PRAGMA اجرا نمی‌شود.
4. **فایل‌های `-wal`/`-shm`:** با WAL، SQLite کنار DB دو فایل کمکی می‌سازد؛ هنگام **Backup دستی/کپی** باید هر سه در نظر گرفته شوند (سرویس Backup از SQLite Online Backup API استفاده می‌کند → ایمن است).
5. **`PropAccount.is_active`** (`prop.py:65`) طبق دامنهٔ درخواست **تغییر نکرد** (فقط `CustomTimeInterval` و `TimePoint`).
6. **`is_active` در API:** نوع پاسخ از `int` به `bool` تغییر کرد؛ Frontend از این فیلد استفاده نمی‌کند → بدون شکست.
7. **Restore تعریف‌شده برای تک‌معامله:** حذف گروهی + بازگردانی گروهی در دامنهٔ این فاز نبود.
8. **No frontend test جدید:** رفتار UI با `tsc` + `build` + تست‌های بک‌اند پوشش داده شد.

---

## 🏁 جمع‌بندی فاز ۲۶

| بخش | موارد | وضعیت |
|---|---|---|
| ۱. Restore + نمایش حذف‌شده‌ها | ۲ | ✅ |
| ۲. مدرن‌سازی Backend | ۳ (WAL، lifespan، DeclarativeBase) | ✅ |
| ۳. کیفیت کد | ۴ (enum، Boolean، requirements، README) | ✅ |
| **جمع** | **۹ مورد + Migration + ۱۱ تست** | ✅ |

**دستاوردها:** رفع هر دو DeprecationWarning (FastAPI + SQLAlchemy)، فعال‌سازی WAL، تکمیل چرخهٔ Soft Delete با Restore، چکیده‌سازی نوع `test_type`، pin کردن وابستگی‌ها و افزودن README.

*گزارش فاز ۲۶ — ۱۴۰۵/۰۷/۰۶ (2026-09-28)*



---
