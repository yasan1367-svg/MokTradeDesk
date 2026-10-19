# PHASE 39.5 — Fix `conftest.py` (DB تست جداگانه)

> **تاریخ:** ۱۴۰۵/۰۷/۰۸ (2026-09-30)
> **وضعیت:** ✅ کامل — ✅ ۲۳۲ تست پاس · ✅ خروجی pytest = 0 · ✅ `trading_desk.db` واقعی **بایت‌به‌بایت دست‌نخورده**
> **قوانین:** ✅ Auto-approve خاموش · ✅ گام‌به‌گام · ✅ commit **نشد**

---

## ۱. خلاصه اجرایی

هوک `startup` در `app/main.py` هنگام هر بار ساخت `TestClient(app)` (به‌صورت context manager) اجرا می‌شد و روی **دیتابیس واقعی** `trading_desk.db` این دو کار را انجام می‌داد:

1. `alembic upgrade head` (مهاجرت روی DB واقعی)
2. ساخت Backup + روشن‌کردن thread پس‌زمینهٔ Backup خودکار

با اصلاح `backend/tests/conftest.py`:

- `DATABASE_URL` **قبل از** import شدن `app` به یک فایل موقت تستی اشاره می‌کند (engine هرگز به DB واقعی وصل نمی‌شود).
- هوک‌های `startup`/`shutdown` اپ در تست‌ها **پاک (no-op)** می‌شوند ⇒ نه مهاجرت، نه Backup، نه thread.
- دیتابیس درون‌حافظه‌ی هر تست (`sqlite://` + `StaticPool`) دست‌نخورده باقی ماند.
- فایل DB تستی در پایان اجرای تست‌ها پاک می‌شود.

**نتیجهٔ عددی:** قبل و بعد از pytest، دیتابیس واقعی **همان رکورد، همان حجم و همان SHA-256** را دارد و تعداد فایل‌های Backup تغییر نکرد (۳۰ → ۳۰).

---

## ۲. یافته‌های کد فعلی (گام ۱)

فایل `backend/tests/conftest.py` (نسخهٔ قبل از اصلاح):

```python
from app.core.database import Base, get_db
from app.main import app  # ← ریشهٔ مشکل
...
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db(): ...
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:   # ← این خط رویداد startup را اجرا می‌کند
        yield c
    app.dependency_overrides.clear()
```

پاسخ به سؤال‌های گزارش:

| پرسش | پاسخ |
|------|------|
| چطور DB را می‌سازد؟ | `db_session` یک `engine` روی `sqlite://` درون‌حافظه + `StaticPool` می‌سازد و `Base.metadata.create_all` می‌زند؛ سپس با `dependency_overrides[get_db]` به روترها تزریق می‌شود. |
| آیا `app.main` را import می‌کند؟ | ✅ بله (خط ۱۴ نسخهٔ قبلی) — برای لود شدن همهٔ مدل‌ها/روترها. |
| آیا هوک startup اجرا می‌شود؟ | ✅ بله — چون `with TestClient(app)` context manager است و lifespan را اجرا می‌کند. |
| آیا `trading_desk.db` استفاده می‌شود؟ | ✅ بله — به‌صورت **غیرمستقیم**: `settings.DATABASE_URL` پیش‌فرض (`sqlite:///./trading_desk.db`) درون هوک startup برای `alembic upgrade head` و `backup_service` استفاده می‌شد. |

شاهد مستقل: پوشهٔ `backend/backups/` پر از فایل‌های `trading_desk_YYYYMMDD_HHMMSS.db` با اندازهٔ دقیقاً برابر DB واقعی (413,696 بایت) بود که برای هر تست یکی ساخته شده بود.

---

## ۳. تحلیل (گام ۲)

**چرا DB واقعی migrate می‌شد؟**
`app/main.py:89` یک `@app.on_event("startup")` دارد که در آن:

```python
alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)  # real DB
alembic_command.upgrade(alembic_cfg, "head")
...
svc.create_backup()          # Backup از DB واقعی
```

`conftest` فقط لایهٔ dependency (`get_db`) را override می‌کرد، اما هوک startup مسیر مستقلی دارد و `settings.DATABASE_URL` را دست‌نخورده می‌بیند ⇒ هم مهاجرت و هم Backup روی DB واقعی اجرا می‌شد.

**گزینه‌ها:**

| گزینه | ارزیابی |
|-------|---------|
| **A — `:memory:`** | ✅ سریع، جداسازی کامل؛ هر تست DB تازه. ← برای `db_session` انتخاب شد (رفتار موجود، حفظ شد). |
| **B — temp file** | ✅ مناسب برای engine سراسری اپ (چون `:memory:` بین اتصال‌ها گم می‌شود). ← برای `DATABASE_URL` سراسری انتخاب شد. |
| **C — `trading_desk_test.db`** | ⚠️ فایل ماندگار روی دیسک می‌سازد و نیاز به gitignore دارد. |
| **D — disable هوک startup** | ✅ حذف ریشهٔ عارضه (مهاجرت/Backup/thread). ← همراه A و B انتخاب شد. |

**راه‌حل انتخابی: ترکیب A + B + D** (دفاع چندلایه):
1. `DATABASE_URL` → فایل موقت (B): حتی اگر هوکی اجرا شود، هدفش DB تستی است.
2. پاک‌کردن `app.router.on_startup/on_shutdown` (D): هوک اصلاً اجرا نمی‌شود.
3. `db_session` روی `:memory:` (A): تست‌ها کاملاً مستقل و سریع.
4. پاک‌سازی فایل موقت در پایان session.

---

## ۴. تغییرات `conftest.py` (گام ۳)

فایل `backend/tests/conftest.py` بازنویسی شد:

```python
import os
import sys
import tempfile

# ۱) قبل از import شدن app: هدایت DATABASE_URL به فایل موقت
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="trading_desk_test_", suffix=".db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB_PATH.replace("\\", "/")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app

# ۲) غیرفعال‌سازی هوک‌های startup/shutdown در تست‌ها
app.router.on_startup.clear()
app.router.on_shutdown.clear()
```

- `db_session` و `client` **بدون تغییر** (به‌جز جای‌گذاری) باقی ماندند تا رفتار ۲۳۲ تست حفظ شود.
- fixture جدید session-scoped:

```python
@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_database():
    yield
    try:
        if os.path.exists(_TEST_DB_PATH):
            os.remove(_TEST_DB_PATH)
    except OSError:
        pass
```

**نکتهٔ کلیدی ترتیب import:** تنظیم `os.environ["DATABASE_URL"]` در بالای فایل و **قبل از** `from app.core.config import ...`/`from app.main import app` است؛ چون `Settings()` زمان import ساخته می‌شود و env-var بر `.env` اولویت دارد.

---

## ۵. تست‌ها (گام ۴)

### شرایط اولیه (قبل از pytest)

```
trades: 0
accounts: 0
transactions: 0
screenshots: 0
sha256: 18c9b0243cfd601f70d48b53c1adc14da1960fce2270a178cada22a51257bd85
size: 413696
mtime: 1790740983.7406285
```

### اجرای pytest

```powershell
cd backend
venv\Scripts\python.exe -m pytest -q -p no:warnings
```

خروجی:

```
232 passed in 9.83s
PYTEST_EXIT=0
```

### تأیید جدا‌سازی (آزمون کنترل‌شده)

اسکریپت تشخیصی موقت تأیید کرد:

```
env DATABASE_URL     = sqlite:///C:/Users/DIGI/AppData/Local/Temp/trading_desk_test_....db
settings.DATABASE_URL = sqlite:///C:/Users/DIGI/AppData/Local/Temp/trading_desk_test_....db
engine.url            = sqlite:///C:/Users/.../trading_desk_test_....db
on_startup BEFORE clear = 1
on_startup AFTER  clear = 0
TestClient status = 200
new backup files: []
temp db size after TestClient: 0   ← مهاجرت اجرا نشد
```

⇒ نه `alembic upgrade head` اجرا شد، نه Backup ساخته شد، نه thread پس‌زمینه روشن شد.

---

## ۶. تأیید DB واقعی دست‌نخورده

### وضعیت بعد از pytest

```
trades: 0
accounts: 0
transactions: 0
screenshots: 0
sha256: 18c9b0243cfd601f70d48b53c1adc14da1960fce2270a178cada22a51257bd85
size: 413696
mtime: 1790740983.7406285
```

| شاخص | قبل | بعد | نتیجه |
|------|:---:|:---:|:---:|
| `trades` | 0 | 0 | ✅ بدون تغییر |
| `accounts` | 0 | 0 | ✅ بدون تغییر |
| `transactions` | 0 | 0 | ✅ بدون تغییر |
| `screenshots` | 0 | 0 | ✅ بدون تغییر |
| SHA-256 | `18c9b024…5bd85` | `18c9b024…5bd85` | ✅ **یکسان** |
| حجم (بایت) | 413,696 | 413,696 | ✅ یکسان |
| mtime | 1790740983.7406285 | 1790740983.7406285 | ✅ **حتی mtime هم تغییر نکرد** |
| تعداد Backupها | ۳۰ | ۳۰ | ✅ Backup جدید ساخته نشد |
| فایل موقت باقی‌مانده | — | صفر | ✅ پاک شد |

> mtime یکسان یعنی فایل DB واقعی حتی **یک‌بار هم باز نشده برای نوشتن** — قوی‌ترین سطح تأیید.

---

## ۷. بدهی فنی #۱ فاز ۳۹ — وضعیت

| # | مورد | وضعیت قبل | وضعیت بعد |
|:--|:-----|:---:|:---:|
| ۱ | `pytest` فایل `trading_desk.db` واقعی را migrate می‌کرد | 🟠 باز | ✅ **بسته شد** |

---

## ۸. فایل‌ها

| فایل | تغییر |
|------|-------|
| `backend/tests/conftest.py` | 🔧 بازنویسی شده (DB تستی موقت + no-op کردن هوک‌ها + پاک‌سازی) |
| `PHASE39_5_CONFTEST_FIX.md` | ➕ این گزارش |

> ⛔ commit نشد (طبق دستور).

