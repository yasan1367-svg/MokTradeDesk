import { useState, useEffect } from 'react';
import GlassCard from '../components/GlassCard';
import MetricCard from '../components/MetricCard';
import AnalysisTable from '../components/AnalysisTable';
import {
  getAllVersions,
  getTrades,
  exportAnalysisPdf,
  analyzeVersionScoped,
  analyzePropStage,
  analyzePersonalAccount,     // فاز ۴۸c
  getAnalysisVersion,
  getAnalysisProp,
  getAnalysisPersonalAccount, // فاز ۴۸c
  getAllPropStages,
  getPersonalTradingAccounts, // فاز ۴۸c
} from '../api/client';

import EquityCurveChart from '../components/charts/EquityCurveChart';
import SessionBarChart from '../components/charts/SessionBarChart';
import WinLossPieChart from '../components/charts/WinLossPieChart';
import WeekdayBarChart from '../components/charts/WeekdayBarChart';
import PnLDistributionChart from '../components/charts/PnLDistributionChart';

// فاز ۳۸.۴ (Clean Break) — تب «بروکر» حذف شد: حساب مالیِ نوع «بروکر» وجود ندارد
// (حساب‌های معاملاتی → `PersonalTradingAccount` در بک‌اند) و endpointهای تحلیل بروکر هم نیستند.
type ScopeType = 'backtest' | 'forward' | 'real_personal' | 'prop_stage_1' | 'prop_stage_2' | 'prop_stage_3';
const SCOPE_TABS: { key: ScopeType; icon: string; label: string; testType?: string }[] = [
  { key: 'backtest', icon: '📊', label: 'بک‌تست', testType: 'BACKTEST' },
  { key: 'forward', icon: '📈', label: 'فوروارد', testType: 'FORWARD' },
  // فاز ۴۸c — حساب معاملاتی شخصی (REAL_PERSONAL)؛ مسیر تحلیلش `personal-account` است نه نسخه
  { key: 'real_personal', icon: '💼', label: 'واقعی شخصی', testType: 'REAL_PERSONAL' },
  { key: 'prop_stage_1', icon: '🏁', label: 'مرحله ۱' },
  { key: 'prop_stage_2', icon: '🔍', label: 'مرحله ۲' },
  { key: 'prop_stage_3', icon: '💰', label: 'مرحله ۳' },
];

/** فاز ۴۸c — `test_type` هر دامنه/تب (منبع واحد حقیقت؛ جایگزین ternaryهای پراکنده) */
const testTypeOfScope = (scope: ScopeType): string | undefined =>
  SCOPE_TABS.find((t) => t.key === scope)?.testType;

interface Version { id: number; version_name: string; strategy_name: string; }
interface PropStageOption { id: number; display_name: string; stage_type: string; }
interface PersonalAccountOption {
  id: number;
  account_label?: string | null;
  account_number?: string | null;
  broker_name?: string | null;
}

const SCOPE_KEY = 'analysis_selected_scope';
const VALID_SCOPES: ScopeType[] = SCOPE_TABS.map((t) => t.key);

/** مقدار ذخیره‌شده در localStorage را اعتبارسنجی می‌کند (scopeهای حذف‌شده مثل 'broker') */
function readStoredScope(): ScopeType {
  if (typeof window === 'undefined') return 'backtest';
  try {
    const stored = JSON.parse(localStorage.getItem(SCOPE_KEY) || '"backtest"') as ScopeType;
    return VALID_SCOPES.includes(stored) ? stored : 'backtest';
  } catch {
    return 'backtest';
  }
}

// فاز ۲۳ — هر تب مرحله فقط مراحل همان نوع را نشان می‌دهد
const STAGE_TYPE_BY_SCOPE: Record<string, string> = {
  prop_stage_1: 'stage_1',
  prop_stage_2: 'stage_2',
  prop_stage_3: 'funded_real',
};

export default function AnalysisPage() {
  const [scope, setScope] = useState<ScopeType>(readStoredScope);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [propStages, setPropStages] = useState<PropStageOption[]>([]);
  // فاز ۴۸c — حساب‌های معاملاتی شخصی (دامنهٔ REAL_PERSONAL)
  const [personalAccounts, setPersonalAccounts] = useState<PersonalAccountOption[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ═════════════════════════════════════════════
  // ۱. بارگذاری لیست‌های اولیه (نسخه‌ها / پراپ‌ها)
  // فاز ۳۸.۳ — بارگذاری «بروکرها» حذف شد (query مرده)
  // ═════════════════════════════════════════════
  useEffect(() => {
    getAllVersions()
      .then((res) => setVersions(res.data))
      .catch((err) => console.error('خطا در دریافت نسخه‌ها:', err));
    getAllPropStages()
      .then((res) => setPropStages(res.data))
      .catch((err) => console.error('خطا در دریافت مراحل پراپ:', err));
    // فاز ۴۸c — حساب‌های معاملاتی شخصی (منبع: /api/trading/accounts)
    getPersonalTradingAccounts()
      .then((res) => setPersonalAccounts(res.data || []))
      .catch((err) => console.error('خطا در دریافت حساب‌های معاملاتی شخصی:', err));
  }, []);

  // ═════════════════════════════════════════════
  // فاز ۲۳ — انتخاب خودکار اولین مرحلهٔ مربوط به تب جاری (۱/۲/۳)
  // ═════════════════════════════════════════════
  useEffect(() => {
    // فاز ۴۸c — تب «واقعی شخصی»: اولین حساب معاملاتی شخصی خودکار انتخاب می‌شود
    if (scope === 'real_personal') {
      setSelectedId(personalAccounts.length > 0 ? personalAccounts[0].id : null);
      return;
    }
    if (!scope.startsWith('prop_stage_')) return;
    const stageType = STAGE_TYPE_BY_SCOPE[scope];
    const first = propStages.find((s) => s.stage_type === stageType);
    setSelectedId(first ? first.id : null);
  }, [scope, propStages, personalAccounts]);

  // ═════════════════════════════════════════════
  // ۲. بارگذاری تحلیل و معاملات بر اساس scope
  // ═════════════════════════════════════════════
  useEffect(() => {
    if (!selectedId || !scope) return;
    setLoading(true); setError(null);
    const loadData = async () => {
      try {
        let analysisData: any = null;
        let tradesData: any[] = [];
        try {
          const isVersion = scope === 'backtest' || scope === 'forward';
          // فاز ۴۸c: منبع واحد `test_type` از تب فعال (testTypeOfScope)
          const testType = testTypeOfScope(scope);
          // فاز ۳۸.۴: تب «بروکر» حذف شد ⇒ سه دامنه: نسخه / حساب شخصی / مرحله پراپ
          // فاز ۴۸c: `real_personal` ⇒ ENDPOINT حساب شخصی (scope=PERSONAL_ACCOUNT)
          const res = isVersion
            ? await getAnalysisVersion(selectedId, testType)
            : scope === 'real_personal'
              ? await getAnalysisPersonalAccount(selectedId)
              : await getAnalysisProp(selectedId);
          analysisData = res.data;
        } catch (e) {
          console.log('تحلیلی یافت نشد');
        }
        try {
          // فاز ۲۳ — لیست معاملات بر اساس scope (نسخه/مرحله پراپ)
          // فاز ۳۸.۴: شاخهٔ «بروکر» (با پارامتر نامعتبر `finance_account_id`) حذف شد
          // فاز ۴۸c: شاخهٔ حساب شخصی ⇒ `personal_trading_account_id`
          const isVersionScope = scope === 'backtest' || scope === 'forward';
          const tradesRes = isVersionScope
            ? await getTrades({ version_id: selectedId, test_type: testTypeOfScope(scope), limit: 500 })
            : scope === 'real_personal'
              ? await getTrades({ personal_trading_account_id: selectedId, limit: 500 })
              : await getTrades({ prop_stage_id: selectedId, limit: 500 });
          tradesData = tradesRes.data.trades || [];
        } catch (e) {
          console.log('معامله‌ای یافت نشد');
        }
        setAnalysis(analysisData);
        setTrades(tradesData);
      } catch { setError('خطا در بارگذاری داده‌ها'); }
      finally { setLoading(false); }
    };
    loadData();
  }, [selectedId, scope]);

  // ═════════════════════════════════════════════
  // اجرای تحلیل بر اساس scope
  // ═════════════════════════════════════════════
  const handleReanalyze = async () => {
    if (!selectedId) return;
    setLoading(true); setError(null);
    try {
      const isVersion = scope === 'backtest' || scope === 'forward';
      const testType = testTypeOfScope(scope);
      if (isVersion) {
        await analyzeVersionScoped(selectedId, testType);
        const res = await getAnalysisVersion(selectedId, testType);
        setAnalysis(res.data);
      } else if (scope === 'real_personal') {
        // فاز ۴۸c — تحلیل دامنهٔ REAL_PERSONAL (scope=PERSONAL_ACCOUNT)
        await analyzePersonalAccount(selectedId);
        const res = await getAnalysisPersonalAccount(selectedId);
        setAnalysis(res.data);
      } else {
        // فاز ۳۸.۴: تب «بروکر» حذف شد ⇒ باقی موارد مرحله پراپ است
        await analyzePropStage(selectedId);
        const res = await getAnalysisProp(selectedId);
        setAnalysis(res.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در تحلیل');
    } finally { setLoading(false); }
  };

  const handleScopeChange = (newScope: ScopeType) => {
    setScope(newScope);
    setSelectedId(null);
    setAnalysis(null);
    setTrades([]);
    setError(null);
    localStorage.setItem(SCOPE_KEY, JSON.stringify(newScope));
  };

  return (
    <div>
      {/* تب‌های نوع تحلیل (فاز ۲۰) */}
      <GlassCard className="mb-4">
        <div className="flex flex-wrap gap-2">
          {SCOPE_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => handleScopeChange(t.key)}
              className={`px-4 py-2.5 rounded-[10px] text-[12px] font-extrabold transition-all ${
                scope === t.key
                  ? 'bg-[var(--accent)] text-white shadow-md'
                  : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-subtle)] hover:border-[var(--accent)]'
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </GlassCard>

      {/* انتخابگر بر اساس scope */}
      <GlassCard className="mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[250px]">
            <label className="text-[var(--text-secondary)] text-sm block mb-2">
              {scope === 'real_personal'
                ? 'انتخاب حساب معاملاتی شخصی'
                : scope.startsWith('prop_stage_')
                  ? 'انتخاب مرحله پراپ'
                  : 'انتخاب نسخه'}
            </label>
            {scope === 'real_personal' ? (
              /* فاز ۴۸c — دامنهٔ REAL_PERSONAL: منبع /api/trading/accounts */
              <select value={selectedId || ''} onChange={(e) => setSelectedId(Number(e.target.value) || null)}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)]">
                <option value="">— حساب معاملاتی شخصی ثبت نشده است —</option>
                {personalAccounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.account_label || a.account_number || `#${a.id}`}
                    {a.broker_name ? ` — ${a.broker_name}` : ''}
                  </option>
                ))}
              </select>
            ) : scope.startsWith('prop_stage_') ? (
              <select value={selectedId || ''} onChange={(e) => setSelectedId(Number(e.target.value) || null)}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)]">
                <option value="">— مرحله‌ای از این نوع وجود ندارد —</option>
                {propStages
                  .filter((s) => s.stage_type === STAGE_TYPE_BY_SCOPE[scope])
                  .map((s) => <option key={s.id} value={s.id}>{s.display_name}</option>)}
              </select>
            ) : (
              <select value={selectedId || ''} onChange={(e) => setSelectedId(Number(e.target.value) || null)}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)]">
                <option value="">— نسخه‌ای وجود ندارد —</option>
                {versions.map((v) => <option key={v.id} value={v.id}>{v.strategy_name} / {v.version_name}</option>)}
              </select>
            )}
          </div>

          <button onClick={handleReanalyze} disabled={loading || !selectedId}
            className="bg-[var(--accent)] hover:bg-accent/80 text-white px-6 py-3 rounded-xl transition-all disabled:opacity-50 mt-6">
            {loading ? '⏳ در حال تحلیل...' : '🔄 تحلیل مجدد'}
          </button>
          {analysis && selectedId && (scope === 'backtest' || scope === 'forward') && (
            <button onClick={async () => {
              try {
                const res = await exportAnalysisPdf(selectedId!, scope === 'forward' ? 'FORWARD' : 'BACKTEST');
                const blob = new Blob([res.data], { type: 'application/pdf' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url;
                a.download = `analysis_${selectedId}_${new Date().toISOString().slice(0, 10)}.pdf`;
                document.body.appendChild(a); a.click();
                window.URL.revokeObjectURL(url); a.remove();
              } catch { setError('خطا در دانلود PDF'); }
            }}
              className="bg-[#E45D72] hover:bg-[#E45D72]/80 text-white px-5 py-3 rounded-xl transition-all mt-6 flex items-center gap-1">
              📄 دانلود PDF
            </button>
          )}
        </div>

        {error && (
          <div className="mt-4 bg-loss/10 border border-loss/30 text-[var(--loss)] p-3 rounded-xl text-sm">
            ❌ {error}
          </div>
        )}
      </GlassCard>

      {analysis ? (
        <>
          {/* متریک‌های پایه */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
            <MetricCard
              label="💰 سود خالص"
              value={`${analysis.net_pnl >= 0 ? '+' : ''}${analysis.net_pnl} USDT `}
              sub={`از ${analysis.total_trades} معامله`}
              color={analysis.net_pnl >= 0 ? 'profit' : 'loss'}
              icon="💰"
            />
            <MetricCard
              label="📈 نرخ برد"
              value={`${analysis.win_rate}٪`}
              sub={`${Math.round((analysis.win_rate / 100) * analysis.total_trades)} برد`}
              icon="📈"
            />
            <MetricCard
              label="🏆 فاکتور سود"
              value={analysis.profit_factor}
              sub="سود کل / ضرر کل"
              color="accent"
              icon="🏆"
            />
            <MetricCard
              label="⚠️ حداکثر ضرر"
              value={`-${analysis.max_dd} USDT `}
              sub="کمترین نقطه‌ی منحنی"
              color="loss"
              icon="⚠️"
            />
          </div>

          {/* متریک‌های تکمیلی */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
            <MetricCard
              label="🎯 Net R"
              value={`${analysis.net_r} R`}
              sub="مجموع R-Multiple معاملات"
              color={analysis.net_r >= 0 ? 'profit' : 'loss'}
              icon="🎯"
            />
            <MetricCard
              label="📐 اکسپکتنسی"
              value={`${analysis.expectancy} USDT `}
              sub={analysis.expectancy_r !== null && analysis.expectancy_r !== undefined ? `${analysis.expectancy_r} R به‌ازای هر معامله` : 'به‌ازای هر معامله'}
              color={analysis.expectancy >= 0 ? 'profit' : 'loss'}
              icon="📐"
            />
            <MetricCard
              label="📊 میانگین برد / باخت"
              value={`+${analysis.avg_win} / -${analysis.avg_loss}`}
              sub={`بزرگ‌ترین: +${analysis.largest_win} / -${analysis.largest_loss}`}
              icon="📊"
            />
            <MetricCard
              label="🔻 بیشترین باخت متوالی"
              value={analysis.max_consecutive_losses}
              sub={
                analysis.consistency_analysis
                  ? `نسبت برد/باخت: ${analysis.consistency_analysis.avg_win_avg_loss_ratio}`
                  : undefined
              }
              color="loss"
              icon="🔻"
            />
          </div>

          {analysis.consistency_analysis && (
            <div className="glass-card p-5 mb-6">
              <div className="text-[var(--text-secondary)] text-sm mb-3">📉 تحلیل پایداری (Consistency)</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-[var(--text-secondary)] text-xs mb-1">انحراف معیار سود معاملات</div>
                  <div className="font-bold text-[var(--text-primary)]">{analysis.consistency_analysis.pnl_std_dev} USDT </div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs mb-1">وابستگی به معاملات بزرگ</div>
                  <div className="font-bold text-[var(--text-primary)]">
                    {analysis.consistency_analysis.top_trades_contribution_percent}٪ از سود از ۳ معامله‌ی برتر
                  </div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs mb-1">نسبت میانگین برد به باخت</div>
                  <div className="font-bold text-[var(--text-primary)]">{analysis.consistency_analysis.avg_win_avg_loss_ratio}</div>
                </div>
              </div>
            </div>
          )}

{/* نمودارها */}
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
  <GlassCard className="lg:col-span-2">
    <h3 className="text-[var(--text-primary)] font-bold mb-4">📈 منحنی سرمایه</h3>
    <EquityCurveChart trades={trades} initialBalance={10000} />
  </GlassCard>

  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">🥇 برد / باخت</h3>
    <WinLossPieChart
      wins={Math.round((analysis.win_rate / 100) * analysis.total_trades)}
      losses={analysis.total_trades - Math.round((analysis.win_rate / 100) * analysis.total_trades)}
    />
  </GlassCard>
</div>

<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">🌍 نرخ برد بر اساس سشن</h3>
    <SessionBarChart data={analysis.session_analysis || {}} metric="win_rate" />
  </GlassCard>

  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">📅 نرخ برد بر اساس روز هفته</h3>
    <WeekdayBarChart data={analysis.weekday_analysis || {}} metric="win_rate" />
  </GlassCard>
</div>

<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">💰 توزیع سود بر اساس نماد</h3>
    <PnLDistributionChart trades={trades} />
  </GlassCard>

  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">💵 سود خالص بر اساس سشن</h3>
    <SessionBarChart data={analysis.session_analysis || {}} metric="net_pnl" />
  </GlassCard>
</div>

          {/* تحلیل‌های تفکیکی */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <AnalysisTable
              title="تحلیل سشن‌ها"
              icon="🌍"
              data={analysis.session_analysis || {}}
              firstColumnLabel="سشن"
            />
            <AnalysisTable
              title="تحلیل روزهای هفته"
              icon="📅"
              data={analysis.weekday_analysis || {}}
              firstColumnLabel="روز"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <AnalysisTable
              title="تحلیل ساعت‌ها"
              icon="🕐"
              data={analysis.hour_analysis || {}}
              firstColumnLabel="ساعت"
            />
            <AnalysisTable
              title="تحلیل بازه‌های سفارشی"
              icon="⏰"
              data={analysis.custom_time_analysis || {}}
              firstColumnLabel="بازه"
            />
          </div>

          {/* جدول معاملات */}
          <GlassCard>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-[var(--text-primary)] font-bold">
                📋 لیست معاملات ({trades.length})
              </h3>
            </div>

            {trades.length === 0 ? (
              <div className="text-[var(--text-secondary)] text-sm text-center py-8">
                معامله‌ای برای این دامنه ثبت نشده است
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[var(--text-secondary)] border-b border-[var(--border-subtle)]">
                      <th className="text-right py-2">#</th>
                      <th className="text-right py-2">نماد</th>
                      <th className="text-right py-2">نوع تست</th>
                      <th className="text-right py-2">جهت</th>
                      <th className="text-right py-2">حجم</th>
                      <th className="text-right py-2">قیمت باز</th>
                      <th className="text-right py-2">قیمت بسته</th>
                      <th className="text-right py-2">سود/زیان</th>
                      <th className="text-right py-2">تاریخ بسته</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, idx) => (
                      <tr key={t.id} className="border-b border-card-border/50 hover:bg-card/50">
                        <td className="py-2 text-[var(--text-secondary)]">{idx + 1}</td>
                        <td className="py-2 text-[var(--text-primary)] font-bold">{t.symbol}</td>
                        <td className="py-2">
                          <span className="text-xs bg-accent/20 text-[var(--accent)] px-2 py-1 rounded">
                            {t.test_type === 'backtest' ? 'بک‌تست' :
                             t.test_type === 'forward' ? 'فوروارد' :
                             t.test_type === 'real_personal' ? 'رییل شخصی' :
                             t.test_type === 'real_prop' ? 'رییل پراپ' : 'رییل'}
                          </span>
                        </td>
                        <td className={`py-2 ${t.direction === 'buy' ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {t.direction === 'buy' ? 'خرید' : 'فروش'}
                        </td>
                        <td className="py-2 text-[var(--text-primary)]">{t.size}</td>
                        <td className="py-2 text-[var(--text-primary)]">{t.open_price?.toFixed(2)}</td>
                        <td className="py-2 text-[var(--text-primary)]">{t.close_price?.toFixed(2)}</td>
                        <td className={`py-2 font-bold ${t.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)} USDT
                        </td>
                        <td className="py-2 text-[var(--text-secondary)] text-xs">
                          {t.close_time ? new Date(t.close_time).toLocaleString('fa-IR') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>
        </>
      ) : (
        !loading && (
          <GlassCard>
            <div className="text-center py-12 text-[var(--text-secondary)]">
              <div className="text-4xl mb-4">📊</div>
              <div>برای مشاهده‌ی تحلیل، یک دامنه (نسخه / حساب شخصی / مرحله پراپ) انتخاب کنید و روی «تحلیل مجدد» کلیک کنید</div>
            </div>
          </GlassCard>
        )
      )}
    </div>
  );
}
