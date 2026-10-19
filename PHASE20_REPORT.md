# 📋 گزارش فاز ۲۰ — تحلیل ۶گانه + Tab bar + داشبورد پول واقعی

> **تاریخ:** ۱۴۰۵/۰۷/۰۴ (2026-09-26) · **مدل:** `deepseek/deepseek-v4.1-flash`
> **وضعیت:** ✅ کامل — ✅ ۵۲ تست پاس · ✅ build فرانت‌اند (tsc + vite) · ✅ تست زنده

---

## خلاصه

**۶ نوع تحلیل** (بکتست، فوروارد، پراپ ۱/۲/۳، بروکر) از هم جدا شدند با `AnalysisScope`.
داشبورد یک بخش `spendable_money` برای پول قابل خرج گرفت.
فرانت‌اند با Tab bar کاربر می‌تواند بین ۶ نوع تحلیل سوییچ کند.

---

## فایل‌های تغییر‌یافته

| فایل | وضعیت | توضیح |
|---|---|---|
| `backend/app/models/strategy.py` | ✏️ ویرایش | `AnalysisScope` enum + `scope`, `scope_key` در `AnalysisResult` و `AnalysisRun` |
| `backend/app/services/analysis_service.py` | ✏️ Refactor | `_analyze()` generic + `analyze_prop_stage()` + `analyze_broker()` |
| `backend/app/api/analytics.py` | ✏️ ویرایش | ۶ endpoint جدید (POST + GET) · `spendable_money` در دشبورد · گارد سازگاری |
| `backend/app/utils/trade_scope.py` | ✏️ اصلاح نشد | `analysis_trades_filter()` در فاز ۱۹ |
| `backend/migrations/versions/a3f7c21b9d84_phase20_analysis_scope.py` | 🆕 جدید | Migration دو جدول + backfill + قابل downgrade |
| `frontend/src/pages/AnalysisPage.tsx` | ✏️ Refactor | Tab bar + scope-aware loading + localStorage |
| `frontend/src/api/client.ts` | ✏️ ویرایش | ۶ تابع جدید API |
| `backend/tests/test_analysis_scope.py` | 🆕 ۱۴ تست | (`_add_stale_result` به‌روز + ۳ تست scope) |
| **جدید** | `PHASE20_DESIGN.md` | طراحی ۳۵۹ خطی |
| **جدید** | `PHASE20_REPORT.md` | این فایل |

---

## ۱. فاز ۲۰.۱ — Migration + مدل

### قبل
```python
class AnalysisResult(Base):
    version_id = Column(Integer, ForeignKey("strategy_versions.id"), nullable=False)
```

### بعد
```python
class AnalysisScope(str, enum.Enum):
    VERSION = "version"; PROP_STAGE = "prop_stage"; BROKER = "broker"

class AnalysisResult(Base):
    scope = Column(Enum(AnalysisScope), nullable=False, default=AnalysisScope.VERSION, index=True)
    scope_key = Column(String, nullable=False, index=True)
    version_id = Column(Integer, FK("strategy_versions.id"), nullable=True)  # NOT NULL → NULL
    prop_stage_id = Column(Integer, FK("prop_stages.id"), nullable=True)     # جديد
    finance_account_id = Column(Integer, FK("accounts.id"), nullable=True)  # جديد

    __table_args__ = (UniqueConstraint("scope", "scope_key", name="uq_analysis_results_scope_key"),)
```

**Migration:** دو مرحله (add nullable → backfill → alter NOT NULL) · برگشت‌پذیر · داده legacy حفظ شد.

---

## ۲. فاز ۲۰.۲ — Refactor موتور تحلیل

موتور مشترک `_analyze()` استخراج شد – يک method با پارامتری `trades`, `scope`, `**fk`.

| method | فیلتر | Matricها |
|---|---|---|
| `analyze_version` | `ersion_id` + `analysi_trades_filter()` + (اختیاری) `est_type` | مانی |
| `analyze_prop_stage` | `pro_stage_id` | مانی + `ProRulEnginvalide_stage()` |
| `analyze_broker` | `inance_count_id` | مانی |

---

## ۳. فاز ۲۰.۳ — APIهای جدید

| Endpoint | توع | پارمتر |
|---|---|---|
| `POSt /api/analytics/analyze/version/{id}` | POST | `?est_type=BACKTES|FORWRD` |
| `POSt /api/analytics/analyze/prop/{id}` | POST | — |
| `POSt /api/analytics/analyze/broker/{id}` | POST | — |
| `GET /api/analytics/analysis/version/{id}` | GET | `?est_type=...` |
| `GET /api/analytics/analysis/prop/{id}` | GET | — |
| `GET /api/analytics/analysis/broker/{id}` | GET | — |

Backward-compat: `POSt /analyze/{version_id}` و `GET /{version_id}` حفظ شدند.

---

## ۴. فاز ۲۰.۴ — داشبورد پول واقعی

کلید جدبد در پاسخ `/dashboard`:

```json
"spendable_money": {
    "net_pnl": 1234.56,          // سرد مرحلة ۳ + سرد برکر
    "total_balance": 5678.90,    // موجودی برکر + سرد ۲تا
    "initial_capital": 5000.0,   // SUM(DEPOSIT) برکر
}
```

---

## ۵. فاز ۲۰.۵ — فرانت‌اند Tab bar

Tab bar با ۶ دکمه در بالا:

`[ 📊 بکتست ] [ 📈 فوروارد ] [  مرحله ۱ ] [  مرحله ۲ ] [ 💰 مرحله ۳ ] [  برکر ]`

هر Tab انتخابگر مخصوی خود را دارد:
- بکتست/فوروارد → dropdown نسخه
- مراحل ۱/۲/۳ → dropdown مرحلة پِرای (از `GET /prop/stages/all`)
- برکر → dropdown حساب برکر (از `GET /finance/accounts?type=broker`)

ذخیرة انتخاب در `localStorage` با کلید `analysis_selected_scope`.

---

## ۶. تست

| تست | تمداد |
|---|---|
| `pstt` (بک‌اند) | ✅ **۵۲ passed** |
| `tsc -b` (تیپ‌اسکریپ) | ✅ exit=0 |
| `vite build` | ✅ exit=0 |
| تست زنده (uvicorn) | ✅ `POST /a/analytics/analyze/1` → ۴۰۴ صحیح |
| ط Downgrade (alembic) | ✅ `a3fc21b9d84 → 9f1a2b3c4d5e` |

---

## ۷. محدودیت‌ها و یادداشت‌ها

1. **جدول معاملات در AnalysisPage:** برای scopeهای غیر-VERSION، `getVersionTrades` خالی برمی‌گردد (چون endpoint فقط `version_id` را پشتیبانی می‌کند). اضافه کردن endpoint معاملات بر اساس `prop_stage_id` / `finance_account_id` در فاز آینده انجام شود.

2. **Finance bridge (فاز ۲۱):** `spendable_money` فعلاً از محاسبات مستقیم روی Trades + Accounts استفاده می‌کند. سود تحقق‌یافته از Account.balance استخراج نمی‌شود (چون bridge وجود ندارد). فاز ۲۱ این را کامل می‌کند.

3. **PropRuleEngine در تحلیل:** `analyze_prop_stage()` خروجی `evaluate_stage()` را شامل می‌شود که progress, اهداف DD/سود و محدودیت‌ها را نشان می‌دهد — فرانت‌اند فعلاً آن را نمایش نمی‌دهد (فاز ۲۱).

4. **AnalysisPage:** بعد از سوییچ تب، اولین عصر dropdown خودکار مقدار نمی‌گیرد (کاربر باید دستی انتخاب کند). می‌توان در فاز بعد auto-select اولین عصر هر لیست را اضافه کرد.

---

*گزارش فاز ۲۰ — تهیه‌شده در ۱۴۰۵/۰۷/۰۴.*