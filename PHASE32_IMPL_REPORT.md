# 🏢 PHASE 32 — Prop Rule Engine · IMPLEMENTATION REPORT

> **وضعیت:** ✅ کامل (Model + Migration + Engine + API + Tests)
> **تاریخ:** ۱۴۰۵/۰۷/۰۹
> **Revision:** `d4e5f6a7b8c9` → **`f6a7b8c9d0e1`** (head جدید)
> **خروجی تست:** `139 passed` (کل مجموعه) · `22 passed` (Phase 32 + prop)

---

## ۱. خلاصهٔ اجرایی

Pipeline درخواستی پیاده شد:

```text
PropStage ──► Prop Rules ──► PropRuleEngine ──► Rule Evaluation ──► PASS / WARNING / VIOLATION
                                       │
                                       └──► rule_violations (تاریخچهٔ ثبت‌شده)
```

- موتور قوانین اکنون برای هر ارزیابی، **۷ قاعده** را نوعدار بررسی می‌کند و برای هرکدام یک
  نتیجهٔ ساختاریافته (`rule_type`, `actual_value`, `limit_value`, `severity`) تولید می‌کند.
- نتایج در جدول جدید **`rule_violations`** ثبت می‌شوند (append-only ⇒ تاریخچه حفظ می‌شود).
- دو endpoint جدید اضافه شد: `POST /stages/{id}/evaluate` و `GET /stages/{id}/violations`.

---

## ۲. تغییرات فایل‌به‌فایل

### ۲.۱ `backend/app/models/prop.py`
- افزودن `RuleType` (۷ مقدار): `DAILY_DRAWDOWN`, `MAX_DRAWDOWN`, `PROFIT_TARGET`,
  `MIN_TRADING_DAYS`, `EQUITY_BALANCE`, `FLOATING_PNL`, `STAGE_STATUS`.
- افزودن `Severity` (۳ مقدار): `PASS`, `WARNING`, `VIOLATION`.
- افزودن مدل `RuleViolation` دقیقاً طبق قرارداد:

```python
class RuleViolation(Base):
    __tablename__ = "rule_violations"

    id = Column(Integer, primary_key=True, index=True)
    prop_stage_id = Column(Integer, ForeignKey("prop_stages.id"), nullable=False, index=True)
    rule_type = Column(Enum(RuleType), nullable=False, index=True)
    actual_value = Column(Float, nullable=False)
    limit_value = Column(Float, nullable=False)
    severity = Column(Enum(Severity), nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

    stage = relationship("PropStage", back_populates="rule_violations")
```

- افزودن رابطهٔ `PropStage.rule_violations` (cascade delete-orphan).
- ✅ **قانون «قوانین متعلق به PropStage»:** کلید خارجی `prop_stage_id` اجباری است.

### ۲.۲ `backend/migrations/versions/f6a7b8c9d0e1_phase32_rule_engine.py` (جدید)
- ساخت جدول `rule_violations` با ۴ ایندکس (`id`, `prop_stage_id`, `rule_type`, `severity`).
- Enum در دیتابیس با **NAME** ذخیره می‌شود (`'DAILY_DRAWDOWN'`, `'VIOLATION'`) — هم‌راستا با
  بقیهٔ Enumهای پروژه.
- `down_revision = d4e5f6a7b8c9` (head قبلی) · downgrade کامل.
- ✅ اجرا شد روی `trading_desk.db` و جدول تأیید شد.

### ۲.۳ `backend/app/services/prop_rule_engine.py`
- `evaluate_stage` اکنون کلیدهای زیر را نیز برمی‌گرداند:
  `rule_checks` (لیست ۷ نتیجهٔ ساختاریافته)، `overall_severity`، `floating_pnl`.
  (کلیدهای قبلی و `violations` رشته‌ای **حفظ شدند** ⇒ سازگاری کامل با
  `analytics.py`, `check-pass`, `pass_stage`.)
- متدهای جدید: `record_violations(...)`، `get_violations(...)`، `_build_rule_checks(...)`،
  `_grade_loss(...)`، `_overall_severity(...)`.

#### نگاشت آستانهٔ قوانین

| قاعده | actual_value | limit_value | PASS | WARNING | VIOLATION |
|:---|:---|:---|:---|:---|:---|
| `DAILY_DRAWDOWN` | بدترین زیان روز | `max_daily_dd` | < 80% | ۸۰٪ تا حد | > حد |
| `MAX_DRAWDOWN` | حداکثر افت | `max_total_dd` | < 80% | ۸۰٪ تا حد | > حد |
| `PROFIT_TARGET` | سود کل | `profit_target` | هدف محقق | هدف محقق‌نشده | — |
| `MIN_TRADING_DAYS` | روزها | `min_trading_days` | برآورده | کمتر از حد | — |
| `EQUITY_BALANCE` | موجودی | کف (`initial − max_total_dd`) | ≥ initial | < initial | < کف |
| `FLOATING_PNL` | زیان شناور معاملات باز | `max_daily_dd` | < 80% | ۸۰٪ تا حد | > حد |
| `STAGE_STATUS` | ۱ اگر ACTIVE | ۱ | ACTIVE | — | وضعیت terminal |

### ۲.۴ `backend/app/api/prop.py`
- `_serialize_rule_violation(v)` — خروجی JSON.
- `POST /api/prop/stages/{stage_id}/evaluate` — اجرای ارزیابی + ثبت + تولید هشدار ⇒
  خروجی `{stage_id, overall_severity, recorded, rule_checks, evaluation}`.
- `GET /api/prop/stages/{stage_id}/violations?severity=&limit=` — تاریخچه؛
  `severity` نامعتبر ⇒ `400`.

---

## ۳. باگ کشف‌شده و رفع‌شده (Out of spec, in-scope)

`max_daily_loss = abs(min(daily_pnl.values()))` **هر روز پرسود را نیز «زیان» می‌شمرد**
(مثلاً یک روز +$۹۵۰ ⇒ Daily DD = $۹۵۰ ⇒ نقض کاذب). اصلاح شد به:

```python
max_daily_loss = max(0.0, -min(daily_pnl.values())) if daily_pnl else 0.0
```

فقط روزهای منفی زیان شمرده می‌شوند. ✅ رگرسیون: همهٔ تست‌های قبلی پراپ سبز ماندند.

---

## ۴. تست‌ها — `backend/tests/test_phase32_rule_engine.py` (جدید · ۱۲ تست)

| تست | پوشش |
|:---|:---|
| `test_rule_checks_cover_all_rule_types` | هر ۷ RuleType تولید می‌شود |
| `test_rule_checks_healthy_stage_all_pass` | مرحله سالم ⇒ همه PASS |
| `test_daily_drawdown_violation` | زیان ۷۰۰ > ۵۰۰ ⇒ VIOLATION |
| `test_daily_drawdown_warning_near_limit` | ۸۴٪ حد ⇒ WARNING |
| `test_profit_target_and_min_days_warning` | هدف/روز برآورده‌نشده ⇒ WARNING |
| `test_stage_status_rule_violation_on_terminal` | وضعیت FAILED ⇒ VIOLATION |
| `test_floating_pnl_uses_open_trades` | زیان شناور معامله باز |
| `test_record_violations_persists_rows` | ۷ ردیف ثبت + `occurred_at` |
| `test_get_violations_filter_by_severity` | فیلتر severity |
| `test_record_violations_missing_stage_returns_empty` | مرحله ناموجود |
| `test_evaluate_and_list_violations_endpoint` | هر دو endpoint + خطای ۴۰۰ |
| `test_evaluate_endpoint_missing_stage` | ۴۰۴ |

---

## ۵. خروجی اجرای تست

```text
tests/test_phase32_rule_engine.py + tests/test_prop.py .... 22 passed
pytest (کل مجموعه) ....................................... 139 passed
alembic upgrade head ..................................... rule_violations ✓
```

---

## ۶. یادداشت‌های طراحی / تصمیم‌ها

1. **append-only:** هر فراخوانی `/evaluate` هفت ردیف جدید می‌سازد (تاریخچه). برای جلوگیری از
   رشد بی‌رویه، `limit` و فیلتر `severity` در endpoint فراهم شد؛ throttle/snapshot در فاز
   بعدی (M5 سند Audit) قابل افزودن است.
2. **Enum در DB = NAME:** طبق قرارداد پروژه؛ تست‌ها با `.value` مقایسه می‌کنند.
3. **`violations` رشته‌ای حفظ شد** تا فرانت/مصرف‌کننده‌های موجود نشکنند؛ `rule_checks`
   جایگزین نوعدار آن است.
4. **سازگاری:** `analytics.py` و `check-pass` بدون تغییر کار می‌کنند و اکنون `rule_checks`
   را هم می‌بینند.
5. **فازهای بعدی (خارج از این فاز):** Trailing DD، Consistency، Daily Profit Cap و News Rule
   (Q-5 گزینهٔ ج) به همین ساختار `rule_checks` قابل افزودن‌اند.

