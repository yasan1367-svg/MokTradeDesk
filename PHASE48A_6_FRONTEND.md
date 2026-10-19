# PHASE 48a.6 — فرانت `ComparisonPage` (قرارداد جدید مقایسه/رتبه‌بندی)

> وضعیت: ✅ کامل — **بدون commit** (منتظر تأیید)
> تست‌ها: `TSC_EXIT=0` · `VITEST_EXIT=0 (9 passed)` · `BUILD_EXIT=0`

---

## ۱) خلاصهٔ اجرایی

فرانتِ مقایسه که روی **قرارداد قدیم** (`items / health_score / best_health_score / recommendation /
symbol_bests / detail_bests` + `min_trades`) نوشته شده بود، با **قرارداد جدید** بک‌اند
(`{comparison, test_type, filters, best}` با `rank/score/metrics/reasons[/error]`) هم‌آهنگ شد.

- **`client.ts`**: تایپ‌های جدید + `compareVersions`/`rankVersions`؛ حذف `compareVersionsWithDetails` و `min_trades`.
- **`ComparisonPage.tsx`**: بازنویسی کامل (۶۷۱ → ۵۲۹ خط) — فیلترهای جدید + جدول رتبه‌بندی + بهترین نسخه + نمودارها + Drawer دلایل.
- **بک‌اند**: هیچ تغییری لازم نشد (reasons همان `{icon, text}[]` ماند — تصمیم «گزینه الف»).

---

## ۲) تغییرات `frontend/src/api/client.ts` (+۴۴/−۳)

**اضافه:**
```typescript
export interface CompareRequest { version_ids: number[]; test_type?: string; symbol?: string; date_from?: string; date_to?: string; }
export interface Reason { icon: string; text: string; }
export interface VersionComparisonItem { version_id: number; rank?: number; score?: number; metrics?: Record<string, any>; reasons?: Reason[]; error?: string; }
export interface CompareResponse { comparison: VersionComparisonItem[]; test_type: string; filters: { symbol?; date_from?; date_to? }; best: VersionComparisonItem | null; }
export interface RankResponse { ranking: VersionComparisonItem[]; best: VersionComparisonItem | null; }

export const compareVersions = (data: CompareRequest) => api.post<CompareResponse>('/api/analytics/compare', data);
export const rankVersions   = (data: CompareRequest) => api.post<RankResponse>('/api/analytics/rank', data);
```

**حذف:** `compareVersionsWithDetails` و پارامتر `min_trades` (تنها مصرف‌کننده‌اش همان تابع بود).

---

## ۳) تغییرات `frontend/src/pages/ComparisonPage.tsx` (بازنویسی کامل)

### حذف‌شده
- import `compareVersionsWithDetails`
- اسلایدر **`minTrades`** و `belowThreshold`
- **`items` / `skipped` / `health_score` / `best_health_score` / `recommendation` / `symbol_bests` / `detail_bests`**
- تابع `getCellStyle` (مقایسهٔ flat قدیم)

### اضافه‌شده
| مورد | جزئیات |
|---|---|
| State جدید | `testType` (پیش‌فرض `BACKTEST`)، `symbol`، `dateFrom`، `dateTo` |
| انتخابگر Test Type | `BACKTEST / FORWARD / REAL_PERSONAL / REAL_PROP` |
| فیلتر نماد | input (`XAUUSD`) |
| فیلتر تاریخ | دو `input[type=date]` |
| نگاشت نام | `labelOf(version_id)` ⇒ «استراتژی / نسخه» و `strategyOf(version_id)` از `getAllVersions()` |
| جدول رتبه‌بندی | ستون‌ها: رتبه | نسخه | Score | نرخ برد | فاکتور سود | سود خالص | حداکثر DD | دلایل |
| نمایش خطای نسخهٔ تحلیل‌نشده | `colSpan=6` با `⚠️ {item.error}` |
| کارت «🏆 بهترین نسخه» | با `best.version_id` + **`best.score`** |
| نمودارها | ۴× `ComparisonBarChart` (`win_rate/net_pnl/profit_factor/max_dd`) + `ComparisonRadarChart` |
| Drawer دلایل | با `reasons = {icon, text}[]` |
| حالت‌ها | `loading` ⇒ `Skeleton` · خالی ⇒ `EmptyState` · خطا ⇒ `toast.error` |
| Badge رتبه | طلایی/نقره‌ای/خنثی بر اساس `rank` |

### «آرایهٔ مشتق‌شده» برای نمودارها (بدون دست‌زدن به کامپوننت‌های چارت)
کامپوننت‌های موجود انتظار آرایهٔ **flat** داشتند (`version_name`, `strategy_name`, `health_score`, `win_rate`, …)
در حالی که قرارداد جدید `metrics` تودرتو + `score` دارد. بنابراین در صفحه:

```ts
const chartItems = (result?.comparison ?? [])
  .filter((i) => !i.error && i.metrics)
  .map((i) => {
    const m = i.metrics || {};
    return {
      version_id: i.version_id,
      version_name: labelOf(i.version_id),
      strategy_name: strategyOf(i.version_id),
      win_rate: Number(m.win_rate ?? 0),
      profit_factor: Number(m.profit_factor ?? 0),
      net_pnl: Number(m.net_pnl ?? 0),
      max_dd: Number(m.max_dd ?? 0),
      health_score: Number(i.score ?? 0), // Radar نام health_score می‌خواهد ⇒ از score پر می‌شود
    };
  });
```
⇒ **هیچ تغییری در `ComparisonBarChart`/`ComparisonRadarChart` لازم نشد** (نمودار Radar حالا «Score» را به‌جای «Health Score» نشان می‌دهد).

### حفظ‌شده
- ظاهر فعلی (Tailwind + CSS variables: `--bg-card`, `--accent`, `--profit`, `--warning-soft`, …) و ساختار دیوها
- انتخابگر استراتژی/جستجو و ساختار لیست نسخه‌ها (checkbox، سقف ۵ نسخه)
- `getAllVersions` + `getStrategies`

### استفادهٔ هدفمند از کامپوننت‌های موجود
`EmptyState` (حالت خالی) · `Skeleton` (حالت بارگذاری) · `useToast` (خطا/هشدار).

---

## ۴) نتیجهٔ تست‌ها

```
npx tsc -b --force   →  TSC_EXIT=0
npx vitest run       →  2 files passed · 9 tests passed · VITEST_EXIT=0
npm run build        →  ✓ built in 3.94s · BUILD_EXIT=0
```
(⛔ خطای موقت گام ۲ یعنی `TS2305: no exported member 'compareVersionsWithDetails'` کاملاً برطرف شد.)

---

## ۵) چیزهایی که اضافه/حذف شد — فهرست سریع
- **+** فیلترهای `test_type`/`symbol`/`date_from`/`date_to`
- **+** جدول رتبه‌بندی (rank/score/metrics/reasons) و Drawer دلایل
- **+** کارت بهترین نسخه بر پایهٔ `best.score`
- **+** نمایش `error` برای نسخهٔ تحلیل‌نشده
- **−** `min_trades` slider · `items` · `skipped` · `health_score` · `best_health_score` · `recommendation` · `symbol_bests` · `detail_bests`

---

## ۶) وضعیت Git (⛔ بدون commit)
```
M frontend/src/api/client.ts
M frontend/src/pages/ComparisonPage.tsx   (بازنویسی کامل: 671 → 529 خط)
```
