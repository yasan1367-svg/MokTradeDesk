# PHASE 41 — Safety Net

> **تاریخ:** ۱۴۰۵/۰۷/۰۸ (2026-09-30)
> **وضعیت:** ✅ کامل (با یک مانع شبکه‌ای) — ✅ ۲۵۰ pytest · ✅ DB واقعی دست‌نخورده · ✅ tag baseline
> **قوانین:** ✅ Auto-approve خاموش · ✅ گام‌به‌گام · ✅ commit/push **نشد**

---

## ۱. خلاصه اجرایی

1. **Baseline tag** ساخته شد: `v0.40-baseline` روی `4c61eee` + بکاپ دیتابیس در `C:\Backup\`.
2. **ruff/pre-commit** به‌دلیل **بلوکه‌بودن شبکه (PyPI)** نصب نشد؛ فایل‌های کانفیگ ساخته شدند و گزارش با یک **ابزار AST جایگزین** تهیه شد.
3. **`/compare` رفع شد**: کد مرده + تکرار حذف، و نبود نسخه ⇒ **۴۰۴** (قبلاً ۵۰۰).
4. **تست migration** اضافه شد: روی DB خالی upgrade + `compare_metadata` ⇒ **۵ اختلاف نوع** (بدون اختلاف ساختاری).
5. تست‌ها: **۲۵۰ passed** · Alembic head `f39a1b2c3d4e` · دیتابیس واقعی SHA-256 بدون تغییر.

---

## ۲. تسک ۴۱.۱ — Baseline Tag

| گام | نتیجه |
|:---|:---|
| `git status` (ابتدا) | ✅ clean |
| `git log` | HEAD = **`4c61eee`** (Phase 40) |
| بکاپ DB | `C:\Backup\trading_desk.db.v0.40-baseline` — ۴۱۳,۶۹۶ بایت |
| SHA-256 بکاپ vs DB واقعی | ✅ یکسان: `18C9B024…BD85` |
| Tag | ✅ `v0.40-baseline` → `4c61eee` |
| `git push origin main --tags` | ⛔ **انجام نشد** (طبق «Auto-approve خاموش») — منتظر تأیید کاربر |

> تگ فقط **محلی** است. `origin/main` == HEAD == `4c61eee` ⇒ هنوز push نشده.

---

## ۳. تسک ۴۱.۲ — ruff + pre-commit

### نصب ❌ (مانع محیطی)
```
ERROR: Could not install packages due to an OSError:
HTTPSConnectionPool(host='files.pythonhosted.org', port=443):
ConnectionResetError(10054) / ReadTimeoutError (read timeout=120)
```
تلاش‌ها: `pypi.org` (چند بار، `--retries 10`) و آینهٔ `mirrors.aliyun.com` — هر دو به‌دلیل reset شدن اتصال ناموفق. TCP به پورت ۴۴۳ باز است ولی دانلود وسط راه قطع می‌شود (محدودیت سندباکس).

### فایل‌های ساخته‌شده ✅
- `backend/pyproject.toml` — `[tool.ruff]` با `select = ["F821","F401","F841"]`
- `backend/.pre-commit-config.yaml` — hook رسمی ruff

> ⚠️ `.gitignore` قاعدهٔ `*.pre*` داشت که `.pre-commit-config.yaml` را **ignore** می‌کرد؛ یک استثنا (`!backend/.pre-commit-config.yaml`) اضافه شد تا فایل قابل commit شود.

### گزارش جایگزین (ابزار AST موقت)
چون ruff نصب نشد، یک اسکریپت موقت مبتنی بر `ast` نوشتم که این قواعد را تقریب می‌زند.

```
files scanned: 90
total findings: 96
```

| قاعده | تعداد | توضیح |
|:---|:---:|:---|
| **F401** (import بی‌استفاده) | **۸۶** | شامل چند false-positive |
| **F841** (متغیر محلی بی‌استفاده) | **۹** | واقعی |
| **unreachable** (کد مرده) | **۱** | 🟠 واقعی — پایین |
| **F821?** (نام تعریف‌نشده، محافظه‌کارانه) | **۰** | — |

**فایل‌های مهم F401 (نمونه):**
- `app/main.py:11` → `engine`, `Base`
- `app/api/trades.py:11` → `Strategy` · `:13` → `PropStage` · `:3` → `and_`
- `app/api/analytics.py:2` → `joinedload` · `:270,:369,:452,:558` → `FinanceAccount`, `AccountType`, ...
- `app/api/prop.py:10` → `WithdrawalStatus` · `:16` → `FinancialTransaction`
- `app/api/finance.py:3`, `prop.py:4`, `symbol_mappings.py:3` → `List`

**F401 با false-positive (توجه):**
- `migrations/env.py` (همهٔ مدل‌ها) → **عمدی** برای ثبت در `Base.metadata` (نباید حذف شوند)
- `from __future__ import annotations` → `annotations` یک نام نیست (اسکریپت اشتباه می‌گیرد)
- `app/api/__init__.py` → re-export ماژول‌ها

**F841 (۹ مورد):** `analytics.py:728` `now` · `import_service.py:209` `idx` · `chart_helpers.py:107` `wedges`,`texts` · `test_import_engine.py:345` `original` · `test_phase38_personal_finance.py:140` `acc` · `test_prop.py:144` `msg` · `migrations/versions/9f1a2b3c4d5e…:102,130` `default_account_holder`,`l_id`

**🟠 unreachable (کد مرده) — کشف مهم:**
```
app/services/import_engine.py:1068  →  if invalid: ...  (بعد از یک return بی‌قید از متد _blocking_error)
```
این دقیقاً هم‌خانوادهٔ باگ `/compare` است: یک بلوک تکراری که بعد از `return` مانده و هرگز اجرا نمی‌شود. (در گزارش فاز ۴۲ ثبت شد.)

> ⛔ طبق دستور («فقط گزارش»)، هیچ‌کدام fix **نشد**.

---

## ۴. تسک ۴۱.۳ — اصلاح `/compare`

### یافته‌های کد (قبل)
فایل `backend/app/api/analytics.py` — تابع `compare_versions` (خط ۱۰۲۳):

```python
try:
    service = AnalysisService(db)
    service = AnalysisService(db)                       # ← تکرار
    result = service.compare_versions(request.version_ids, min_trades=request.min_trades or 0)
    return result
    raise HTTPException(status_code=404, detail=str(e))  # ← کد مرده + NameError (e تعریف نشده)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"خطا در مقایسه: {str(e)}")  # ← ValueError هم ۵۰۰ می‌شد
```

پاسخ به پرسش‌ها:
- `raise` بعد از `return`؟ ✅ بله (unreachable + `e` تعریف‌نشده)
- `service =` دو بار؟ ✅ بله
- `except ValueError`؟ ❌ نبود ⇒ `ValueError` («هیچ نسخه‌ی قابل‌مقایسه‌ای یافت نشد») به **۵۰۰** تبدیل می‌شد.

### تغییرات
```diff
     try:
         service = AnalysisService(db)
-        service = AnalysisService(db)
         result = service.compare_versions(request.version_ids, min_trades=request.min_trades or 0)
         return result
-        raise HTTPException(status_code=404, detail=str(e))
+    except ValueError as e:
+        raise HTTPException(status_code=404, detail=str(e))
     except Exception as e:
         raise HTTPException(status_code=500, detail=f"خطا در مقایسه: {str(e)}")
```

### تست‌ها — `backend/tests/test_phase41_compare.py`
| تست | انتظار |
|:---|:---|
| `test_compare_unanalyzed_version_returns_404` | نسخهٔ تحلیل‌نشده ⇒ ۴۰۴ (نه ۵۰۰) |
| `test_compare_invalid_input_returns_404` | نسخهٔ ناموجود / لیست خالی ⇒ ۴۰۴ |
| `test_compare_two_analyzed_versions_works` | دو نسخهٔ تحلیل‌شده ⇒ ۲۰۰ + `items` + `best_version_id` |

نتیجه: **۳ passed** (EXIT=0).

---

## ۵. تسک ۴۱.۴ — تست Migration

فایل جدید: `backend/tests/test_migrations.py` — روی یک DB **موقت**، `alembic upgrade head` می‌زند و `compare_metadata` اجرا می‌کند. (تأیید شد `migrations/env.py` از URL کانفیگ استفاده می‌کند، نه `settings.DATABASE_URL` ⇒ DB واقعی لمس نمی‌شود.)

نتیجه اجرا:
```
[test_migrations_match_models] اختلافات مدل vs migration: 5
1 passed
```

| # | جدول.ستون | اختلاف (باگ مدل vs migration) |
|:--|:---|:---|
| ۱ | `analysis_results.scope` | `VARCHAR(10)` → `Enum(VERSION/PROP_STAGE/PERSONAL_ACCOUNT)` |
| ۲ | `analysis_runs.scope` | `VARCHAR(10)` → `Enum(...)` |
| ۳ | `categories.type` | `VARCHAR(8)` → `Enum(INCOME/EXPENSE/TRANSFER/CONVERSION)` |
| ۴ | `prop_alerts.is_read` | `INTEGER()` → `Boolean()` |
| ۵ | `trades.test_type` | `VARCHAR(8)` → `Enum(BACKTEST/FORWARD/REAL_PERSONAL/REAL_PROP)` |

**تفسیر:** هر ۵ مورد از نوع `modify_type` هستند و هیچ اختلاف **جدول/ستون/ایندکس/قید** وجود ندارد ⇒ اسکیمای ساختاری کاملاً هم‌خوان است؛ فقط **نمایش نوع** در SQLite (که نوع‌ها را به‌صورت VARCHAR/INTEGER نگه می‌دارد) متفاوت است.

- تأیید DB واقعی: SHA-256 قبل == بعد ⇒ `18C9B024…BD85`
- طبق دستور، `assert len(diff) == 0` **غیرفعال** گذاشته شد (فاز ۴۲).

---

## ۶. تست‌ها (کل)

| مرحله | تعداد |
|:---|:---|
| قبل از فاز ۴۱ | ۲۴۶ |
| + `test_phase41_compare.py` (۳) | ۲۴۹ |
| + `test_migrations.py` (۱) | **۲۵۰** |

اجرای نهایی: `250 passed, 0 failed` · EXIT=0 · DB واقعی SHA-256 بدون تغییر.

---

## ۷. آماده برای Phase 42

موارد کشف/آمادهٔ `Phase 42`:
1. **کد مرده** در `app/services/import_engine.py:1068` (مشابه `/compare`).
2. **۵ اختلاف نوع** مدل vs migration (بالا) — برای فعال‌سازی `assert` در تست migration.
3. **۹ مورد F841** و **۸۶ مورد F401** (پس از نصب ruff واقعی، تأییدیه/اصلاح).
4. `/compare` ✅ رفع شد.

---

## ۸. بدهی‌های باقی‌مانده

| # | مورد | شدت | یادداشت |
|:--|:---|:---:|:---|
| ۱ | نصب `ruff`/`pre-commit` ناموفق (شبکه) | 🟠 | کانفیگ‌ها آماده‌اند؛ با `pip install ruff pre-commit` روی شبکهٔ سالم + `pre-commit install` فعال می‌شود. |
| ۲ | `git push origin main --tags` انجام نشد | 🟡 | تگ `v0.40-baseline` فقط محلی است — منتظر تأیید. |
| ۳ | کد مرده `import_engine.py:1068` | 🟠 | فاز ۴۲. |
| ۴ | ۵ اختلاف نوع migration | 🟡 | فاز ۴۲. |

---

## ۹. وضعیت Git (بدون commit)

```
 M .gitignore                                  (استثنای pre-commit config)
 M backend/app/api/analytics.py                (fix /compare)
?? backend/.pre-commit-config.yaml
?? backend/pyproject.toml
?? backend/tests/test_migrations.py
?? backend/tests/test_phase41_compare.py
?? PHASE41_IMPL_REPORT.md

HEAD: 4c61eee   ·   tags: v0.40-baseline (local)   ·   origin/main: 4c61eee
```

> ⛔ طبق دستور، هیچ commit/push انجام نشد. ⏸️ توقف.

